"""Create a customer-free daily benchmark from the original UCI archive.

Usage: python scripts/prepare_external_retail.py --archive path/to/online+retail.zip
Requires openpyxl only for rebuilding this derived file, not for running the app.
"""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
import pandas as pd


def prepare(archive, output):
    archive=Path(archive);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    with ZipFile(archive) as bundle:
        member=next(name for name in bundle.namelist() if name.endswith('.xlsx'))
        with bundle.open(member) as source:
            raw=pd.read_excel(source,engine='openpyxl',dtype={'InvoiceNo':str})
    valid=(~raw.InvoiceNo.str.upper().str.startswith('C',na=True)) & (raw.Quantity>0) & (raw.UnitPrice>0) & raw.InvoiceDate.notna()
    rows=raw.loc[valid].copy();rows['date']=pd.to_datetime(rows.InvoiceDate).dt.normalize()
    daily=rows.groupby('date').agg(units=('Quantity','sum'),invoice_count=('InvoiceNo','nunique'),positive_sales_gbp=('UnitPrice',lambda x:float((x*rows.loc[x.index,'Quantity']).sum())))
    daily=daily.reindex(pd.date_range(raw.InvoiceDate.min().normalize(),raw.InvoiceDate.max().normalize(),freq='D'),fill_value=0)
    daily.index.name='date';daily.reset_index().to_csv(output/'daily_sales.csv',index=False,lineterminator='\n')
    metadata={'dataset':'UCI Online Retail','creator':'Daqing Chen','year':2015,'doi':'10.24432/C5BW33','license':'CC BY 4.0','source_url':'https://archive.ics.uci.edu/dataset/352/online+retail','download_url':'https://archive.ics.uci.edu/static/public/352/online+retail.zip','archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'derived_sha256':hashlib.sha256((output/'daily_sales.csv').read_bytes()).hexdigest(),'original_rows':len(raw),'eligible_positive_sales_rows':int(valid.sum()),'excluded_rows':int((~valid).sum()),'calendar_days':len(daily),'start':str(daily.index.min().date()),'end':str(daily.index.max().date()),'transformation':'Exclude cancellation-prefixed invoices, nonpositive quantities/prices and missing dates; aggregate all countries by calendar date; fill absent dates with zero recorded sales. No deduplication. No customer IDs or descriptions retained. Last source date may be partial. Sales are positive recorded sales, not net revenue after returns.','scope':'Separate locally fitted demand benchmark; never joined to official Track 4 records. Currency is GBP, no currency conversion.'}
    (output/'provenance.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',required=True)
    parser.add_argument('--output',default='data/external/uci_online_retail')
    args=parser.parse_args();prepare(args.archive,args.output)
