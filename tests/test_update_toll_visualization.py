"""update_toll_visualization.py: validation, orchestration, archiving, CLI. Paths under /Users/... are redirected."""
import sys
from pathlib import Path as RealPath

import pandas as pd
import pytest

import update_toll_visualization as u


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Redirect the hard-coded /Users/umashankar prefix into tmp_path."""
    def P(s):
        return RealPath(str(s).replace("/Users/umashankar", str(tmp_path / "home")))
    monkeypatch.setattr(u, "Path", P)
    (tmp_path / "home" / "Out").mkdir(parents=True)
    return tmp_path / "home"


def csv(tmp_path, data, name="p.csv"):
    p = tmp_path / name
    pd.DataFrame(data).to_csv(p, index=False)
    return str(p)


GOOD = {"plaza_name": ["A", "B"], "date": ["2024-01-01", "2024-02-01"], "amount": [1, 2]}


def test_validate_ok_prints_summary(tmp_path, capsys):
    assert u.validate_payment_data(csv(tmp_path, GOOD)) is True
    out = capsys.readouterr().out
    assert "Records: 2" in out and "Unique plazas: 2" in out
    assert "2024-01-01 to 2024-02-01" in out


def test_validate_missing_columns(tmp_path, capsys):
    assert u.validate_payment_data(csv(tmp_path, {"plaza_name": ["A"], "date": ["2024-01-01"]})) is False
    out = capsys.readouterr().out
    assert "Missing required columns: amount" in out
    assert "Available columns: plaza_name, date" in out


def test_validate_bad_types(tmp_path, capsys):
    bad = {"plaza_name": ["A"], "date": ["not-a-date"], "amount": [1]}
    assert u.validate_payment_data(csv(tmp_path, bad)) is False
    assert "Error converting data types" in capsys.readouterr().out
    bad = {"plaza_name": ["A"], "date": ["2024-01-01"], "amount": ["abc"]}
    assert u.validate_payment_data(csv(tmp_path, bad)) is False


def test_validate_unreadable_file(tmp_path, capsys):
    assert u.validate_payment_data(str(tmp_path / "nope.csv")) is False
    assert "Error reading file" in capsys.readouterr().out


class FakeDash:
    inits = []
    fail_init = False
    fail_gen = False

    def __init__(self, plaza_path, pay_path):
        if FakeDash.fail_init:
            raise RuntimeError("boom-init")
        FakeDash.inits.append((plaza_path, pay_path))
        self.payments = pd.DataFrame({
            "plaza_name": ["A", "B", "A"],
            "date": pd.to_datetime(["2024-01-05", "2024-03-09", "2024-02-01"]),
            "amount": [1.0, 2.0, 3.0]})
        self.metrics = {"total_collections": 5e7, "top_plazas": {"A": 4e5, "B": 3e5, "C": 2e5, "D": 1e5}}

    def create_interactive_dashboard(self, p):
        if FakeDash.fail_gen:
            raise RuntimeError("boom-gen")
        u.Path(p).write_text("html")

    def export_metrics_json(self, p):
        u.Path(p).write_text("{}")

    def generate_text_report(self, p):
        u.Path(p).write_text("txt")


@pytest.fixture
def fake(monkeypatch):
    FakeDash.inits = []
    FakeDash.fail_init = FakeDash.fail_gen = False
    monkeypatch.setattr(u, "TollPlazaDashboard", FakeDash)
    return FakeDash


def test_update_stops_on_invalid_data(home, fake, tmp_path):
    assert u.update_visualizations(csv(tmp_path, {"x": [1]}), "Out") is False
    assert FakeDash.inits == []


def test_update_requires_plaza_file(home, fake, tmp_path, capsys):
    assert u.update_visualizations(csv(tmp_path, GOOD), "Out") is False
    assert "Plaza data not found" in capsys.readouterr().out


def test_update_happy_path(home, fake, tmp_path, capsys):
    (home / "Out" / "toll_plazas_cleaned.csv").write_text("plaza_name,state\n")
    pay = csv(tmp_path, GOOD)
    assert u.update_visualizations(pay, "Out") is True
    assert FakeDash.inits == [(f"/Users/umashankar/Out/toll_plazas_cleaned.csv", pay)]
    for f in ("toll_dashboard_updated.html", "toll_metrics_updated.json", "toll_analysis_report_updated.txt"):
        assert (home / "Out" / f).exists()
    out = capsys.readouterr().out
    assert "Total Collections: ₹5.00 Crore" in out
    assert "Data Records: 3" in out and "Active Plazas: 2" in out
    assert "Date Range: 2024-01-05 to 2024-03-09" in out
    assert "1. A: ₹4.00 Lakhs" in out and "3. C: ₹2.00 Lakhs" in out
    assert "4. D" not in out  # top three only


def test_update_init_failure(home, fake, tmp_path, capsys):
    (home / "Out" / "toll_plazas_cleaned.csv").write_text("x")
    FakeDash.fail_init = True
    assert u.update_visualizations(csv(tmp_path, GOOD), "Out") is False
    assert "Error initializing dashboard: boom-init" in capsys.readouterr().out


def test_update_generation_failure(home, fake, tmp_path, capsys):
    (home / "Out" / "toll_plazas_cleaned.csv").write_text("x")
    FakeDash.fail_gen = True
    assert u.update_visualizations(csv(tmp_path, GOOD), "Out") is False
    assert "Error generating visualizations: boom-gen" in capsys.readouterr().out


def test_archive_renames_existing_only(home, capsys):
    out = home / "Out"
    (out / "toll_dashboard.html").write_text("a")
    (out / "toll_metrics.json").write_text("b")
    u.archive_previous_versions("Out")
    names = sorted(p.name for p in out.iterdir())
    assert len(names) == 2
    assert all("_backup_" in n for n in names)
    assert any(n.startswith("toll_dashboard_backup_") and n.endswith(".html") for n in names)
    assert any(n.startswith("toll_metrics_backup_") and n.endswith(".json") for n in names)
    assert not (out / "toll_dashboard.html").exists()
    assert "Archived: toll_dashboard_backup_" in capsys.readouterr().out


def run_main(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["prog"] + argv)
    return u.main()


def test_main_missing_file(home, fake, monkeypatch, tmp_path, capsys):
    assert run_main(monkeypatch, ["--data", str(tmp_path / "none.csv")]) is False
    assert "File not found" in capsys.readouterr().out


@pytest.mark.parametrize("answer,expected", [("no", False), ("", False), ("y", True), ("YES", True)])
def test_main_confirmation(home, fake, monkeypatch, tmp_path, answer, expected):
    (home / "Downloads").mkdir()
    (home / "Downloads" / "toll_plazas_cleaned.csv").write_text("x")
    monkeypatch.setattr("builtins.input", lambda prompt="": answer)
    assert run_main(monkeypatch, ["--data", csv(tmp_path, GOOD)]) is expected


def test_main_force_skips_prompt_and_archive_runs(home, fake, monkeypatch, tmp_path):
    out = home / "Out"
    (out / "toll_plazas_cleaned.csv").write_text("x")
    (out / "toll_metrics.json").write_text("old")
    def no_input(prompt=""):
        raise AssertionError("prompt shown")
    monkeypatch.setattr("builtins.input", no_input)
    assert run_main(monkeypatch, ["--data", csv(tmp_path, GOOD), "--output", "Out", "--force", "--archive"]) is True
    assert any(p.name.startswith("toll_metrics_backup_") for p in out.iterdir())
    assert (out / "toll_metrics_updated.json").exists()


def test_main_without_archive_leaves_old_files(home, fake, monkeypatch, tmp_path):
    out = home / "Out"
    (out / "toll_plazas_cleaned.csv").write_text("x")
    (out / "toll_metrics.json").write_text("old")
    assert run_main(monkeypatch, ["--data", csv(tmp_path, GOOD), "--output", "Out", "--force"]) is True
    assert (out / "toll_metrics.json").read_text() == "old"
