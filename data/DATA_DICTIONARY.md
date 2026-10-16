# Data dictionary

Three files. Each participant is identified only by an anonymous `participant_id`
(`P01`…`P65`) that links the two participant-level files.

| File | Rows | Contents |
|---|---|---|
| `unicaes_2024_participants.csv` | 65 | Scale totals, ADHD screen flags, exposure window and engagement counts |
| `unicaes_2024_item_responses.csv` | 65 | Numeric responses to every questionnaire item, pre and post |
| `cohort_demographics.csv` | 11 | Cohort-level demographic aggregates (no row-level demographics are released) |

## De-identification

These files contain no direct identifiers and have been checked for indirect ones:

| Removed or coarsened | Why |
|---|---|
| Focus Bear account ID, email address, full name | Direct identifiers. |
| Survey timestamps | Quasi-identifiers. Only the number of days between the two surveys is kept, rounded to a whole day. |
| Per-week engagement rates | An exact rate divided into its count reconstructs the unrounded window, so rates are not released. `scripts/run_analysis.py` recomputes them from the counts and the rounded window. |
| Age, gender, year of study | 29 of 65 participants completed the demographics form, and 8 of those 29 had a unique combination of the three. Only cohort aggregates are released (`cohort_demographics.csv`). These variables are not used in any analysis. |

The mapping from `participant_id` to app accounts is held privately by Focus Bear and is not
part of this release. `tests/test_dataset.py` checks every release file for identifier-shaped
values and for withheld columns.

## `unicaes_2024_participants.csv`

| Column | Type | Description |
|---|---|---|
| `participant_id` | string | Anonymous ID (`P01`…`P65`). |
| `asrs_total_pre`, `asrs_total_post` | int, 0–72 | ADHD symptom severity: sum of all 18 ASRS v1.1 items (Never = 0 … Very often = 4). Lower = fewer symptoms. **Primary ADHD outcome.** |
| `asrs_a_pre`, `asrs_a_post` | int, 0–24 | ASRS Part A total (items 1–6). |
| `asrs_a_positive_pre`, `asrs_a_positive_post` | 0/1 | ADHD screen positive: Part A total ≥ 14 (Kessler et al., 2007). |
| `se_pre`, `se_post` | int, 10–40 | Academic self-efficacy: sum of 10 EAPESA items (Never = 1 … Always = 4). Higher = greater self-efficacy. **Primary self-efficacy outcome.** |
| `window_days` | int | Days between the pre and post surveys, rounded to a whole day. This is the exposure window for the engagement counts. |
| `total_events` | int | Deliberate Focus Bear engagement events in the window (see below). |
| `focus_events` | int | Focus-mode events in the window: starting a focus session manually or completing one. |
| `habit_events` | int | Morning/evening routine events in the window: starting or completing a routine or a routine activity. |
| `other_events` | int | All other deliberate events in the window. `total_events = focus_events + habit_events + other_events`. |
| `active_days` | int | Distinct calendar days with at least one event in the window. |

### How engagement events were counted

Counts come from the Focus Bear app's event log for each participant's account, restricted
to the participant's own pre→post window. Automated or background events (periodic
background blocking, notifications received, backend errors and timeouts), onboarding events
and daily-usage marker events are excluded, so the counts reflect deliberate use of the app.

## `unicaes_2024_item_responses.csv`

`participant_id` plus one column per item, named `<scale>_<time>_<item>`:

| Columns | Scale | Coding |
|---|---|---|
| `asrs_pre_01` … `asrs_pre_18`, `asrs_post_01` … `asrs_post_18` | ASRS v1.1, items 1–18 in standard order (1–6 = Part A) | Never 0, Rarely 1, Sometimes 2, Often 3, Very often 4 |
| `se_pre_01` … `se_pre_10`, `se_post_01` … `se_post_10` | EAPESA academic self-efficacy, items 1–10 | Never 1, Sometimes 2, Often 3, Always 4 |

All 65 participants answered every item at both time points. The scale totals in the
participants file are the sums of these items (checked by `tests/test_dataset.py`).

## `cohort_demographics.csv`

`statistic,value` pairs: participants with demographics (`n_with_demographics`) out of the
cohort (`n_cohort`); age mean, SD, median, minimum and maximum; counts by gender (`F`/`M`)
and by year of study.
