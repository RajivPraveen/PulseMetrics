import csv
from datetime import date

from pulsemetrics.generate import generate


def test_generator_is_repeatable_and_links_sources(tmp_path):
    first = generate(tmp_path / "first", date(2025, 7, 1), 40)
    second = generate(tmp_path / "second", date(2025, 7, 1), 40)
    assert first == second
    assert first["customers"] == 40
    assert (tmp_path / "first/customers.csv").read_bytes() == (tmp_path / "second/customers.csv").read_bytes()
    with (tmp_path / "first/subscription_periods.csv").open() as handle:
        periods = list(csv.DictReader(handle))
    assert all(1 <= int(row["customer_id"]) <= 40 for row in periods)
