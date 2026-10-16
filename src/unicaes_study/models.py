"""Statistical models.

Design: single-arm pre/post (no control group). Two questions:
  1. Did each outcome change from pre to post?   -> within-subject LMM (random intercept).
  2. Does more Focus Bear engagement predict greater improvement?
       - LMM dose-response:        score ~ time * dose + (1 | participant)
       - Baseline-adjusted ANCOVA: post ~ pre + dose
       - Reliable-improver logit:  P(reliable improvement) ~ dose
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.outliers_influence import variance_inflation_factor

from . import constants as C

PID = C.PARTICIPANT_ID
ERROR_MESSAGE_MAX_CHARS = 120


def to_long(wide: pd.DataFrame) -> pd.DataFrame:
    """Two rows per participant per outcome (time 0 = pre, 1 = post), carrying the dose columns."""
    dose_cols = [f"{family}{C.LOG_Z_SUFFIX}" for family in C.DOSE_FAMILIES]
    parts = []
    for outcome, meta in C.OUTCOMES.items():
        for time_value, col in [(0, meta["pre"]), (1, meta["post"])]:
            part = wide[[PID, *dose_cols]].copy()
            part["outcome"] = outcome
            part["time"] = time_value
            part["score"] = pd.to_numeric(wide[col], errors="coerce")
            parts.append(part)
    return pd.concat(parts, ignore_index=True)


def _outcome_header(outcome: str) -> dict:
    return {"outcome": outcome, "label": C.OUTCOMES[outcome]["label"]}


# --- 1. Pre/post change -----------------------------------------------------------
def pre_post_summary(wide: pd.DataFrame, outcome: str) -> dict:
    """Descriptives, Cohen's dz, paired t-test and Wilcoxon signed-rank test."""
    meta = C.OUTCOMES[outcome]
    paired = wide[[meta["pre"], meta["post"]]].dropna()
    pre, post = paired[meta["pre"]], paired[meta["post"]]
    change = post - pre
    sd_change = change.std(ddof=1)
    t_test = stats.ttest_rel(post, pre)
    try:
        wilcoxon_p = float(stats.wilcoxon(post, pre).pvalue)
    except ValueError:
        wilcoxon_p = np.nan
    return {
        **_outcome_header(outcome), "n": int(len(paired)),
        "pre_mean": pre.mean(), "pre_sd": pre.std(ddof=1),
        "post_mean": post.mean(), "post_sd": post.std(ddof=1),
        "mean_change": change.mean(), "sd_change": sd_change,
        "cohen_dz": change.mean() / sd_change if sd_change else np.nan,
        "shapiro_change_p": stats.shapiro(change).pvalue if len(change) >= 3 else np.nan,
        "paired_t": float(t_test.statistic), "paired_t_p": float(t_test.pvalue),
        "wilcoxon_p": wilcoxon_p,
    }


def lmm_pre_post(long: pd.DataFrame, outcome: str) -> dict:
    """score ~ time + (1 | participant); the time coefficient is the adjusted pre->post change."""
    data = long[long["outcome"] == outcome].dropna(subset=["score"])
    fit = smf.mixedlm("score ~ time", data, groups=data[PID], re_formula="1").fit(
        method="lbfgs", reml=True
    )
    ci = fit.conf_int().loc["time"]
    re_var = float(fit.cov_re.iloc[0, 0])
    total_var = re_var + float(fit.scale)
    return {
        **_outcome_header(outcome),
        "n_obs": int(len(data)), "n_participants": int(data[PID].nunique()),
        "time_coef": float(fit.fe_params["time"]), "se": float(fit.bse_fe["time"]),
        "ci_low": float(ci[0]), "ci_high": float(ci[1]),
        "p": float(fit.pvalues["time"]),
        "icc": re_var / total_var if total_var > 0 else np.nan,
    }


def adhd_screen_summary(wide: pd.DataFrame) -> dict:
    """Screen-positive prevalence pre and post, and McNemar's exact test on paired status."""
    pre, post = wide["asrs_a_positive_pre"], wide["asrs_a_positive_post"]
    out = {
        "cutoff": C.ASRS_PART_A_CUTOFF,
        "n_pre": int(pre.notna().sum()), "pos_pre": int(pre.sum(skipna=True)),
        "n_post": int(post.notna().sum()), "pos_post": int(post.sum(skipna=True)),
    }
    out["pct_pre"] = 100 * out["pos_pre"] / out["n_pre"] if out["n_pre"] else np.nan
    out["pct_post"] = 100 * out["pos_post"] / out["n_post"] if out["n_post"] else np.nan

    both = wide[["asrs_a_positive_pre", "asrs_a_positive_post"]].dropna().astype(int)
    out["n_paired"] = int(len(both))
    out["pos_to_neg"] = int(((both.iloc[:, 0] == 1) & (both.iloc[:, 1] == 0)).sum())
    out["neg_to_pos"] = int(((both.iloc[:, 0] == 0) & (both.iloc[:, 1] == 1)).sum())
    if both.empty:
        out["mcnemar_p"] = np.nan
        return out
    table = pd.crosstab(both.iloc[:, 0], both.iloc[:, 1]).reindex(
        index=[0, 1], columns=[0, 1], fill_value=0
    ).to_numpy()
    out["mcnemar_p"] = float(mcnemar(table, exact=True).pvalue)
    return out


# --- 2. Dose-response -------------------------------------------------------------
def lmm_dose(long: pd.DataFrame, outcome: str, dose_col: str) -> dict:
    """score ~ time * dose + (1 | participant); time:dose is the dose-response term."""
    data = long[long["outcome"] == outcome].dropna(subset=["score", dose_col])
    term = f"time:{dose_col}"
    out = {**_outcome_header(outcome), "dose": dose_col,
           "n_participants": int(data[PID].nunique())}
    try:
        fit = smf.mixedlm(f"score ~ time * {dose_col}", data, groups=data[PID],
                          re_formula="1").fit(method="lbfgs", reml=True)
    except (ValueError, np.linalg.LinAlgError) as e:
        out.update({"interaction_coef": np.nan, "p": np.nan,
                    "error": str(e)[:ERROR_MESSAGE_MAX_CHARS]})
        return out
    ci = fit.conf_int()
    out.update({
        "interaction_coef": float(fit.fe_params[term]), "se": float(fit.bse_fe[term]),
        "ci_low": float(ci.loc[term, 0]), "ci_high": float(ci.loc[term, 1]),
        "p": float(fit.pvalues[term]),
        "dose_main_coef": float(fit.fe_params[dose_col]),
        "dose_main_p": float(fit.pvalues[dose_col]),
    })
    return out


def _ancova_diagnostics(fit) -> dict:
    resid = fit.resid
    exog = pd.DataFrame(fit.model.exog, columns=fit.model.exog_names)
    vifs = [variance_inflation_factor(exog.values, i)
            for i, name in enumerate(exog.columns) if name != "Intercept"]
    return {
        "shapiro_resid_p": float(stats.shapiro(resid).pvalue) if len(resid) >= 3 else np.nan,
        "breusch_pagan_p": float(het_breuschpagan(resid, fit.model.exog)[1]),
        "max_vif": float(np.nanmax(vifs)) if vifs else np.nan,
    }


def ancova_dose(wide: pd.DataFrame, outcome: str, dose_col: str) -> dict:
    """post ~ pre + dose, with partial eta-squared (Type III SS), HC3-robust p and diagnostics."""
    meta = C.OUTCOMES[outcome]
    data = wide[[meta["pre"], meta["post"], dose_col]].dropna()
    data.columns = ["pre", "post", "dose"]
    out = {**_outcome_header(outcome), "dose": dose_col, "n": int(len(data))}
    if len(data) < C.MIN_ANCOVA_N:
        out.update({"dose_coef": np.nan, "p": np.nan, "error": f"n<{C.MIN_ANCOVA_N}"})
        return out

    formula = "post ~ pre + dose"
    fit = smf.ols(formula, data=data).fit()
    robust = smf.ols(formula, data=data).fit(cov_type="HC3")
    ci = fit.conf_int().loc["dose"]
    aov = anova_lm(fit, typ=3)
    ss_dose, ss_resid = aov.loc["dose", "sum_sq"], aov.loc["Residual", "sum_sq"]
    out.update({
        "dose_coef": float(fit.params["dose"]), "se": float(fit.bse["dose"]),
        "ci_low": float(ci[0]), "ci_high": float(ci[1]),
        "p": float(fit.pvalues["dose"]), "p_hc3": float(robust.pvalues["dose"]),
        "partial_eta2": float(ss_dose / (ss_dose + ss_resid)),
        "baseline_coef": float(fit.params["pre"]), "r2": float(fit.rsquared),
        **_ancova_diagnostics(fit),
    })
    return out


# --- 3. Reliable Change Index (Jacobson & Truax, 1991) ------------------------------
def reliable_change(wide: pd.DataFrame, outcome: str, reliability: float):
    """Per-participant RCI and reliable-change classification.

    RCI = (post - pre) / S_diff, S_diff = sqrt(2) * SD_pre * sqrt(1 - reliability).
    |RCI| > 1.96 is change beyond measurement error; its sign is read against the outcome's
    beneficial direction. Returns (per_participant_df, summary_dict).
    """
    meta = C.OUTCOMES[outcome]
    data = wide[[PID, meta["pre"], meta["post"]]].dropna().copy()
    pre, post = data[meta["pre"]], data[meta["post"]]
    sd_pre = float(pre.std(ddof=1))
    s_diff = np.sqrt(2.0) * sd_pre * np.sqrt(max(0.0, 1.0 - reliability))
    data["rci"] = (post - pre) / s_diff if s_diff > 0 else np.nan

    improving_sign = -1 if meta["beneficial"] == "decrease" else 1
    signed_rci = improving_sign * data["rci"]
    data["reliable_improved"] = (signed_rci >= C.RCI_CRITICAL).astype(int)
    data["reliable_deteriorated"] = (signed_rci <= -C.RCI_CRITICAL).astype(int)

    n = len(data)
    n_improved = int(data["reliable_improved"].sum())
    n_deteriorated = int(data["reliable_deteriorated"].sum())
    summary = {
        **_outcome_header(outcome), "n": n,
        "reliability": reliability, "sd_pre": sd_pre, "s_diff": s_diff,
        "rci_threshold_points": C.RCI_CRITICAL * s_diff,
        "n_improved": n_improved, "n_deteriorated": n_deteriorated,
        "n_unchanged": n - n_improved - n_deteriorated,
        "pct_improved": 100.0 * n_improved / n if n else np.nan,
        "pct_deteriorated": 100.0 * n_deteriorated / n if n else np.nan,
    }
    return data[[PID, "rci", "reliable_improved", "reliable_deteriorated"]], summary


def rci_responder_dose(wide: pd.DataFrame, responders: pd.DataFrame,
                       outcome: str, dose_col: str) -> dict:
    """Logistic regression of reliable-improver status on dose; odds ratio per 1 SD of dose.

    Responder status is one classification per person, so a mixed model does not apply.
    """
    data = wide.merge(responders, on=PID)[["reliable_improved", dose_col]].dropna()
    out = {**_outcome_header(outcome), "dose": dose_col,
           "n": int(len(data)), "n_responders": int(data["reliable_improved"].sum())}
    if data["reliable_improved"].nunique() < 2 or out["n_responders"] < C.MIN_RESPONDERS_FOR_LOGIT:
        out.update({"odds_ratio": np.nan, "p": np.nan, "note": "too few responders to model"})
        return out
    fit = smf.logit(f"reliable_improved ~ {dose_col}", data=data).fit(disp=False)
    ci = fit.conf_int().loc[dose_col]
    out.update({
        "coef": float(fit.params[dose_col]),
        "odds_ratio": float(np.exp(fit.params[dose_col])),
        "or_ci_low": float(np.exp(ci[0])), "or_ci_high": float(np.exp(ci[1])),
        "p": float(fit.pvalues[dose_col]),
    })
    return out


# --- Multiple comparisons ---------------------------------------------------------
def add_fdr(results: pd.DataFrame, p_col: str = "p", out_col: str = "p_fdr") -> pd.DataFrame:
    """Benjamini-Hochberg FDR across the rows of one results table."""
    results = results.copy()
    has_p = results[p_col].notna()
    results[out_col] = np.nan
    results["significant_fdr"] = False
    if has_p.any():
        reject, p_adjusted, _, _ = multipletests(results.loc[has_p, p_col], method="fdr_bh")
        results.loc[has_p, out_col] = p_adjusted
        results.loc[has_p, "significant_fdr"] = reject
    return results
