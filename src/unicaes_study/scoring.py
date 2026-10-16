"""Score the questionnaires from the released item responses.

The participants file already carries the scale totals; re-deriving them here lets anyone
check the scoring, and the item responses are needed for Cronbach's alpha (used by the
Reliable Change Index).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import constants as C


def item_columns(scale: str, timepoint: str) -> list[str]:
    return [f"{scale}_{timepoint}_{i:02d}" for i in range(1, C.N_ITEMS[scale] + 1)]


def score_scales(items: pd.DataFrame) -> pd.DataFrame:
    """Scale totals and the ADHD screen flag. A total is missing if any of its items is."""
    scores = items[[C.PARTICIPANT_ID]].copy()
    for t in C.TIMEPOINTS:
        asrs = items[item_columns(C.ASRS, t)]
        part_a = asrs.iloc[:, :C.ASRS_PART_A_N_ITEMS].sum(axis=1, min_count=C.ASRS_PART_A_N_ITEMS)
        scores[f"asrs_total_{t}"] = asrs.sum(axis=1, min_count=C.N_ITEMS[C.ASRS])
        scores[f"asrs_a_{t}"] = part_a
        scores[f"asrs_a_positive_{t}"] = (part_a >= C.ASRS_PART_A_CUTOFF).astype("Int64").where(
            part_a.notna()
        )
        se = items[item_columns(C.SELF_EFFICACY, t)]
        scores[f"se_{t}"] = se.sum(axis=1, min_count=C.N_ITEMS[C.SELF_EFFICACY])
    return scores


def cronbach_alpha(items: pd.DataFrame) -> float:
    """Cronbach's alpha on listwise-complete rows."""
    x = items.dropna(how="any").to_numpy(dtype=float)
    n_rows, k = x.shape
    if k < 2 or n_rows < 2:
        return float("nan")
    total_var = x.sum(axis=1).var(ddof=1)
    if not np.isfinite(total_var) or total_var <= 0:
        return float("nan")
    return (k / (k - 1)) * (1.0 - float(x.var(axis=0, ddof=1).sum() / total_var))


def baseline_reliabilities(items: pd.DataFrame) -> dict[str, float]:
    """Baseline (pre) Cronbach's alpha for each outcome."""
    return {
        outcome: cronbach_alpha(items[item_columns(meta["scale"], "pre")])
        for outcome, meta in C.OUTCOMES.items()
    }


def find_score_mismatches(participants: pd.DataFrame, items: pd.DataFrame) -> list[str]:
    """Columns where the released totals disagree with the item re-scoring (should be none)."""
    rescored = score_scales(items).set_index(C.PARTICIPANT_ID)
    released = participants.set_index(C.PARTICIPANT_ID)
    return [
        col for col in rescored.columns
        if not rescored[col].astype("Float64").equals(
            released.loc[rescored.index, col].astype("Float64")
        )
    ]
