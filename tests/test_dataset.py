"""Guards on the released data: no identifiers, expected schema, internally consistent scores."""

from __future__ import annotations

import re

import pandas as pd
import pytest

from unicaes_study import constants as C
from unicaes_study import scoring

DATA_FILES = sorted(C.DATA_DIR.glob("*.csv"))
PARTICIPANT_ID_PATTERN = re.compile(r"^P\d{2,}$")
IDENTIFIER_PATTERNS = {
    "uuid": re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I),
    "email": re.compile(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", re.I),
    "date": re.compile(r"\d{4}-\d{2}-\d{2}"),
}
# Row-level quasi-identifiers that were deliberately withheld (see data/DATA_DICTIONARY.md).
WITHHELD_COLUMNS = {"user_id", "email", "name", "age", "gender", "academic_year",
                    "pre_date", "post_date"}


@pytest.fixture(scope="module")
def participants() -> pd.DataFrame:
    return pd.read_csv(C.PARTICIPANTS_CSV)


@pytest.fixture(scope="module")
def items() -> pd.DataFrame:
    return pd.read_csv(C.ITEM_RESPONSES_CSV)


@pytest.mark.parametrize("path", DATA_FILES, ids=lambda p: p.name)
def test_no_identifier_shaped_values(path):
    text = path.read_text()
    for label, pattern in IDENTIFIER_PATTERNS.items():
        assert not pattern.search(text), f"{label}-like value in {path.name}"


@pytest.mark.parametrize("path", DATA_FILES, ids=lambda p: p.name)
def test_no_withheld_columns(path):
    leaked = WITHHELD_COLUMNS & set(pd.read_csv(path, nrows=0).columns)
    assert not leaked, f"{path.name} contains withheld columns {leaked}"


def test_participant_ids_are_anonymous_and_unique(participants, items):
    for frame in (participants, items):
        ids = frame[C.PARTICIPANT_ID]
        assert ids.is_unique
        assert ids.map(lambda v: bool(PARTICIPANT_ID_PATTERN.match(v))).all()
    assert set(participants[C.PARTICIPANT_ID]) == set(items[C.PARTICIPANT_ID])


def test_window_is_whole_days(participants):
    """Fractional windows would encode the exact survey timestamps."""
    assert pd.api.types.is_integer_dtype(participants[C.WINDOW_DAYS])
    assert (participants[C.WINDOW_DAYS] > 0).all()


def test_no_precomputed_rates(participants):
    """Exact per-week rates divided into counts would reconstruct the unrounded window."""
    assert not [c for c in participants.columns if c.endswith("_per_week")]


def test_released_totals_match_item_scoring(participants, items):
    assert scoring.find_score_mismatches(participants, items) == []


def test_scores_within_scale_range(participants):
    for meta in C.OUTCOMES.values():
        low, high = meta["score_range"]
        for col in (meta["pre"], meta["post"]):
            assert participants[col].between(low, high).all(), col
