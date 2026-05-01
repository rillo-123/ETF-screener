import json

from ETF_screener.xetra_extractor import XETRETFExtractor


def test_extract_etf_tickers_falls_back_to_validated_config_when_csv_missing(tmp_path):
    etfs_file = tmp_path / "etfs.json"
    blacklist_file = tmp_path / "blacklist.json"
    etfs_file.write_text(
        json.dumps(
            {
                "AAA.DE": {"status": "active", "name": "Alpha ETF"},
                "BBB.DE": {"status": "active", "name": "Beta ETF"},
            }
        ),
        encoding="utf-8",
    )
    blacklist_file.write_text(json.dumps({}), encoding="utf-8")

    extractor = XETRETFExtractor(
        csv_file=str(tmp_path / "missing.csv"),
        etfs_file=str(etfs_file),
        blacklist_file=str(blacklist_file),
    )

    tickers = extractor.extract_etf_tickers()

    assert tickers == {
        "AAA.DE": "Alpha ETF",
        "BBB.DE": "Beta ETF",
    }
