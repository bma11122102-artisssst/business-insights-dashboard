"""Official Track 4 inputs, adapted to the original dashboard's column contract."""
from pathlib import Path
import pandas as pd
from vaultdata.config import REPO_ROOT
from vaultdata.data.loader import DataLoadError, enrich
from vaultdata.data.audit import validate_sources

TRACK4_PATH = REPO_ROOT / 'data' / 'track4' / '04_business_money_leak'
TABLE_NAMES = ('customers', 'products', 'transactions', 'inventory', 'campaigns')

def load_sources(path: Path = TRACK4_PATH) -> dict[str, pd.DataFrame]:
    try:
        sources = {name: pd.read_csv(path / f'{name}.csv') for name in TABLE_NAMES}
        validate_sources(sources)
        return sources
    except (OSError, ValueError) as exc:
        raise DataLoadError(f'Could not load the official Track 4 files: {exc}') from exc

def prepare_transactions(sources: dict[str, pd.DataFrame]) -> pd.DataFrame:
    try:
        raw = sources['transactions'].merge(sources['customers'], on='customer_id', how='left', validate='many_to_one', indicator='_customer_join')
        raw = raw.merge(sources['products'], on='product_id', how='left', validate='many_to_one', indicator='_product_join')
        if (raw['_customer_join'] != 'both').any() or (raw['_product_join'] != 'both').any():
            raise DataLoadError('Some transactions have missing customer or product references.')
        raw = raw.drop(columns=['_customer_join', '_product_join'])
        raw['Date'] = pd.to_datetime(raw['timestamp'], errors='raise').dt.normalize()
        raw['Hour'] = pd.to_datetime(raw['timestamp'], errors='raise').dt.hour
        raw['Gross value'] = raw['quantity'] * raw['unit_price']
        raw['Discount value'] = raw['Gross value'] * raw['discount_pct']
        raw['Total'] = raw['Gross value'] - raw['Discount value']
        raw['cogs'] = raw['quantity'] * raw['unit_cost']
        raw['Estimated margin'] = raw['Total'] - raw['cogs']
        raw = raw.rename(columns={'transaction_id':'Invoice ID', 'category':'Product line', 'quantity':'Quantity', 'unit_price':'Unit price', 'customer_segment':'Customer type', 'payment_method':'Payment', 'region':'Region', 'channel':'Channel', 'status':'Status'})
        result = enrich(raw)
        result.attrs['source'] = 'track4'
        return result
    except (KeyError, ValueError, pd.errors.MergeError) as exc:
        raise DataLoadError(f'Invalid Track 4 joins or values: {exc}') from exc

def is_track4(df: pd.DataFrame) -> bool:
    return df.attrs.get('source') == 'track4'

def completed(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[df['Status'] == 'Completed'].copy() if is_track4(df) else df
