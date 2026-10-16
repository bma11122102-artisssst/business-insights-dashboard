from pathlib import Path
import hashlib
import json
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from vaultdata.ml.external import evaluate_external, EXTERNAL_PATH
from vaultdata.viz.charts import distribution_donut


def test_external_benchmark_provenance_and_temporal_evaluation():
    report,forecast,holdout=evaluate_external()
    metadata=report['provenance']
    assert metadata['original_rows']==541909
    assert metadata['license']=='CC BY 4.0'
    assert report['source_sha256']==hashlib.sha256((EXTERNAL_PATH/'daily_sales.csv').read_bytes()).hexdigest()
    assert pd.Timestamp(report['validation_windows'][-1]['validation_end']) < pd.Timestamp(report['test_start'])
    assert len(holdout)==14 and len(forecast)==30
    assert report['test']['mae']>=0
    assert report['selected_model']==min(report['validation'],key=lambda k:report['validation'][k]['mae'])
    assert 'customer' not in ' '.join(pd.read_csv(EXTERNAL_PATH/'daily_sales.csv').columns).lower()


def test_external_benchmark_rejects_changed_source(tmp_path):
    (tmp_path/'provenance.json').write_bytes((EXTERNAL_PATH/'provenance.json').read_bytes())
    (tmp_path/'daily_sales.csv').write_bytes((EXTERNAL_PATH/'daily_sales.csv').read_bytes()+b'\n')
    with pytest.raises(ValueError,match='checksum'):
        evaluate_external(tmp_path)


def test_recommendations_render_without_external_model():
    script='''
from vaultdata.data.track4 import load_sources,prepare_transactions
from views.track4 import recommendations
df=prepare_transactions(load_sources());recommendations(df,df)
'''
    app=AppTest.from_string(script).run(timeout=30)
    assert not app.exception
    assert app.checkbox and app.text_area
    assert not any('Get LeakLens' in item.label for item in app.button)


def test_empty_donut_has_no_misleading_segments():
    fig=distribution_donut(pd.Series(dtype=float),'No orders','orders')
    assert not fig.data
    assert 'No data' in fig.layout.annotations[0].text
