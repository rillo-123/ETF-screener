import json

import pytest

from ETF_screener.ucits_catalogue import (
    CatalogueError,
    compare_catalogue,
    filter_catalogue,
    load_catalogue,
)


def test_catalogue_loads_a_unique_ucits_starter_universe():
    funds = load_catalogue()

    assert len(funds) >= 8
    assert len({fund["ticker"] for fund in funds}) == len(funds)
    assert all(len(fund["isin"]) == 12 for fund in funds)


def test_catalogue_filters_are_case_insensitive_and_ter_is_inclusive():
    funds = load_catalogue()

    result = filter_catalogue(
        funds,
        asset_class="equity",
        distribution_policy="accumulating",
        max_ter_pct=0.22,
    )

    assert [fund["ticker"] for fund in result] == ["SXR8.DE", "EUNL.DE", "VWCE.DE"]


def test_catalogue_comparison_preserves_requested_order():
    funds = load_catalogue()

    result = compare_catalogue(funds, ["VWCE.DE", "SXR8.DE"])

    assert [fund["ticker"] for fund in result] == ["VWCE.DE", "SXR8.DE"]


def test_catalogue_rejects_bad_data(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"funds": [{"ticker": "BAD"}]}), encoding="utf-8")

    with pytest.raises(CatalogueError):
        load_catalogue(str(path))
