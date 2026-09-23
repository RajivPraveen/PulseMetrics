# Experimentation

The included experiment asks whether a redesigned onboarding experience increases activation within seven days of trial start.

## Population and outcome

Every demo customer is assigned once to `control` or `treatment`. Only trial users whose seven-day outcome window has closed enter the analysis. Conversion is a recorded `activated` event within seven days of trial start.

## What the engine reports

- Control and treatment sample sizes and conversion counts
- Conversion rates, absolute difference in percentage points, and relative lift
- Two-sided z-test p-value and a 95% Newcombe interval for the absolute difference
- Cohen's h as a standardized effect size
- Minimum detectable positive difference at 80% target power
- Design power for a 3 percentage point practical threshold
- A recommendation that checks statistical and practical significance

The result is saved as JSON in `analytics.experiment_results`, then displayed on the Experimentation page. The example images in the README show one deterministic synthetic run; rerunning the generator with different options can change the numbers.

## Interpretation

A small p-value only addresses evidence against equal conversion rates. The interval shows plausible effect sizes; the practical threshold says how large a gain would matter to the product. The displayed power is calculated for that threshold, rather than from the observed lift. This demo uses one primary outcome and one experiment. A system that monitors many tests or stops early needs a multiple-testing or sequential-testing policy before it should make automated launch decisions.

See the exact formula choices in [KPI definitions](KPI_DEFINITIONS.md) and the implementation in `src/pulsemetrics/experiments.py`.
