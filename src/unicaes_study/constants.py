"""Study constants: file locations, scale definitions, outcome metadata, dose families."""

from __future__ import annotations

from pathlib import Path

# --- Paths ------------------------------------------------------------------------
REPO_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_DIR / "data"
RESULTS_DIR = REPO_DIR / "results"
FIGURES_SUBDIR = "figures"

PARTICIPANTS_CSV = DATA_DIR / "unicaes_2024_participants.csv"
ITEM_RESPONSES_CSV = DATA_DIR / "unicaes_2024_item_responses.csv"

PARTICIPANT_ID = "participant_id"

# --- Scales -----------------------------------------------------------------------
# Item columns are named <scale>_<time>_<NN>, e.g. asrs_pre_01, se_post_10.
ASRS = "asrs"
SELF_EFFICACY = "se"
TIMEPOINTS = ("pre", "post")
N_ITEMS = {ASRS: 18, SELF_EFFICACY: 10}
ASRS_PART_A_N_ITEMS = 6                    # Part A = the first six ASRS items

# ADHD screen: ASRS Part A total >= 14 (Kessler et al., 2007).
ASRS_PART_A_CUTOFF = 14

# --- Outcomes ---------------------------------------------------------------------
# "beneficial" is the direction of an improvement: ADHD symptoms should go down,
# self-efficacy up. "scale" links each outcome to its item columns.
OUTCOMES = {
    "asrs_total": {
        "scale": ASRS,
        "pre": "asrs_total_pre", "post": "asrs_total_post",
        "label": "ADHD symptoms (ASRS, 18 items)", "beneficial": "decrease",
        "score_range": (0, 72),
    },
    "self_efficacy": {
        "scale": SELF_EFFICACY,
        "pre": "se_pre", "post": "se_post",
        "label": "Academic self-efficacy (10 items)", "beneficial": "increase",
        "score_range": (10, 40),
    },
}

# --- Engagement dose --------------------------------------------------------------
WINDOW_DAYS = "window_days"
DAYS_PER_WEEK = 7.0
EVENT_COUNT_COLS = ["total_events", "focus_events", "habit_events", "other_events"]
# One dose-response model per outcome x dose family.
DOSE_FAMILIES = ["total_events", "focus_events", "habit_events"]
LOG_Z_SUFFIX = "_logz"                     # primary predictor: z(log1p(events per week))
RAW_Z_SUFFIX = "_z"                        # sensitivity predictor: z(events per week)

# --- Inference --------------------------------------------------------------------
RCI_CRITICAL = 1.96                        # two-sided 95% (Jacobson & Truax, 1991)
MIN_ANCOVA_N = 10
MIN_RESPONDERS_FOR_LOGIT = 3
