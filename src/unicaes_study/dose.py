"""Engagement-dose predictors.

Dose = Focus Bear engagement events per week during each participant's pre->post window.
Counts are right-skewed, so the primary predictor is log1p(events per week), z-scored on the
analysis sample; the untransformed rate (z-scored) is a sensitivity analysis.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import constants as C


def zscore(values: pd.Series) -> pd.Series:
    values = pd.to_numeric(values, errors="coerce")
    sd = values.std(ddof=1)
    if not sd or not np.isfinite(sd):
        return values * 0.0
    return (values - values.mean()) / sd


def add_dose_predictors(participants: pd.DataFrame) -> pd.DataFrame:
    """Add <family>_per_week, <family>_logz and <family>_z columns."""
    out = participants.copy()
    weeks = (out[C.WINDOW_DAYS] / C.DAYS_PER_WEEK).where(lambda w: w > 0)
    for family in C.EVENT_COUNT_COLS:
        out[f"{family}_per_week"] = out[family] / weeks
    for family in C.DOSE_FAMILIES:
        per_week = out[f"{family}_per_week"].astype(float)
        out[f"{family}{C.LOG_Z_SUFFIX}"] = zscore(np.log1p(per_week))
        out[f"{family}{C.RAW_Z_SUFFIX}"] = zscore(per_week)
    return out
