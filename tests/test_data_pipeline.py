import pandas as pd
import pytest
from src.data_pipeline import normalize_district_name, match_district

def test_normalize_district_name():
    assert normalize_district_name("LA VICTORIA") == "LA VICTORIA"
    assert normalize_district_name("BREÑA") == "BRENA"
    assert normalize_district_name("BRE\ufffdA") == "BREA"

def test_match_district():
    valid = ["LA VICTORIA", "BRENA", "RIMAC"]
    assert match_district("LA VICTORIA", valid) == "LA VICTORIA"
    assert match_district("BREA", valid) == "BRENA"
    assert match_district("RIMAC", valid) == "RIMAC"
    assert match_district("COMAS", valid) is None
