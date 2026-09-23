"""Export README previews from the current PostgreSQL analytics marts."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import psycopg
from dotenv import load_dotenv
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
BG = "#091225"
PANEL = "#13223B"
TEXT = "#EFF6FF"
MUTED = "#9FB3CD"
CYAN = "#4DE1D2"
PURPLE = "#A58BFF"
CORAL = "#FF8D8D"


def canvas(title: str, subtitle: str):
    fig = plt.figure(figsize=(16, 9), facecolor=BG)
    fig.text(0.055, 0.945, "◉  PULSEMETRICS", color=CYAN, fontsize=13, weight="bold")
    fig.text(0.055, 0.885, title, color=TEXT, fontsize=30, weight="bold")
    fig.text(0.055, 0.843, subtitle, color=MUTED, fontsize=12)
    fig.text(0.945, 0.945, "DEMO DATA", color=MUTED, fontsize=10, ha="right")
    return fig


def panel(fig, box, radius=0.018):
    x, y, width, height = box
    fig.patches.append(FancyBboxPatch(
        (x, y), width, height,
        boxstyle=f"round,pad=0.006,rounding_size={radius}",
        transform=fig.transFigure, facecolor=PANEL, edgecolor="#1F3555",
        linewidth=1, zorder=-10,
    ))


def style_axis(ax):
    ax.set_facecolor(PANEL)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=10, length=0)
    ax.grid(axis="y", color="#334765", alpha=0.55)
    ax.set_axisbelow(True)


def save(fig, path: Path):
    fig.savefig(path, dpi=150, facecolor=BG, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print(path)


def overview(out: Path, rows: list[tuple]):
    months = [r[0].strftime("%b %Y") for r in rows]
    mrr = [float(r[1]) for r in rows]
    last = rows[-1]
    fig = canvas("Executive overview", f"Revenue and customer health · reporting through {months[-1]}")
    cards = [
        ("MONTHLY REVENUE", f"${mrr[-1] / 1000:,.1f}k"),
        ("ANNUAL RUN RATE", f"${float(last[2]) / 1000:,.1f}k"),
        ("PAID CUSTOMERS", f"{last[3]:,}"),
        ("LOGO CHURN", f"{float(last[4]) * 100:.1f}%"),
    ]
    for i, (label, value) in enumerate(cards):
        x = 0.055 + i * 0.237
        panel(fig, (x, 0.665, 0.218, 0.13))
        fig.text(x + 0.018, 0.755, label, color=MUTED, fontsize=10, weight="bold")
        fig.text(x + 0.018, 0.695, value, color=TEXT, fontsize=25, weight="bold")
    panel(fig, (0.055, 0.105, 0.61, 0.51))
    panel(fig, (0.687, 0.105, 0.258, 0.51))
    fig.text(0.076, 0.56, "Monthly recurring revenue", color=TEXT, fontsize=17, weight="bold")
    ax = fig.add_axes((0.085, 0.18, 0.55, 0.32))
    style_axis(ax)
    x = np.arange(len(mrr))
    ax.plot(x, mrr, color=CYAN, linewidth=3)
    ax.fill_between(x, mrr, color=CYAN, alpha=0.12)
    ax.set_xlim(0, len(mrr) - 1)
    ax.set_ylim(0, max(mrr) * 1.12)
    ax.set_xticks(x[::max(1, len(x) // 5)], months[::max(1, len(x) // 5)])
    ax.set_yticks([0, max(mrr) / 2, max(mrr)], ["$0", f"${max(mrr)/2000:.0f}k", f"${max(mrr)/1000:.0f}k"])
    fig.text(0.71, 0.56, "Revenue movement", color=TEXT, fontsize=17, weight="bold")
    movements = [("New", float(last[5]), CYAN), ("Expansion", float(last[6]), PURPLE),
                 ("Churn", -float(last[7]), CORAL)]
    for i, (label, value, color) in enumerate(movements):
        y = 0.455 - i * 0.105
        fig.text(0.71, y, label, color=MUTED, fontsize=12)
        fig.text(0.92, y, f"{'+' if value > 0 else '−'}${abs(value):,.0f}",
                 color=color, fontsize=15, weight="bold", ha="right")
    save(fig, out / "executive.png")


def acquisition(out: Path, row: tuple):
    month, visitors, signups, trials, activated, paid, visit_to_signup, trial_to_paid = row
    fig = canvas("Acquisition funnel", f"Signup cohort · {month:%B %Y}")
    panel(fig, (0.055, 0.11, 0.89, 0.67))
    stages = ["Website visitors", "Signups", "Trials", "Activated in 7 days", "Paid in 30 days"]
    values = [visitors, signups, trials, activated, paid]
    colors = ["#365A86", "#4779A3", "#559AB4", "#4BC4C1", CYAN]
    ax = fig.add_axes((0.25, 0.2, 0.63, 0.47))
    style_axis(ax)
    ax.grid(False)
    bars = ax.barh(np.arange(5), values, color=colors, height=0.62)
    ax.set_yticks(np.arange(5), stages)
    ax.tick_params(axis="y", colors=TEXT, labelsize=13, pad=15)
    ax.invert_yaxis()
    ax.set_xlim(0, max(values) * 1.13)
    ax.set_xticks([])
    for bar, value in zip(bars, values):
        ax.text(bar.get_width() + max(values) * 0.015, bar.get_y() + bar.get_height() / 2,
                f"{value:,}", color=TEXT, va="center", fontsize=13, weight="bold")
    fig.text(0.075, 0.71, "VISIT → SIGNUP", color=MUTED, fontsize=10, weight="bold")
    fig.text(0.075, 0.66, f"{float(visit_to_signup) * 100:.1f}%", color=CYAN, fontsize=24, weight="bold")
    fig.text(0.075, 0.56, "TRIAL → PAID", color=MUTED, fontsize=10, weight="bold")
    fig.text(0.075, 0.51, f"{float(trial_to_paid) * 100:.1f}%", color=PURPLE, fontsize=24, weight="bold")
    save(fig, out / "acquisition.png")


def retention(out: Path, rows: list[tuple]):
    cohorts = sorted({r[0] for r in rows})[-12:]
    values = np.full((len(cohorts), 7), np.nan)
    lookup = {(c, n): float(rate) for c, n, rate in rows}
    for i, cohort in enumerate(cohorts):
        for n in range(7):
            values[i, n] = lookup.get((cohort, n), np.nan)
    fig = canvas("Paid customer retention", "Share of each first-payment cohort still subscribed at month end")
    panel(fig, (0.055, 0.105, 0.89, 0.68))
    ax = fig.add_axes((0.18, 0.17, 0.7, 0.53))
    ax.set_facecolor(PANEL)
    cmap = LinearSegmentedColormap.from_list("pulse", ["#274161", "#317C95", CYAN])
    cmap.set_bad(PANEL)
    ax.imshow(np.ma.masked_invalid(values), cmap=cmap, vmin=0.55, vmax=1, aspect="auto")
    ax.set_xticks(range(7), [f"M{n}" for n in range(7)], color=TEXT, fontsize=11)
    ax.set_yticks(range(len(cohorts)), [c.strftime("%b %Y") for c in cohorts], color=TEXT, fontsize=10)
    ax.tick_params(length=0, pad=10)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for i in range(len(cohorts)):
        for j in range(7):
            if not np.isnan(values[i, j]):
                ax.text(j, i, f"{values[i,j]*100:.0f}%", ha="center", va="center",
                        color=BG if values[i, j] > 0.82 else TEXT, fontsize=10, weight="bold")
    save(fig, out / "retention.png")


def experimentation(out: Path, result: dict):
    fig = canvas("Onboarding experiment", "Primary outcome · activation within seven days of trial start")
    panel(fig, (0.055, 0.11, 0.52, 0.67))
    panel(fig, (0.596, 0.11, 0.349, 0.67))
    ax = fig.add_axes((0.13, 0.22, 0.37, 0.42))
    style_axis(ax)
    rates = [result["control_rate"], result["treatment_rate"]]
    bars = ax.bar([0, 1], rates, color=["#4E6789", CYAN], width=0.55)
    ax.set_xticks([0, 1], ["Control", "Treatment"], color=TEXT, fontsize=12)
    ax.set_ylim(0, max(rates) * 1.35)
    ax.set_yticks([0, 0.2, 0.4, 0.6], ["0%", "20%", "40%", "60%"])
    for bar, rate in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width() / 2, rate + 0.02, f"{rate * 100:.1f}%",
                ha="center", color=TEXT, fontsize=19, weight="bold")
    fig.text(0.625, 0.70, "RELATIVE LIFT", color=MUTED, fontsize=10, weight="bold")
    fig.text(0.625, 0.645, f"+{result['relative_lift'] * 100:.1f}%", color=CYAN,
             fontsize=30, weight="bold")
    details = [
        ("95% CI · absolute lift", f"{result['ci_low']*100:.1f} to {result['ci_high']*100:.1f} pp"),
        ("p-value", "<0.00001" if result["p_value"] < 0.00001 else f"{result['p_value']:.5f}"),
        ("Sample size", f"{result['control_n']:,} / {result['treatment_n']:,}"),
        ("80% power MDE", f"{result['mde_absolute']*100:.1f} pp"),
    ]
    for i, (label, value) in enumerate(details):
        y = 0.545 - i * 0.092
        fig.text(0.625, y, label, color=MUTED, fontsize=11)
        fig.text(0.918, y, value, color=TEXT, fontsize=12, ha="right", weight="bold")
    save(fig, out / "experimentation.png")


def main():
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "assets/previews")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        overview_rows = conn.execute("""
            select month_start, mrr, arr, paid_customers, logo_churn_rate,
                   new_mrr, expansion_mrr, churned_mrr
            from analytics.mart_monthly_kpis order by month_start
        """).fetchall()
        funnel = conn.execute("""
            select month_start, website_visitors, signups, trials, activated, paid_30d,
                   visit_to_signup, trial_to_paid
            from analytics.mart_funnel_monthly order by month_start desc limit 1
        """).fetchone()
        cohort_rows = conn.execute("""
            select cohort_month, month_number, retention_rate
            from analytics.mart_cohort_retention where month_number <= 6
        """).fetchall()
        experiment = conn.execute("""
            select result from analytics.experiment_results
            where experiment_name = 'onboarding_redesign_v1'
        """).fetchone()
    if not overview_rows or not funnel or not cohort_rows or not experiment:
        raise RuntimeError("Run the warehouse refresh before generating previews")
    overview(args.out, overview_rows)
    acquisition(args.out, funnel)
    retention(args.out, cohort_rows)
    experimentation(args.out, experiment[0])
    (args.out / "snapshot.json").write_text(json.dumps({
        "generated_from": "PostgreSQL analytics marts",
        "reporting_month": overview_rows[-1][0].isoformat(),
        "experiment": "onboarding_redesign_v1",
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
