"""HTML dashboard, loader output, edge cases of the text report and sample-data generator."""
import json

import numpy as np
import pandas as pd
import pytest

from toll_plaza_dashboard import TollPlazaDashboard, create_sample_payment_data


def make(tmp_path, plazas, pay):
    pp, payp = tmp_path / "plazas.csv", tmp_path / "pay.csv"
    pd.DataFrame(plazas).to_csv(pp, index=False)
    pd.DataFrame(pay).to_csv(payp, index=False)
    return TollPlazaDashboard(str(pp), str(payp))


PLAZAS = {"plaza_name": ["A", "B"], "state": ["Goa", "Goa"]}
PAY = {"plaza_name": ["A", "B", "A"], "date": ["2024-01-01", "2024-01-01", "2024-02-01"],
       "amount": [1_000_000.0, 3_000_000.0, 2_000_000.0]}


def test_no_payment_path_leaves_payments_and_metrics_unset(tmp_path):
    pp = tmp_path / "p.csv"
    pd.DataFrame(PLAZAS).to_csv(pp, index=False)
    d = TollPlazaDashboard(str(pp))
    assert d.payments is None and d.metrics is None
    assert len(d.plazas) == 2


def test_calculate_metrics_without_payments_is_noop(tmp_path):
    pp = tmp_path / "p.csv"
    pd.DataFrame(PLAZAS).to_csv(pp, index=False)
    d = TollPlazaDashboard(str(pp))
    d._calculate_metrics()
    assert d.metrics is None


def test_loader_adds_month_and_day_and_prints_summary(tmp_path, capsys):
    d = make(tmp_path, PLAZAS, PAY)
    assert list(d.payments["month"]) == ["2024-01", "2024-01", "2024-02"]
    out = capsys.readouterr().out
    assert "Loaded 3 payment records" in out
    assert "Unique plazas: 2" in out


def test_top_plazas_limit_and_order(tmp_path):
    d = make(tmp_path, PLAZAS, PAY)
    assert d._get_top_plazas(1) == {"A": 3_000_000.0}
    assert d._get_top_plazas(10) == {"A": 3_000_000.0, "B": 3_000_000.0}


def test_top_plazas_capped_at_ten(tmp_path):
    n = 12
    plazas = {"plaza_name": [f"P{i}" for i in range(n)], "state": ["Goa"] * n}
    pay = {"plaza_name": [f"P{i}" for i in range(n)], "date": ["2024-01-01"] * n,
           "amount": [float(i + 1) for i in range(n)]}
    d = make(tmp_path, plazas, pay)
    top = d.metrics["top_plazas"]
    assert len(top) == 10
    assert list(top)[0] == "P11" and list(top)[-1] == "P2"


def test_volatility_is_per_plaza_std(tmp_path):
    d = make(tmp_path, PLAZAS, PAY)
    vol = d.metrics["collection_volatility"]
    assert vol["A"] == pytest.approx(np.std([1_000_000.0, 2_000_000.0], ddof=1))
    assert np.isnan(vol["B"])


def test_dashboard_without_payments_prints_error_and_returns_none(tmp_path, capsys):
    pp = tmp_path / "p.csv"
    pd.DataFrame(PLAZAS).to_csv(pp, index=False)
    d = TollPlazaDashboard(str(pp))
    out = tmp_path / "dash.html"
    assert d.create_interactive_dashboard(str(out)) is None
    assert not out.exists()
    assert "No payment data loaded" in capsys.readouterr().out


def test_dashboard_html_embeds_kpis_and_data(tmp_path):
    d = make(tmp_path, PLAZAS, PAY)
    out = tmp_path / "dash.html"
    assert d.create_interactive_dashboard(str(out)) == str(out)
    html = out.read_text()
    assert "₹0.60 Cr" in html  # 6.0M rupees
    assert "₹30.00 L" in html  # avg daily: (4M + 2M)/2 = 3M
    assert "Active Plazas" in html
    assert '"2024-01": 4000000.0' in html and '"2024-02": 2000000.0' in html
    assert json.dumps({"A": 3000000.0, "B": 3000000.0}) in html
    assert "const totalCollections = 6000000.0;" in html
    assert html.count("<canvas") == 3


def test_active_plazas_kpi_counts_unique(tmp_path):
    d = make(tmp_path, PLAZAS, PAY)
    out = tmp_path / "d.html"
    d.create_interactive_dashboard(str(out))
    assert '<div class="kpi-value">2</div>' in out.read_text()


def test_export_json_roundtrip_types(tmp_path):
    d = make(tmp_path, PLAZAS, PAY)
    p = d.export_metrics_json(str(tmp_path / "m.json"))
    data = json.loads(open(p).read())
    assert data["total_collections"] == 6_000_000.0
    assert data["avg_daily_collection"] == pytest.approx(3_000_000.0)
    assert data["avg_plaza_revenue"] == pytest.approx(3_000_000.0)
    assert data["monthly_breakdown"] == {"2024-01": 4_000_000.0, "2024-02": 2_000_000.0}
    assert data["state_breakdown"] == {"Goa": 6_000_000.0}
    assert data["top_plazas"] == {"A": 3_000_000.0, "B": 3_000_000.0}
    assert "generated_at" in data


def test_text_report_sections_and_unknown_state(tmp_path):
    plazas = {"plaza_name": ["A"], "state": ["Goa"]}
    pay = {"plaza_name": ["A", "Z"], "date": ["2024-01-01", "2024-01-02"], "amount": [4_000_000.0, 1_000_000.0]}
    d = make(tmp_path, plazas, pay)
    rep = open(d.generate_text_report(str(tmp_path / "r.txt"))).read()
    assert "Total Collections: ₹0.50 Crore" in rep
    assert "Average Daily Collection: ₹25.00 Lakhs" in rep
    assert "Average Plaza Revenue: ₹25.00 Lakhs" in rep
    assert "Active Toll Plazas: 2" in rep
    assert "Date Range: 2024-01-01 to 2024-01-02" in rep
    assert "Total Toll Plazas in Network: 1" in rep
    assert "States with Toll Infrastructure: 1" in rep
    assert "Data Points Analyzed: 2" in rep
    lines = [l for l in rep.splitlines() if l.startswith((" 1.", " 2."))]
    assert lines[0].startswith(" 1. A") and "Goa" in lines[0] and "80.00%" in lines[0]
    assert lines[1].startswith(" 2. Z") and "Unknown" in lines[1] and "20.00%" in lines[1]
    assert "COLLECTIONS BY STATE" in rep and "MONTHLY TRENDS" in rep


def test_text_report_first_month_zero_change_and_only_top_15(tmp_path):
    n = 17
    plazas = {"plaza_name": [f"P{i:02d}" for i in range(n)], "state": ["Goa"] * n}
    pay = {"plaza_name": [f"P{i:02d}" for i in range(n)], "date": ["2024-01-01"] * n,
           "amount": [float(100_000 * (i + 1)) for i in range(n)]}
    d = make(tmp_path, plazas, pay)
    rep = open(d.generate_text_report(str(tmp_path / "r.txt"))).read()
    assert "2024-01  | ₹" in rep and "+0.00%" in rep
    ranked = [l for l in rep.splitlines() if l[:3].strip().rstrip(".").isdigit() and "|" in l and "L (" in l]
    assert len(ranked) == 15
    assert ranked[0].startswith(" 1. P16")
    assert not any("P00" in l or "P01" in l for l in ranked)


def test_text_report_states_sorted_desc(tmp_path):
    plazas = {"plaza_name": ["A", "B"], "state": ["Goa", "Assam"]}
    pay = {"plaza_name": ["A", "B"], "date": ["2024-01-01"] * 2, "amount": [1e6, 3e6]}
    d = make(tmp_path, plazas, pay)
    rep = open(d.generate_text_report(str(tmp_path / "r.txt"))).read()
    sect = rep.split("COLLECTIONS BY STATE")[1].split("MONTHLY")[0]
    assert sect.index("Assam") < sect.index("Goa")


def test_sample_data_defaults_and_columns(tmp_path, monkeypatch):
    np.random.seed(1)
    plazas = pd.DataFrame({"plaza_name": ["A", None, "B"]})
    out = tmp_path / "s.csv"
    df = create_sample_payment_data(plazas, str(out))
    assert out.exists()
    assert list(df.columns) == ["plaza_name", "date", "amount", "vehicle_count"]
    assert set(df["plaza_name"]) == {"A", "B"}  # None dropped
    assert len(df) == 12 * 28 * 2
    assert df["vehicle_count"].between(500, 2000).all()
    assert df["date"].iloc[0] == "2024-01-01"
    assert df["date"].iloc[-1] == "2024-12-23"
    assert pd.read_csv(out).shape == df.shape


def test_sample_data_samples_at_most_100_plazas_per_day(tmp_path):
    np.random.seed(2)
    plazas = pd.DataFrame({"plaza_name": [f"P{i}" for i in range(150)]})
    df = create_sample_payment_data(plazas, str(tmp_path / "s.csv"))
    assert len(df) == 12 * 28 * 100
