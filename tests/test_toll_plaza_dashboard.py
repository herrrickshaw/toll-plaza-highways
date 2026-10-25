"""Metrics and report maths in toll_plaza_dashboard.py, on small fixed fixtures (no random data)."""
import json

import numpy as np
import pandas as pd
import pytest

from toll_plaza_dashboard import TollPlazaDashboard, create_sample_payment_data


@pytest.fixture
def files(tmp_path):
    plazas = pd.DataFrame({"plaza_name": ["A", "B", "C"], "state": ["Haryana", "Haryana", "Gujarat"]})
    # amounts in rupees
    pay = pd.DataFrame({
        "plaza_name": ["A", "B", "A", "C", "Z"],
        "date": ["2024-01-01", "2024-01-01", "2024-01-02", "2024-02-01", "2024-02-01"],
        "amount": [1_000_000.0, 3_000_000.0, 2_000_000.0, 4_000_000.0, 500_000.0],
    })
    pp, payp = tmp_path / "plazas.csv", tmp_path / "pay.csv"
    plazas.to_csv(pp, index=False)
    pay.to_csv(payp, index=False)
    return pp, payp


def test_metrics_hand_computed(files):
    d = TollPlazaDashboard(*files)
    m = d.metrics
    assert m["total_collections"] == 10_500_000
    # days: Jan1 = 4.0M, Jan2 = 2.0M, Feb1 = 4.5M -> mean 3.5M
    assert m["avg_daily_collection"] == pytest.approx(3_500_000)
    # per plaza: A 3.0M, B 3.0M, C 4.0M, Z 0.5M -> mean 2.625M
    assert m["avg_plaza_revenue"] == pytest.approx(2_625_000)
    assert m["monthly_breakdown"] == {"2024-01": 6_000_000, "2024-02": 4_500_000}
    assert m["state_breakdown"] == {"Haryana": 6_000_000, "Gujarat": 4_000_000}  # unknown plaza Z dropped
    assert list(m["top_plazas"])[0] == "C"


def test_json_and_text_report(files, tmp_path):
    d = TollPlazaDashboard(*files)
    out = json.loads(open(d.export_metrics_json(str(tmp_path / "m.json"))).read())
    assert out["total_collections"] == 10_500_000
    rep = open(d.generate_text_report(str(tmp_path / "r.txt"))).read()
    assert "Total Collections: ₹1.05 Crore" in rep
    assert "2024-02  | ₹        45.00 |    -25.00%" in rep  # 60 L -> 45 L month on month


def test_loader_prints_total_in_crore(files, capsys):
    TollPlazaDashboard(*files)
    assert "Total collections: ₹1.05 Cr" in capsys.readouterr().out


def test_sample_payment_data_is_in_rupees_like_the_report(tmp_path):
    """The report divides by 1e7 for crore and 1e5 for lakh, so amounts must be rupees.

    The generator draws 20-100 lakh x 0.7-1.3 per plaza-day, i.e. Rs 14 lakh - 1.3 crore.
    """
    np.random.seed(0)
    plazas = pd.DataFrame({"plaza_name": [f"P{i}" for i in range(5)], "state": ["Goa"] * 5})
    df = create_sample_payment_data(plazas, str(tmp_path / "s.csv"))
    assert len(df) == 12 * 28 * 5
    assert df["amount"].min() >= 14e5 and df["amount"].max() <= 1.3e7
