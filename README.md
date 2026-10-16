# UNICAES 2024: Focus Bear pre/post study

De-identified data and analysis code for a single-arm pre/post study of
[Focus Bear](https://www.focusbear.io), a focus and routine app, with undergraduate students at
Universidad Católica de El Salvador (UNICAES) in 2024.

65 students completed questionnaires on ADHD symptoms (ASRS v1.1, 18 items) and academic
self-efficacy (EAPESA, 10 items) before and after a period of using the app (median 56 days
between surveys, range 21–76). App engagement during that window comes from the app's event log.

Every number in [`results/`](results/) can be regenerated from [`data/`](data/) with one command.

## Authors

- **Jeremy Nagel**, RMIT University and Focus Bear Pty Ltd
- **Andrea Cuéllar**, Focus Bear Pty Ltd
- **Hector Mena**, Universidad Católica de El Salvador (UNICAES), Santa Ana

To cite this repository, use [`CITATION.cff`](CITATION.cff) (GitHub's "Cite this repository" button).

## Findings

Full tables are in [`results/results_summary.md`](results/results_summary.md).

| Outcome (n = 65) | Pre M (SD) | Post M (SD) | Change [95% CI] | p | Cohen's dz |
|---|---|---|---|---|---|
| ADHD symptoms, ASRS total (lower is better) | 32.0 (10.2) | 29.1 (11.4) | −2.83 [−4.51, −1.15] | < .001 | −0.41 |
| Academic self-efficacy (higher is better) | 27.7 (5.3) | 29.5 (4.9) | +1.86 [+0.88, +2.85] | < .001 | +0.46 |

- **Both outcomes improved from pre to post.** The share of students screening positive for
  ADHD (ASRS Part A ≥ 14) fell from 36.9% to 26.2%, though this change was not significant
  (McNemar exact p = .143).
- **No dose-response.** Students who used Focus Bear more did not improve more. None of the 12
  dose-response tests (2 outcomes × 3 engagement measures × 2 models) survived false discovery
  rate correction.
- **Change beyond measurement error was uncommon for ADHD symptoms.** 6 of 65 students (9%)
  showed reliable improvement on the ASRS and 18 (28%) on self-efficacy (Jacobson–Truax RCI).

### Limitations

- **No control group.** The pre→post changes cannot be attributed to Focus Bear: maturation,
  repeated testing, the academic calendar and regression to the mean are all uncontrolled.
- **Small sample.** With n = 65 the null dose-response results may reflect limited power as
  much as a true absence of effect. Focus-mode use was sparse (33 of 65 students had none).
- **Self-report outcomes** only.

## Conflict of interest

Focus Bear Pty Ltd develops the app being evaluated and carried out this analysis. Jeremy
Nagel is Focus Bear's founder and Andrea Cuéllar works for Focus Bear. The data and code are
published so the analysis can be checked independently.

## Repository layout

```
data/                     de-identified dataset + DATA_DICTIONARY.md
src/unicaes_study/        scoring, dose predictors, statistical models, report writer
scripts/run_analysis.py   data/ -> results/
results/                  tables (CSV), figures, results_summary.md (generated, committed)
tests/                    privacy checks on data/ and a reproducibility check on results/
```

## Reproducing the results

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # exact versions used for results/
pip install -e .
python scripts/run_analysis.py    # rewrites results/
pytest                            # privacy checks + regenerated results match committed ones
```

## Data

See [`data/DATA_DICTIONARY.md`](data/DATA_DICTIONARY.md) for every column and for how the data
were de-identified. In short: no names, emails, account IDs or survey dates; the survey window
is rounded to whole days; and age, gender and year of study are released only as cohort
aggregates, because several combinations were unique to one student.

## Methods

**Outcomes.** Scale totals are summed from the item responses, which are released so the
scoring can be checked. The ADHD screen uses the ASRS Part A total ≥ 14 (Kessler et al., 2007).

**Pre→post change.** Linear mixed model `score ~ time + (1 | participant)`, with paired t-test,
Wilcoxon signed-rank test and Cohen's dz alongside. Change in ADHD screen status uses McNemar's
exact test.

**Engagement dose.** Deliberate app events per week during each student's pre→post window
(automated, background and onboarding events excluded), in three families: all events,
focus-mode events and routine (habit) events. Rates are log1p-transformed and z-scored.
A sensitivity analysis uses untransformed rates.

**Dose-response.** Two models per outcome and dose family, each corrected with the
Benjamini–Hochberg false discovery rate across its six tests:

- Mixed model `score ~ time * dose + (1 | participant)`, where the `time × dose` interaction is
  the dose-response.
- Baseline-adjusted ANCOVA `post ~ pre + dose`, with HC3-robust p-values and residual
  diagnostics.

**Reliable change.** Jacobson–Truax Reliable Change Index using baseline Cronbach's α computed
from the items (ASRS α = 0.85, self-efficacy α = 0.90). Logistic regression tests whether
engagement predicts being a reliable improver.

All tests are two-sided.

## References

- Jacobson, N. S., & Truax, P. (1991). Clinical significance: A statistical approach to defining
  meaningful change in psychotherapy research. *Journal of Consulting and Clinical Psychology,
  59*(1), 12–19. https://doi.org/10.1037/0022-006X.59.1.12
- Kessler, R. C., Adler, L., Ames, M., et al. (2005). The World Health Organization Adult ADHD
  Self-Report Scale (ASRS): a short screening scale for use in the general population.
  *Psychological Medicine, 35*(2), 245–256. https://doi.org/10.1017/S0033291704002892
- Kessler, R. C., Adler, L. A., Gruber, M. J., Sarawate, C. A., Spencer, T., & Van Brunt, D. L.
  (2007). Validity of the World Health Organization Adult ADHD Self-Report Scale (ASRS) Screener
  in a representative sample of health plan members. *International Journal of Methods in
  Psychiatric Research, 16*(2), 52–65. https://doi.org/10.1002/mpr.208
- Palenzuela, D. L. (1983). Construcción y validación de una escala de autoeficacia percibida
  específica de situaciones académicas. *Análisis y Modificación de Conducta, 9*(21), 185–219.

## Licence

Code: [MIT](LICENSE). Data and results: [CC BY 4.0](data/LICENSE.md).
