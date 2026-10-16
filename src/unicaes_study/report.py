"""Figures and the Markdown results summary."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

from . import constants as C  # noqa: E402

FIGURE_SIZE = (6, 5)
FIGURE_DPI = 120
P_DISPLAY_FLOOR = 0.001
PRIMARY_DOSE_COL = f"total_events{C.LOG_Z_SUFFIX}"
SPARSE_DOSE_FAMILY = "focus_events"


def fmt_p(p: float) -> str:
    if pd.isna(p):
        return "n/a"
    return f"<{P_DISPLAY_FLOOR}" if p < P_DISPLAY_FLOOR else f"{p:.3f}"


def _fmt_ci(row: pd.Series, decimals: int = 3) -> str:
    if pd.isna(row.get("ci_low")):
        return "n/a"
    return f"[{row['ci_low']:+.{decimals}f}, {row['ci_high']:+.{decimals}f}]"


def _dose_name(dose_col: str) -> str:
    return dose_col.removesuffix(C.LOG_Z_SUFFIX)


# --- Figures ----------------------------------------------------------------------
def _save(fig, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=FIGURE_DPI)
    plt.close(fig)


def plot_pre_post(wide: pd.DataFrame, figures_dir: Path) -> None:
    for outcome, meta in C.OUTCOMES.items():
        scores = wide[[meta["pre"], meta["post"]]].dropna().melt(var_name="Time", value_name="Score")
        scores["Time"] = scores["Time"].map({meta["pre"]: "Pre", meta["post"]: "Post"})
        fig, ax = plt.subplots(figsize=FIGURE_SIZE)
        sns.boxplot(data=scores, x="Time", y="Score", order=["Pre", "Post"], ax=ax)
        sns.stripplot(data=scores, x="Time", y="Score", order=["Pre", "Post"],
                      color="0.3", alpha=0.5, ax=ax)
        ax.set_title(meta["label"])
        _save(fig, figures_dir / f"prepost_{outcome}.png")


def plot_dose_change(wide: pd.DataFrame, figures_dir: Path) -> None:
    for outcome, meta in C.OUTCOMES.items():
        data = wide[[meta["pre"], meta["post"], PRIMARY_DOSE_COL]].dropna()
        data["change"] = data[meta["post"]] - data[meta["pre"]]
        fig, ax = plt.subplots(figsize=FIGURE_SIZE)
        sns.regplot(data=data, x=PRIMARY_DOSE_COL, y="change", ax=ax,
                    scatter_kws={"alpha": 0.6}, line_kws={"color": "crimson"})
        ax.axhline(0, color="0.6", lw=1, ls="--")
        ax.set_xlabel("Total engagement events (log per week, z)")
        ax.set_ylabel("Change (post − pre)")
        ax.set_title(f"Dose-response: {meta['label']}")
        _save(fig, figures_dir / f"dose_change_{outcome}.png")


# --- Summary sections -------------------------------------------------------------
def _section_pre_post(desc: pd.DataFrame, lmm_pp: pd.DataFrame) -> list[str]:
    lines = [
        "\n## 1. Did outcomes change from pre to post?\n",
        "Linear mixed model `score ~ time + (1 | participant)`; the `time` coefficient is the "
        "pre→post change.\n",
        "| Outcome | n | Pre (M±SD) | Post (M±SD) | Δ (post−pre) | 95% CI | p | Cohen's dz |",
        "|---|---|---|---|---|---|---|---|",
    ]
    desc = desc.set_index("outcome")
    for _, r in lmm_pp.iterrows():
        d = desc.loc[r["outcome"]]
        lines.append(
            f"| {r['label']} | {r['n_participants']} | {d['pre_mean']:.1f}±{d['pre_sd']:.1f} | "
            f"{d['post_mean']:.1f}±{d['post_sd']:.1f} | {r['time_coef']:+.2f} | "
            f"{_fmt_ci(r, 2)} | {fmt_p(r['p'])} | {d['cohen_dz']:+.2f} |"
        )
    lines.append("\n_ADHD symptoms improve if Δ is negative; self-efficacy improves if Δ is "
                 "positive._\n")
    return lines


def _section_adhd_screen(adhd: dict) -> list[str]:
    return [
        f"\n## 2. ADHD screen (ASRS Part A total ≥ {adhd['cutoff']}; Kessler et al., 2007)\n",
        f"- **Pre:** {adhd['pos_pre']}/{adhd['n_pre']} screen positive ({adhd['pct_pre']:.1f}%). "
        f"**Post:** {adhd['pos_post']}/{adhd['n_post']} ({adhd['pct_post']:.1f}%).",
        f"- Paired (n={adhd['n_paired']}): {adhd['pos_to_neg']} moved positive→negative, "
        f"{adhd['neg_to_pos']} negative→positive; McNemar exact p={fmt_p(adhd['mcnemar_p'])}.",
    ]


def _section_dose(lmm_d: pd.DataFrame, anc: pd.DataFrame) -> list[str]:
    lines = [
        "\n## 3. Does more engagement predict more improvement?\n",
        "### 3a. LMM `score ~ time * dose + (1 | participant)`\n",
        "The `time × dose` interaction is the dose-response. FDR (Benjamini-Hochberg) across "
        "the six tests.\n",
        "| Outcome | Dose family | time × dose | 95% CI | p | p (FDR) |",
        "|---|---|---|---|---|---|",
    ]
    for _, r in lmm_d.iterrows():
        lines.append(
            f"| {r['label']} | {_dose_name(r['dose'])} | {r['interaction_coef']:+.3f} | "
            f"{_fmt_ci(r)} | {fmt_p(r['p'])} | {fmt_p(r['p_fdr'])} |"
        )
    lines += [
        "\n### 3b. Baseline-adjusted ANCOVA `post ~ pre + dose`\n",
        "FDR across the six tests; HC3 = heteroscedasticity-robust p.\n",
        "| Outcome | Dose family | dose β | 95% CI | partial η² | p | p (HC3) | p (FDR) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for _, r in anc.iterrows():
        lines.append(
            f"| {r['label']} | {_dose_name(r['dose'])} | {r['dose_coef']:+.3f} | {_fmt_ci(r)} | "
            f"{r['partial_eta2']:.3f} | {fmt_p(r['p'])} | {fmt_p(r['p_hc3'])} | "
            f"{fmt_p(r['p_fdr'])} |"
        )
    return lines


def _section_rci(rci_summary: pd.DataFrame, rci_logit: pd.DataFrame) -> list[str]:
    lines = [
        "\n## 4. Reliable Change Index (Jacobson & Truax, 1991)\n",
        "Reliable change uses baseline internal consistency (Cronbach's α, computed from the "
        "item responses). |RCI| > 1.96 marks change beyond measurement error.\n",
        "| Outcome | n | α (pre) | RCI threshold (points) | Reliably improved | Reliably worsened |",
        "|---|---|---|---|---|---|",
    ]
    for _, r in rci_summary.iterrows():
        lines.append(
            f"| {r['label']} | {int(r['n'])} | {r['reliability']:.2f} | "
            f"{r['rci_threshold_points']:.1f} | {int(r['n_improved'])} "
            f"({r['pct_improved']:.0f}%) | {int(r['n_deteriorated'])} "
            f"({r['pct_deteriorated']:.0f}%) |"
        )
    lines += [
        "\nDoes engagement predict being a reliable improver? Logistic regression, "
        "FDR-corrected:\n",
        "| Outcome | Dose family | Reliable improvers | OR per 1 SD | p | p (FDR) |",
        "|---|---|---|---|---|---|",
    ]
    for _, r in rci_logit.iterrows():
        odds_ratio = f"{r['odds_ratio']:.2f}" if pd.notna(r.get("odds_ratio")) else "n/a"
        lines.append(
            f"| {r['label']} | {_dose_name(r['dose'])} | {int(r['n_responders'])} | "
            f"{odds_ratio} | {fmt_p(r.get('p'))} | {fmt_p(r.get('p_fdr'))} |"
        )
    return lines


def _section_bottom_line(wide: pd.DataFrame, lmm_d: pd.DataFrame, anc: pd.DataFrame,
                         n: int) -> list[str]:
    any_significant = bool(lmm_d["significant_fdr"].any() or anc["significant_fdr"].any())
    dose_line = (
        "- At least one dose-response effect survived FDR correction; see Section 3."
        if any_significant else
        "- **No dose-response effect survived FDR correction** in either the LMM or the ANCOVA: "
        "in this sample, more Focus Bear engagement was not associated with greater "
        "improvement in ADHD symptoms or self-efficacy."
    )
    n_without_focus = int((wide[SPARSE_DOSE_FAMILY] == 0).sum())
    return [
        "\n## 5. Interpretation\n",
        dose_line,
        "- The pre→post changes in Section 1 describe within-person change over time. With "
        "**no control group** they cannot be attributed to Focus Bear: maturation, repeated "
        "testing and regression to the mean are uncontrolled.",
        f"- **Power:** n = {n} is small, so the null dose-response results may reflect limited "
        f"power as much as a true absence of effect. Focus-mode events were sparse "
        f"({n_without_focus} of {len(wide)} participants had none), so that dose family is "
        "especially underpowered.",
    ]


def write_summary(path: Path, *, wide, desc, lmm_pp, lmm_d, anc, adhd, rci_summary, rci_logit) -> None:
    n = int(lmm_pp["n_participants"].max())
    lines = [
        "# UNICAES 2024: results\n",
        "_Generated by `scripts/run_analysis.py` from the de-identified dataset in `data/`. "
        "Do not edit by hand._\n",
        f"Single-arm pre/post study, n = {n} students with complete pre and post surveys. "
        "All p-values two-sided. Dose = log1p(Focus Bear engagement events per week during "
        "each participant's pre→post window), z-scored.\n",
        *_section_pre_post(desc, lmm_pp),
        *_section_adhd_screen(adhd),
        *_section_dose(lmm_d, anc),
        *_section_rci(rci_summary, rci_logit),
        *_section_bottom_line(wide, lmm_d, anc, n),
        "\n_Full tables: `results/*.csv`. Figures: `results/figures/`._\n",
    ]
    path.write_text("\n".join(lines))
