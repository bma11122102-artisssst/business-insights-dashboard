"""Actual customer-level RFM clustering, distinct from supplied profile labels."""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score,davies_bouldin_score
from vaultdata.ml.common import SEED,InsufficientData

def customer_features(transactions,as_of=None):
    if transactions.empty: raise InsufficientData('No customer orders are available.')
    end=pd.Timestamp(as_of) if as_of is not None else transactions.Date.max()
    eligible=transactions[(transactions.Status=='Completed') & (transactions.Date<=end)]
    profiles=eligible.groupby('customer_id').agg(last_purchase=('Date','max'),frequency=('Invoice ID','nunique'),monetary=('Total','sum'))
    profiles['recency']=(end-profiles.last_purchase).dt.days
    return profiles[['recency','frequency','monetary']]

def segment_customers(transactions,as_of=None):
    features=customer_features(transactions,as_of)
    if len(features)<20: raise InsufficientData('At least 20 customers with completed orders are needed to compare groups.')
    matrix=StandardScaler().fit_transform(np.log1p(features[['recency','frequency','monetary']]))
    trials={};models={}
    for k in range(2,min(7,len(features))):
        model=KMeans(n_clusters=k,n_init=10,random_state=SEED).fit(matrix)
        if len(np.unique(model.labels_))<2: continue
        trials[k]=float(silhouette_score(matrix,model.labels_,sample_size=min(1000,len(features)),random_state=SEED))
        models[k]=model
    if not trials: raise InsufficientData('Customer histories are too similar to form distinct groups.')
    k=max(trials,key=trials.get);model=models[k]
    assignments=features.copy(); assignments['cluster']=model.labels_
    grouped=assignments.groupby('cluster').agg(customers=('frequency','size'),mean_recency_days=('recency','mean'),mean_completed_orders=('frequency','mean'),mean_spend=('monetary','mean'),revenue=('monetary','sum')).sort_values('mean_spend',ascending=False)
    global_spend=assignments.monetary.mean();global_recency=assignments.recency.mean()
    names={}
    for n,(cluster,row) in enumerate(grouped.iterrows(),1):
        descriptor='higher spending' if row.mean_spend>=global_spend else 'lower spending'
        descriptor+=', more recent' if row.mean_recency_days<=global_recency else ', less recent'
        names[cluster]=f'Group {n}: {descriptor}'
    assignments['group']=assignments.cluster.map(names)
    grouped['group']=[names[c] for c in grouped.index]
    summary={'method':'KMeans on standardized log1p customer recency, frequency, monetary value','seed':SEED,'customers_clustered':len(features),'selected_k':k,
        'silhouette':trials[k],'davies_bouldin':float(davies_bouldin_score(matrix,model.labels_)), 'candidate_silhouettes':trials,
        'as_of':str((pd.Timestamp(as_of) if as_of is not None else transactions.Date.max()).date()), 'groups':grouped.reset_index(drop=True).to_dict('records'),
        'limitations':['Unsupervised group separation is not prediction accuracy or proof of meaningful business types.', 'Features use only completed orders at or before the snapshot date. Customers with no completed purchases are not clustered.', 'Supplied customer_segment is not a training target; new groups are derived independently. Low silhouette means weak group separation.']}
    return summary,assignments.reset_index()
