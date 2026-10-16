import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vaultdata.data.loader import load_dataset  # noqa: E402


@pytest.fixture(scope="session")
def demo_df() -> pd.DataFrame:
    return load_dataset()
