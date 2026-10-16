"""End-to-end: the analysis runs from data/ alone and reproduces the committed results."""

from __future__ import annotations

import subprocess
import sys

import pandas as pd
import pytest

from unicaes_study import constants as C

RUN_ANALYSIS = C.REPO_DIR / "scripts" / "run_analysis.py"
# Mixed-model and logit optimisers can differ in late decimals
# across platforms and library versions.
TOLERANCE = 1e-4


@pytest.fixture(scope="module")
def fresh_results(tmp_path_factory):
    out = tmp_path_factory.mktemp("results")
    subprocess.run([sys.executable, str(RUN_ANALYSIS), "--results-dir", str(out)], check=True)
    return out


@pytest.mark.parametrize("table", sorted(p.stem for p in C.RESULTS_DIR.glob("*.csv")))
def test_committed_results_are_reproducible(fresh_results, table):
    committed = pd.read_csv(C.RESULTS_DIR / f"{table}.csv")
    regenerated = pd.read_csv(fresh_results / f"{table}.csv")
    pd.testing.assert_frame_equal(committed, regenerated, check_exact=False, rtol=TOLERANCE)


def test_summary_and_figures_written(fresh_results):
    assert (fresh_results / "results_summary.md").exists()
    assert len(list((fresh_results / C.FIGURES_SUBDIR).glob("*.png"))) == 2 * len(C.OUTCOMES)
