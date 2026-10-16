"""Reproduce every result in results/ from the de-identified dataset in data/.

Usage:  python scripts/run_analysis.py [--results-dir results]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from unicaes_study import constants as C
from unicaes_study import dose, models, report, scoring


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--results-dir", type=Path, default=C.RESULTS_DIR)
    return parser.parse_args()


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    participants = pd.read_csv(C.PARTICIPANTS_CSV)
    items = pd.read_csv(C.ITEM_RESPONSES_CSV)
    mismatches = scoring.find_score_mismatches(participants, items)
    if mismatches:
        raise SystemExit(f"Released totals disagree with item re-scoring: {mismatches}")
    return participants, items


def run_per_dose(fit, frame: pd.DataFrame, suffix: str = C.LOG_Z_SUFFIX) -> pd.DataFrame:
    """One model per outcome x dose family, FDR-corrected across the table."""
    rows = [fit(frame, outcome, f"{family}{suffix}")
            for outcome in C.OUTCOMES for family in C.DOSE_FAMILIES]
    return models.add_fdr(pd.DataFrame(rows))


def combine_dose_tables(lmm_d: pd.DataFrame, anc: pd.DataFrame) -> pd.DataFrame:
    lmm_part = lmm_d[["outcome", "label", "dose", "interaction_coef", "p", "p_fdr"]].rename(
        columns={"interaction_coef": "lmm_coef", "p": "lmm_p", "p_fdr": "lmm_p_fdr"}
    )
    anc_part = anc[["outcome", "dose", "dose_coef", "p", "p_fdr"]].rename(
        columns={"dose_coef": "ancova_beta", "p": "ancova_p", "p_fdr": "ancova_p_fdr"}
    )
    combined = lmm_part.merge(anc_part, on=["outcome", "dose"], how="left")
    combined["dose"] = combined["dose"].str.removesuffix(C.LOG_Z_SUFFIX)
    return combined


def run_reliable_change(wide: pd.DataFrame, items: pd.DataFrame):
    reliabilities = scoring.baseline_reliabilities(items)
    summaries, responders = [], {}
    for outcome in C.OUTCOMES:
        responders[outcome], summary = models.reliable_change(
            wide, outcome, reliabilities[outcome]
        )
        summaries.append(summary)
    logit_rows = [
        models.rci_responder_dose(wide, responders[outcome], outcome,
                                  f"{family}{C.LOG_Z_SUFFIX}")
        for outcome in C.OUTCOMES for family in C.DOSE_FAMILIES
    ]
    return pd.DataFrame(summaries), models.add_fdr(pd.DataFrame(logit_rows))


def main() -> None:
    args = parse_args()
    results_dir = args.results_dir
    figures_dir = results_dir / C.FIGURES_SUBDIR
    figures_dir.mkdir(parents=True, exist_ok=True)

    participants, items = load_data()
    wide = dose.add_dose_predictors(participants)
    long = models.to_long(wide)

    desc = pd.DataFrame([models.pre_post_summary(wide, k) for k in C.OUTCOMES])
    lmm_pp = pd.DataFrame([models.lmm_pre_post(long, k) for k in C.OUTCOMES])
    adhd = models.adhd_screen_summary(wide)
    lmm_d = run_per_dose(models.lmm_dose, long)
    anc = run_per_dose(models.ancova_dose, wide)
    anc_raw = run_per_dose(models.ancova_dose, wide, suffix=C.RAW_Z_SUFFIX)
    rci_summary, rci_logit = run_reliable_change(wide, items)

    tables = {
        "descriptives_prepost": desc,
        "lmm_prepost": lmm_pp,
        "adhd_screen": pd.DataFrame([adhd]),
        "lmm_dose_response": lmm_d,
        "ancova_dose": anc,
        "ancova_dose_sensitivity_raw": anc_raw,
        "dose_response_table": combine_dose_tables(lmm_d, anc),
        "rci_summary": rci_summary,
        "rci_dose_logit": rci_logit,
    }
    for name, table in tables.items():
        table.to_csv(results_dir / f"{name}.csv", index=False)

    report.plot_pre_post(wide, figures_dir)
    report.plot_dose_change(wide, figures_dir)
    report.write_summary(
        results_dir / "results_summary.md", wide=wide, desc=desc, lmm_pp=lmm_pp, lmm_d=lmm_d, anc=anc,
        adhd=adhd, rci_summary=rci_summary, rci_logit=rci_logit,
    )
    print(f"Wrote {len(tables)} tables, figures and results_summary.md to {results_dir}")


if __name__ == "__main__":
    main()
