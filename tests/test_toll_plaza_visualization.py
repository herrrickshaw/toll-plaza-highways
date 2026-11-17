"""Row parsing in TollPlazaVisualization._clean_plaza_data on hand-made PDF-table rows."""
import pandas as pd

from toll_plaza_visualization import TollPlazaVisualization


def clean(rows):
    v = TollPlazaVisualization()
    v.plazas_df = pd.DataFrame(rows)
    return v._clean_plaza_data().reset_index(drop=True)


def test_basic_row():
    df = clean([["1", "Kherki Daula Toll Plaza", "NH-48", "Haryana"]])
    r = df.iloc[0]
    assert (r["plaza_name"], r["state"], r["highway"]) == ("Kherki Daula Toll Plaza", "Haryana", "NH-48")


def test_states_outside_the_short_list_are_recognised():
    df = clean([["1", "Balasore Toll Plaza", "NH-16", "Odisha"],
                ["2", "Bakhtiyarpur Toll Plaza", "NH-31", "Bihar"],
                ["3", "Kumbalam Toll Plaza", "NH-66", "Kerala"]])
    assert list(df["state"]) == ["Odisha", "Bihar", "Kerala"]


def test_state_cell_preferred_over_plaza_name_containing_a_state():
    df = clean([["2", "Haryana", "Delhi Gurgaon Toll Plaza", "NH-48"]])
    assert df.iloc[0]["state"] == "Haryana"
    assert df.iloc[0]["plaza_name"] == "Delhi Gurgaon Toll Plaza"


def test_serial_number_is_not_used_as_plaza_name():
    df = clean([["514", "Manoharpur", "NH-48", "Rajasthan"]])
    assert df.iloc[0]["plaza_name"] == "Manoharpur"


def test_highway_requires_nh_number_not_any_nh_substring():
    df = clean([["7", "NH-44", "KANHAN TOLL PLAZA", "Maharashtra"]])
    assert df.iloc[0]["highway"] == "NH-44"
    assert df.iloc[0]["plaza_name"] == "KANHAN TOLL PLAZA"


def test_duplicate_plaza_names_collapse_and_empty_rows_dropped():
    df = clean([["1", "X Toll Plaza", "NH-1", "Punjab"], ["2", "X Toll Plaza", "NH-1", "Punjab"],
                [None, None, None, None]])
    assert len(df) == 1
