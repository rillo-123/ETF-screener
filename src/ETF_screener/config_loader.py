
import json
from pathlib import Path
from typing import Any, Dict

_paths_cache = None

def get_paths() -> Dict[str, Any]:
    """
    Load and cache paths from config/paths.json.
    """
    global _paths_cache
    if _paths_cache is not None:
        return _paths_cache
    config_dir = Path(__file__).parent.parent.parent / "config"
    path_file = config_dir / "paths.json"
    with open(path_file, "r", encoding="utf-8") as f:
        _paths_cache = json.load(f)
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
            return json.load(f)  # type: ignore[no-any-return]
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
