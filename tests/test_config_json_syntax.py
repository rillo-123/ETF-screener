import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config"


def _config_json_files() -> list[Path]:
    return sorted(CONFIG_DIR.glob("*.json"))


def test_all_config_json_files_parse() -> None:
    """Ensure every JSON file in config/ is syntactically valid."""
    json_files = _config_json_files()
    assert json_files, f"No JSON files found in {CONFIG_DIR}"

    for file_path in json_files:
        raw = file_path.read_text(encoding="utf-8")
        try:
            json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AssertionError(
                f"Invalid JSON in {file_path}: {exc.msg} at line {exc.lineno}, col {exc.colno}"
            ) from exc


def test_ribbon_settings_has_required_sections() -> None:
    """Guard against accidentally deleting top-level ribbon config sections."""
    ribbon_path = CONFIG_DIR / "ribbon_settings.json"
    ribbon = json.loads(ribbon_path.read_text(encoding="utf-8"))

    required_keys = {"aggregate", "dsl_layer_styles", "ribbons"}
    missing = required_keys.difference(ribbon.keys())
    assert not missing, f"Missing required keys in {ribbon_path}: {sorted(missing)}"
