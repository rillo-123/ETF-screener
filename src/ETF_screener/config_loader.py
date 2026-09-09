import json
import os
from pathlib import Path
from typing import Any, Dict, cast

_paths_cache: Dict[str, Any] | None = None
CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def _check_external_storage(paths: Dict[str, Any]) -> None:
    root = paths.get("external_storage_root")
    if root and not (Path(root) / ".etf-screener-storage").is_file():
        raise RuntimeError(
            f"ETF Screener storage is unavailable at {root}. Connect the Kingston "
            "SSD or update config/paths.local.json. No replacement store was created."
        )


def get_paths() -> Dict[str, Any]:
    """
    Load and cache paths from config/paths.json.
    """
    global _paths_cache
    if _paths_cache is not None:
        _check_external_storage(_paths_cache)
        return _paths_cache
    config_dir = CONFIG_DIR
    path_file = config_dir / "paths.json"
    with open(path_file, "r", encoding="utf-8") as f:
        _paths_cache = cast(Dict[str, Any], json.load(f))
    local_file = config_dir / "paths.local.json"
    if local_file.exists() and os.getenv("ETF_SCREENER_IGNORE_LOCAL_PATHS") != "1":
        with local_file.open(encoding="utf-8") as handle:
            overrides = json.load(handle)
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(_paths_cache.get(key), dict):
                _paths_cache[key].update(value)
            else:
                _paths_cache[key] = value
    _check_external_storage(_paths_cache)
    return _paths_cache


def load_command_config(config_file: str = "config/commands.json") -> Dict[str, Any]:
    """
    Load command configuration from JSON file.

    Args:
        config_file: Path to commands.json configuration file
    """
    config_path = Path(config_file)
    if not config_path.exists():
        # Try relative to package root
        config_path = Path(__file__).parent.parent.parent / config_file

    if config_path.exists():
        with open(config_path) as f:
            return cast(Dict[str, Any], json.load(f))
    return {}


def apply_flag_config(
    parser: Any, flags_config: Dict[str, Any], parse_volume: Any
) -> None:
    """
    Apply flag configuration to an argparse parser.

    Args:
        parser: argparse parser/subparser
        flags_config: Dictionary of flag configurations
        parse_volume: Function to parse volume strings (for volume type)
    """
    for flag_name, flag_config in flags_config.items():
        flag_type = flag_config.get("type", "str")

        # Handle positional arguments
        if flag_config.get("type") == "positional":
            parser.add_argument(
                flag_name,
                nargs=flag_config.get("nargs", "?"),
                help=flag_config.get("help", ""),
            )
            continue

        # Build argument kwargs
        kwargs = {"help": flag_config.get("help", "")}

        if flag_type == "volume":
            kwargs["type"] = parse_volume
            kwargs["default"] = parse_volume(flag_config.get("default", "10M"))
        elif flag_type == "int":
            kwargs["type"] = int
            kwargs["default"] = flag_config.get("default", 0)
        elif flag_type == "choice":
            kwargs["choices"] = flag_config.get("choices", [])
            kwargs["default"] = flag_config.get("default")
        else:  # str
            if "default" in flag_config:
                kwargs["default"] = flag_config["default"]

        parser.add_argument(flag_name, **kwargs)
