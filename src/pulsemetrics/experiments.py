"""Two-arm activation experiment with uncertainty, power and practical significance."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass

import numpy as np
import psycopg
from dotenv import load_dotenv
from scipy.optimize import brentq
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import (
    confint_proportions_2indep,
    proportion_effectsize,
    proportions_ztest,
)


@dataclass
class ExperimentResult:
    experiment_name: str
    control_n: int
    treatment_n: int
    control_converted: int
    treatment_converted: int
    control_rate: float
    treatment_rate: float
    absolute_lift: float
    relative_lift: float | None
    ci_low: float
    ci_high: float
    p_value: float
    mde_absolute: float
    design_power: float
    practical_threshold: float
    cohen_h: float
    recommendation: str


def analyze(
    control_converted: int,
    control_n: int,
    treatment_converted: int,
    treatment_n: int,
    *,
    name: str = "onboarding_redesign_v1",
    alpha: float = 0.05,
    target_power: float = 0.80,
    practical_threshold: float = 0.03,
) -> ExperimentResult:
    if min(control_n, treatment_n) < 2:
        raise ValueError("Each variant needs at least two eligible users")
    if not (0 <= control_converted <= control_n and 0 <= treatment_converted <= treatment_n):
        raise ValueError("Conversions must be between zero and sample size")
    p0 = control_converted / control_n
    p1 = treatment_converted / treatment_n
    diff = p1 - p0
    _, p_value = proportions_ztest(
        [treatment_converted, control_converted], [treatment_n, control_n]
    )
    if np.isnan(p_value):
        p_value = 1.0
    ci_low, ci_high = confint_proportions_2indep(
        treatment_converted, treatment_n, control_converted, control_n,
        compare="diff", method="newcomb", alpha=alpha,
    )
    power_model = NormalIndPower()
    ratio = treatment_n / control_n
    baseline = min(max(p0, 1e-6), 1 - 1e-6)

    def power_at(delta: float) -> float:
        treatment_rate = min(baseline + delta, 1 - 1e-6)
        effect = proportion_effectsize(treatment_rate, baseline)
        return float(power_model.power(effect, control_n, alpha=alpha, ratio=ratio))

    max_delta = 1 - baseline - 1e-6
    mde = float(brentq(lambda d: power_at(d) - target_power, 1e-6, max_delta)) \
        if power_at(max_delta) >= target_power else max_delta
    design_power = power_at(min(practical_threshold, max_delta))
    cohen_h = float(proportion_effectsize(p1, p0))
    if ci_low > 0 and diff >= practical_threshold:
        recommendation = "Ship: statistically significant and practically meaningful"
    elif ci_high < 0:
        recommendation = "Do not ship: statistically significant negative effect"
    elif p_value < alpha:
        recommendation = "Investigate: significant effect below practical threshold"
    else:
        recommendation = "Continue testing: evidence is inconclusive"
    return ExperimentResult(
        name, control_n, treatment_n, control_converted, treatment_converted,
        p0, p1, diff, diff / p0 if p0 else None,
        float(ci_low), float(ci_high), float(p_value), mde,
        float(design_power), practical_threshold, cohen_h, recommendation,
    )


def analyze_warehouse(database_url: str) -> ExperimentResult:
    with psycopg.connect(database_url) as conn:
        rows = conn.execute("""
            with cutoff as (
              select (max(month_start) + interval '1 month' - interval '7 days') as mature_before
              from raw.marketing_spend
            )
            select experiment_variant, count(*) as n,
                   count(*) filter (where activated_within_7d) as converted
            from analytics.dim_customer, cutoff
            where trial_started_at is not null and trial_started_at < cutoff.mature_before
            group by 1
        """).fetchall()
        variants = {name: (n, converted) for name, n, converted in rows}
        if set(variants) != {"control", "treatment"}:
            raise ValueError("Both experiment variants must have eligible users")
        control_n, control_converted = variants["control"]
        treatment_n, treatment_converted = variants["treatment"]
        result = analyze(control_converted, control_n, treatment_converted, treatment_n)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analytics.experiment_results (
              experiment_name text PRIMARY KEY, computed_at timestamptz NOT NULL DEFAULT now(),
              result jsonb NOT NULL
            )
        """)
        conn.execute("""
            INSERT INTO analytics.experiment_results (experiment_name, result)
            VALUES (%s, %s::jsonb)
            ON CONFLICT (experiment_name) DO UPDATE SET
              computed_at = now(), result = EXCLUDED.result
        """, (result.experiment_name, json.dumps(asdict(result))))
        conn.commit()
    return result


def main() -> None:
    load_dotenv()
    result = analyze_warehouse(os.environ["DATABASE_URL"])
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
