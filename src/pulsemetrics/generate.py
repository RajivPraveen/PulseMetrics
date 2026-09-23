"""Deterministic synthetic exports for a fictional SaaS company."""
from __future__ import annotations

import argparse
import calendar
import csv
import random
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

CHANNELS = ["Organic", "Paid Search", "Paid Social", "Referral", "Partner"]
FEATURES = ["dashboard", "automation", "integration", "collaboration", "reporting"]
START = date(2025, 1, 1)


def add_months(day: date, count: int) -> date:
    total = day.year * 12 + day.month - 1 + count
    year, month = divmod(total, 12)
    return date(year, month + 1, min(day.day, calendar.monthrange(year, month + 1)[1]))


def stamp(day: date, hour: int = 12) -> str:
    return datetime(day.year, day.month, day.day, hour, tzinfo=UTC).isoformat()


def month_start(day: date) -> date:
    return day.replace(day=1)


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def generate(out: Path, as_of: date | None = None, customers: int = 1400) -> dict[str, int]:
    as_of = as_of or datetime.now(UTC).date().replace(day=1)
    if as_of <= START:
        raise ValueError("as_of must be after 2025-01-01")
    out.mkdir(parents=True, exist_ok=True)
    tables: dict[str, list[dict]] = {name: [] for name in (
        "customers", "web_visits", "subscription_periods", "invoices",
        "product_events", "marketing_spend", "support_tickets",
    )}
    counters = defaultdict(int)

    def append(table: str, key: str, row: dict, updated: date) -> int:
        counters[table] += 1
        row[key] = counters[table]
        row["source_updated_at"] = stamp(updated)
        tables[table].append(row)
        return counters[table]

    span = (as_of - START).days
    for customer_id in range(1, customers + 1):
        rng = random.Random(271828 + customer_id)
        # A fixed, skewed signup distribution gives realistic growth and reproducible IDs.
        signup = START + timedelta(days=min(span - 1, int(span * rng.betavariate(1.7, 1.2))))
        channel = rng.choices(CHANNELS, [0.35, 0.25, 0.18, 0.15, 0.07])[0]
        variant = "treatment" if customer_id % 2 else "control"
        segment = rng.choices(["Self Serve", "SMB", "Mid Market"], [0.57, 0.33, 0.10])[0]
        trial = signup + timedelta(days=rng.randint(0, 2)) if rng.random() < 0.94 else None
        activated = trial is not None and rng.random() < (0.44 if variant == "treatment" else 0.35)
        activation_day = trial + timedelta(days=rng.randint(1, 6)) if activated else None
        paid = trial is not None and rng.random() < (0.67 if activated else 0.18)
        paid_day = trial + timedelta(days=rng.randint(8, 25)) if paid else None
        if paid_day and paid_day >= as_of:
            paid_day = None
        append("customers", "customer_id", {
            "signup_at": stamp(signup),
            "trial_started_at": stamp(trial) if trial else "",
            "account_name": f"Acme Account {customer_id:04d}",
            "segment": segment,
            "country": rng.choices(["US", "CA", "UK", "DE", "IN"], [0.55, 0.12, 0.12, 0.09, 0.12])[0],
            "channel": channel,
            "experiment_variant": variant,
        }, signup)

        visitor = f"visitor-{customer_id:06d}"
        for offset in (rng.randint(1, 12), 0):
            visit = max(START, signup - timedelta(days=offset))
            append("web_visits", "visit_id", {
                "visitor_id": visitor, "customer_id": customer_id,
                "visited_at": stamp(visit), "channel": channel,
            }, visit)

        def event(day: date, name: str, feature: str = "", cid: int = customer_id) -> None:
            if day < as_of:
                append("product_events", "event_id", {
                    "customer_id": cid, "occurred_at": stamp(day),
                    "event_name": name, "session_id": f"s-{cid}-{day.isoformat()}",
                    "feature": feature,
                }, day)

        event(signup, "signup")
        if trial:
            event(trial, "trial_started")
        if activation_day:
            event(activation_day, "activated")

        churn_day = None
        upgrade_day = None
        periods = []
        if paid_day:
            initial_mrr = {"Self Serve": 49, "SMB": 149, "Mid Market": 399}[segment]
            # Only mature subscriptions can upgrade or churn.
            if (as_of - paid_day).days > 120 and rng.random() < 0.24:
                upgrade_day = add_months(paid_day, rng.randint(3, 6))
                if upgrade_day >= as_of:
                    upgrade_day = None
            if (as_of - paid_day).days > 90 and rng.random() < 0.22:
                churn_day = add_months(paid_day, rng.randint(3, 11))
                if churn_day >= as_of:
                    churn_day = None
            if upgrade_day and churn_day and upgrade_day >= churn_day:
                upgrade_day = None
            first_end = upgrade_day or churn_day
            first_id = append("subscription_periods", "period_id", {
                "customer_id": customer_id, "started_at": stamp(paid_day),
                "ended_at": stamp(first_end) if first_end else "",
                "plan": "Starter" if segment == "Self Serve" else "Business",
                "mrr": initial_mrr,
            }, first_end or paid_day)
            periods.append((first_id, paid_day, first_end, initial_mrr))
            if upgrade_day:
                second_mrr = round(initial_mrr * 1.6, 2)
                second_id = append("subscription_periods", "period_id", {
                    "customer_id": customer_id, "started_at": stamp(upgrade_day),
                    "ended_at": stamp(churn_day) if churn_day else "",
                    "plan": "Growth", "mrr": second_mrr,
                }, churn_day or upgrade_day)
                periods.append((second_id, upgrade_day, churn_day, second_mrr))
            for period_id, start, end, mrr in periods:
                bill_day = start
                bill_index = 0
                while bill_day < (end or as_of) and bill_day < as_of:
                    append("invoices", "invoice_id", {
                        "customer_id": customer_id, "period_id": period_id,
                        "invoiced_at": stamp(bill_day), "amount": mrr,
                        "invoice_type": "new" if not bill_index and period_id == first_id else (
                            "expansion" if not bill_index else "recurring"),
                    }, bill_day)
                    bill_index += 1
                    bill_day = add_months(start, bill_index)

        # Sparse activity is enough for daily engagement and feature adoption trends.
        active_until = min(as_of, churn_day or as_of)
        current = signup
        while current < active_until:
            if rng.random() < (0.13 if paid_day and current >= paid_day else 0.045):
                event(current, "session_started")
                if rng.random() < 0.65:
                    feature = rng.choices(FEATURES, [0.38, 0.18, 0.14, 0.17, 0.13])[0]
                    event(current, "feature_used", feature)
            current += timedelta(days=1)
        if rng.random() < 0.18:
            ticket_day = signup + timedelta(days=rng.randint(2, max(3, min(180, (as_of - signup).days - 1))))
            if ticket_day < as_of:
                append("support_tickets", "ticket_id", {
                    "customer_id": customer_id, "opened_at": stamp(ticket_day),
                    "status": rng.choice(["resolved", "resolved", "open"]),
                    "priority": rng.choice(["low", "medium", "high"]),
                }, ticket_day)

    # Anonymous traffic makes the website-to-signup funnel meaningful.
    rng = random.Random(424242)
    for idx in range(customers * 2):
        visit = START + timedelta(days=rng.randrange(span))
        append("web_visits", "visit_id", {
            "visitor_id": f"anonymous-{idx:06d}", "customer_id": "",
            "visited_at": stamp(visit), "channel": rng.choice(CHANNELS),
        }, visit)
    month = START
    while month < as_of:
        for channel in CHANNELS:
            spend = {"Organic": 500, "Paid Search": 11000, "Paid Social": 8500,
                     "Referral": 2200, "Partner": 3500}[channel]
            spend = round(spend * (1 + (month.year - 2025) * 0.16) * rng.uniform(0.85, 1.15), 2)
            clicks = int(spend / rng.uniform(2.2, 4.2))
            append("marketing_spend", "spend_id", {
                "month_start": month.isoformat(), "channel": channel, "spend": spend,
                "impressions": clicks * rng.randint(17, 35), "clicks": clicks,
            }, add_months(month, 1) - timedelta(days=1))
        month = add_months(month, 1)

    for name, rows in tables.items():
        columns = list(rows[0]) if rows else []
        write_csv(out / f"{name}.csv", rows, columns)
    return {name: len(rows) for name, rows in tables.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("data/generated"))
    parser.add_argument("--as-of", type=date.fromisoformat,
                        default=datetime.now(UTC).date().replace(day=1))
    parser.add_argument("--customers", type=int, default=1400)
    args = parser.parse_args()
    print(generate(args.out, args.as_of, args.customers))


if __name__ == "__main__":
    main()
