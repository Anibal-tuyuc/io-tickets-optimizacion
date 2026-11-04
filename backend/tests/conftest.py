import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.etl.loader import load_dataset  # noqa: E402


@pytest.fixture(scope="session")
def ds():
    return load_dataset()
