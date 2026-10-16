"""Separate external-data demand benchmark; never pools businesses or currencies."""
import hashlib
import json
from pathlib import Path
import pandas as pd
from vaultdata.config import REPO_ROOT
from vaultdata.ml.demand import evaluate_series

EXTERNAL_PATH=REPO_ROOT/'data'/'external'/'uci_online_retail'


def evaluate_external(path=EXTERNAL_PATH):
    path=Path(path);source=path/'daily_sales.csv'
    metadata=json.loads((path/'provenance.json').read_text(encoding='utf-8'))
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if digest!=metadata['derived_sha256']:
        raise ValueError('External source checksum changed; rebuild its provenance before evaluating.')
    frame=pd.read_csv(source,parse_dates=['date']).set_index('date').asfreq('D')
    if frame.index.has_duplicates or frame.units.isna().any() or (frame.units<0).any():
        raise ValueError('External benchmark requires unique daily nonnegative unit counts.')
    summary,forecast,holdout=evaluate_series(frame.units,future_days=30)
    summary.update({'dataset':'UCI Online Retail','source_sha256':digest,'provenance':metadata,
                    'scope':'Independent fit on external daily positive-sale units. Not transfer validation of the Track 4 model and not pooled with Track 4.',
                    'limitations':summary.get('limitations',[])+['Excluded cancellations and nonpositive rows; does not estimate returns or net revenue.','Zero-filled dates mean no recorded sales, not necessarily zero demand. Final source day may be incomplete.','External business and time period differ from the challenge; no direct calibration or causal impact claim.']})
    return summary,forecast,holdout
