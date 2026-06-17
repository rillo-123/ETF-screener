"""Shared helpers for parsing ETF strategy DSL files."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyBlock:
    """Structured representation of one logical DSL block."""

    name: str
    layer: int
    expressions: tuple[str, ...]


_DEFAULT_SECTION_LAYER = {"TRIGGER": 3, "ENTRY": 3, "FILTER": 2, "EXIT": 4}
_FALLBACK_BLOCK_NAMES = {1: "Context", 2: "Setup", 3: "Trigger", 4: "Exit"}
_CANONICAL_ALIAS = {
    "context": (1, "context"),
    "setup": (2, "setup"),
    "qualify": (2, "setup"),
    "trigger": (3, "trigger"),
    "risk": (4, "risk"),
    "entry": (3, "trigger"),
    "exit": (4, "risk"),
}
_CANONICAL_PREFIX_ORDER = [
    "context",
    "setup",
    "qualify",
    "trigger",
    "risk",
    "entry",
    "exit",
]
STRATEGY_STRUCTURE_AXIS_ORDER = (
    "trend_context",
    "confirmation_depth",
    "trigger_precision",
    "exit_discipline",
    "risk_control",
    "time_discipline",
)
STRATEGY_STRUCTURE_AXIS_CATALOG = (
    {"key": "trend_context", "label": "Trend Context", "max": 10},
    {"key": "confirmation_depth", "label": "Confirmation Depth", "max": 10},
    {"key": "trigger_precision", "label": "Trigger Precision", "max": 10},
    {"key": "exit_discipline", "label": "Exit Discipline", "max": 10},
    {"key": "risk_control", "label": "Risk Control", "max": 10},
    {"key": "time_discipline", "label": "Time Discipline", "max": 10},
)

_MAX_DAYS_PATTERN = re.compile(
    r"^(MAX_DAYS|MAX_SIGNAL_AGE_DAYS|SIGNAL_MAX_DAYS|SINCE_DAYS)\s*:\s*(\d+)\s*$",
    re.IGNORECASE,
)
_INDICATOR_FAMILY_PATTERNS = (
    ("ema", re.compile(r"\bema_\d+\b", re.IGNORECASE)),
    ("rsi", re.compile(r"\brsi(?:_ema)?_\d+(?:_\d+)?\b", re.IGNORECASE)),
    ("macd", re.compile(r"\bmacd(?:_signal)?\b", re.IGNORECASE)),
    ("supertrend", re.compile(r"\b(?:st|supertrend)_\d+_\d+\b", re.IGNORECASE)),
    (
        "avwap",
        re.compile(r"\b(?:avwap|anchored_vwap)_(?:low|high)_\d+\b", re.IGNORECASE),
    ),
    ("volume", re.compile(r"\b(?:volume|vol_ema_\d+)\b", re.IGNORECASE)),
    ("adx", re.compile(r"\badx\b", re.IGNORECASE)),
)


def iter_clean_lines(content: str | None) -> list[str]:
    """Return non-empty DSL lines with comments removed."""
    if not content:
        return []

    cleaned: list[str] = []
    for raw in content.splitlines():
        line = raw.strip()
        if not line:
            continue

        # Preserve legacy layer directives that intentionally start with '#'.
        if re.match(r"^#\s*layer\s*[1-4]\b", line, re.IGNORECASE):
            cleaned.append(line)
            continue

        # Drop inline comments but keep the actual DSL content.
        line = line.split("#", 1)[0].strip()
        if line:
            cleaned.append(line)
    return cleaned


def resolve_block(raw_name: str) -> tuple[int, str]:
    """Return (layer, style_key) for a DSL block name."""
    key = raw_name.strip().lower()
    match = re.match(r"^layer\s*([1-4])$", key) or re.match(r"^l([1-4])$", key)
    if match:
        layer = int(match.group(1))
        style_keys = ["context", "setup", "trigger", "risk"]
        return layer, style_keys[layer - 1]

    if key in _CANONICAL_ALIAS:
        return _CANONICAL_ALIAS[key]

    for prefix in _CANONICAL_PREFIX_ORDER:
        if key.startswith(prefix):
            return _CANONICAL_ALIAS[prefix]

    return 2, ""


def parse_strategy_blocks(content: str | None) -> list[StrategyBlock]:
    """Parse DSL blocks for visualization and structural analysis."""
    lines = iter_clean_lines(content)
    if not lines:
        return []

    block_order: list[tuple[str, int]] = []
    block_exprs: dict[str, list[str]] = {}
    current_block: str | None = None
    current_layer: int | None = None

    for line in lines:
        begin_prefix = re.match(r"^begin\s+(.+)$", line, re.IGNORECASE)
        begin_suffix = re.match(r"^(.+?)\s+begin\b", line, re.IGNORECASE)

        if begin_prefix:
            raw_name = begin_prefix.group(1).strip()
        elif begin_suffix:
            raw_name = begin_suffix.group(1).strip()
        else:
            raw_name = ""

        if raw_name:
            current_block = raw_name
            current_layer, _ = resolve_block(raw_name)
            if raw_name not in block_exprs:
                block_exprs[raw_name] = []
                block_order.append((raw_name, current_layer))
            continue

        if re.match(r"^end\b", line, re.IGNORECASE):
            current_block = None
            current_layer = None
            continue

        if re.match(r"^begin\b", line, re.IGNORECASE):
            continue

        layer_match = re.match(r"^#\s*layer\s*([1-4])\b", line, re.IGNORECASE)
        if layer_match:
            current_layer = int(layer_match.group(1))
            continue

        section = re.match(
            r"^(TRIGGER|FILTER|ENTRY|EXIT):\s*(.+)$", line, re.IGNORECASE
        )
        if not section:
            continue

        expr = section.group(2).strip()
        if not expr:
            continue

        if current_block:
            block_exprs[current_block].append(f"({expr})")
            continue

        slot = current_layer or _DEFAULT_SECTION_LAYER.get(section.group(1).upper(), 2)
        fallback_name = _FALLBACK_BLOCK_NAMES.get(slot, "Block")
        if fallback_name not in block_exprs:
            block_exprs[fallback_name] = []
            block_order.append((fallback_name, slot))
        block_exprs[fallback_name].append(f"({expr})")

    return [
        StrategyBlock(name=name, layer=layer, expressions=tuple(block_exprs[name]))
        for name, layer in block_order
        if block_exprs.get(name)
    ]


def parse_strategy_scripts(content: str | None) -> tuple[str, str]:
    """Compile a DSL file into entry and exit expressions."""
    lines = iter_clean_lines(content)
    if not lines:
        return "False", "False"

    entry_terms: list[str] = []
    exit_terms: list[str] = []
    has_sections = False

    for line in lines:
        section = re.match(
            r"^(TRIGGER|FILTER|ENTRY|EXIT):\s*(.*)$", line, re.IGNORECASE
        )
        if not section:
            continue

        has_sections = True
        keyword = section.group(1).upper()
        expr = section.group(2).strip()
        if not expr:
            continue

        if keyword in {"TRIGGER", "FILTER", "ENTRY"}:
            entry_terms.append(f"({expr})")
        elif keyword == "EXIT":
            exit_terms.append(f"({expr})")

    if has_sections:
        entry_script = " and ".join(entry_terms) if entry_terms else "False"
        exit_script = " or ".join(exit_terms) if exit_terms else "False"
        return entry_script, exit_script

    fallback_expr = " ".join(lines).strip()
    return fallback_expr or "False", "False"


def _empty_structure_profile() -> dict[str, object]:
    axes = {key: 0.0 for key in STRATEGY_STRUCTURE_AXIS_ORDER}
    return {
        "structure_score": 0.0,
        "structure_axes": axes,
        "structure_tags": ["profile_unavailable"],
        "axis_order": list(STRATEGY_STRUCTURE_AXIS_ORDER),
    }


def _clamp_score(value: float) -> float:
    bounded = max(0.0, min(10.0, float(value)))
    return round(bounded, 2)


def _count_distinct_matches(text: str, pattern: re.Pattern[str]) -> int:
    return len({match.group(0).lower() for match in pattern.finditer(text)})


def _indicator_families(text: str) -> set[str]:
    families: set[str] = set()
    for family, pattern in _INDICATOR_FAMILY_PATTERNS:
        if pattern.search(text):
            families.add(family)
    return families


def parse_strategy_structure_profile(content: str | None) -> dict[str, object]:
    """Build a normalized DSL-first strategy structure profile."""
    if not content or not str(content).strip():
        return _empty_structure_profile()

    try:
        lines = iter_clean_lines(content)
        blocks = parse_strategy_blocks(content)
    except Exception:
        return _empty_structure_profile()

    if not lines:
        return _empty_structure_profile()

    role_exprs: dict[str, list[str]] = {
        "context": [],
        "setup": [],
        "trigger": [],
        "risk": [],
    }
    raw_blocks_seen: set[str] = set()
    explicit_exit_count = 0
    max_days: int | None = None
    current_block_raw: str | None = None
    dedicated_trigger_block = False
    dedicated_exit_block = False
    dedicated_qualify_block = False

    for line in lines:
        directive = _MAX_DAYS_PATTERN.match(line)
        if directive:
            max_days = int(directive.group(2))
            continue

        begin_prefix = re.match(r"^begin\s+(.+)$", line, re.IGNORECASE)
        begin_suffix = re.match(r"^(.+?)\s+begin\b", line, re.IGNORECASE)
        if begin_prefix:
            current_block_raw = begin_prefix.group(1).strip()
            raw_blocks_seen.add(current_block_raw.lower())
            continue
        if begin_suffix:
            current_block_raw = begin_suffix.group(1).strip()
            raw_blocks_seen.add(current_block_raw.lower())
            continue
        if re.match(r"^end\b", line, re.IGNORECASE):
            current_block_raw = None
            continue
        if re.match(r"^#\s*layer\s*[1-4]\b", line, re.IGNORECASE):
            continue

        section = re.match(
            r"^(TRIGGER|FILTER|ENTRY|EXIT):\s*(.+)$", line, re.IGNORECASE
        )
        if not section:
            continue

        section_name = section.group(1).upper()
        expr = section.group(2).strip()
        if not expr:
            continue

        canonical_role = (
            resolve_block(current_block_raw)[1] if current_block_raw else ""
        ) or (
            "trigger"
            if section_name in {"TRIGGER", "ENTRY"}
            else "risk" if section_name == "EXIT" else "setup"
        )

        if canonical_role == "setup" and current_block_raw:
            if str(current_block_raw).strip().lower().startswith("qualify"):
                dedicated_qualify_block = True
        if canonical_role == "trigger" and current_block_raw:
            dedicated_trigger_block = True
        if canonical_role == "risk" and current_block_raw:
            dedicated_exit_block = True

        if section_name == "EXIT":
            explicit_exit_count += 1
            role_exprs["risk"].append(expr)
            continue
        if canonical_role == "risk":
            explicit_exit_count += 1
            role_exprs["risk"].append(expr)
            continue
        if canonical_role in role_exprs:
            role_exprs[canonical_role].append(expr)

    if not any(role_exprs.values()):
        return _empty_structure_profile()

    pretrigger_exprs = role_exprs["context"] + role_exprs["setup"]
    pretrigger_text = " ".join(pretrigger_exprs)
    trigger_text = " ".join(role_exprs["trigger"])
    exit_text = " ".join(role_exprs["risk"])
    all_text = " ".join(lines)
    indicator_families = _indicator_families(all_text)
    pretrigger_indicator_families = _indicator_families(pretrigger_text)
    event_func_count = sum(
        1
        for func in ("cross_up", "cross_down", "between", "within")
        if re.search(rf"\b{func}\s*\(", trigger_text, re.IGNORECASE)
    )
    threshold_reclaim = bool(
        re.search(r"\b_d\d+\b", trigger_text, re.IGNORECASE)
        and re.search(r"(>|<|>=|<=)", trigger_text)
    )
    volume_qualified = bool(
        re.search(r"\b(?:volume|vol_ema_\d+)\b", pretrigger_text, re.IGNORECASE)
    )
    long_ema_refs = _count_distinct_matches(
        " ".join(role_exprs["context"]),
        re.compile(r"\bema_(?:50|100|200)\b", re.IGNORECASE),
    )
    slope_count = _count_distinct_matches(
        " ".join(role_exprs["context"]),
        re.compile(r"\b[a-z_0-9]+_slope\b", re.IGNORECASE),
    )
    stacked_trend_relations = len(
        re.findall(
            r"\bema_(?:20|30|40|50|100|200)\s*[<>]=?\s*ema_(?:20|30|40|50|100|200)\b",
            " ".join(role_exprs["context"]),
            re.IGNORECASE,
        )
    )
    context_has_long_trend_guard = bool(
        re.search(
            r"\bclose\s*[<>]=?\s*ema_(?:50|100|200)\b",
            " ".join(role_exprs["context"]),
            re.IGNORECASE,
        )
        or re.search(
            r"\b(?:st|supertrend)_\d+_\d+\b",
            " ".join(role_exprs["context"]),
            re.IGNORECASE,
        )
    )
    exit_style_count = 0
    if re.search(r"\b(?:close|open|high|low)\b", exit_text, re.IGNORECASE):
        exit_style_count += 1
    if re.search(r"\bcross_(?:up|down)\s*\(", exit_text, re.IGNORECASE):
        exit_style_count += 1
    if re.search(
        r"\b(?:ema_\d+|rsi(?:_ema)?_\d+(?:_\d+)?|macd(?:_signal)?|(?:st|supertrend)_\d+_\d+|(?:avwap|anchored_vwap)_(?:low|high)_\d+)\b",
        exit_text,
        re.IGNORECASE,
    ):
        exit_style_count += 1
    if re.search(
        r"\b(?:_slope|ema_(?:50|100|200)\s*[<>]=?\s*ema_(?:50|100|200))\b",
        exit_text,
        re.IGNORECASE,
    ):
        exit_style_count += 1

    trend_context = _clamp_score(
        (2.0 if role_exprs["context"] else 0.0)
        + min(3.0, long_ema_refs * 1.0)
        + min(2.0, slope_count * 0.6)
        + min(2.0, stacked_trend_relations * 0.75)
        + (1.0 if context_has_long_trend_guard else 0.0)
    )
    confirmation_depth = _clamp_score(
        1.5
        + (2.0 if role_exprs["context"] else 0.0)
        + (2.0 if role_exprs["setup"] else 0.0)
        + (1.5 if dedicated_qualify_block else 0.0)
        + min(3.0, math.log1p(len(pretrigger_exprs)) * 1.35)
        + (1.0 if len(pretrigger_exprs) >= 6 else 0.0)
        + min(1.0, max(0, len(pretrigger_indicator_families) - 1) * 0.5)
    )
    trigger_precision = _clamp_score(
        (2.0 if role_exprs["trigger"] else 0.0)
        + (2.5 if dedicated_trigger_block else 0.0)
        + min(3.5, event_func_count * 1.5)
        + (1.0 if threshold_reclaim else 0.0)
        + (1.0 if 0 < len(role_exprs["trigger"]) <= 2 else 0.0)
    )
    exit_discipline = _clamp_score(
        (2.0 if role_exprs["risk"] else 0.0)
        + (2.0 if dedicated_exit_block else 0.0)
        + min(3.0, explicit_exit_count * 1.0)
        + min(3.0, exit_style_count * 0.85)
    )
    risk_control = _clamp_score(
        1.0
        + (2.5 if max_days is not None else 0.0)
        + (1.5 if volume_qualified else 0.0)
        + (2.0 if context_has_long_trend_guard else 0.0)
        + (
            2.0
            if explicit_exit_count >= 2
            else 1.0 if explicit_exit_count == 1 else 0.0
        )
        + (1.0 if slope_count > 0 else 0.0)
    )
    if max_days is None:
        time_discipline_raw = 3.5
    elif max_days <= 10:
        time_discipline_raw = 10.0
    elif max_days <= 20:
        time_discipline_raw = 8.5
    elif max_days <= 40:
        time_discipline_raw = 7.0
    elif max_days <= 80:
        time_discipline_raw = 5.5
    else:
        time_discipline_raw = 4.0
    if event_func_count > 0 and max_days is not None:
        time_discipline_raw += 0.5
    time_discipline = _clamp_score(time_discipline_raw)

    axes = {
        "trend_context": trend_context,
        "confirmation_depth": confirmation_depth,
        "trigger_precision": trigger_precision,
        "exit_discipline": exit_discipline,
        "risk_control": risk_control,
        "time_discipline": time_discipline,
    }
    structure_score = round(
        sum(float(axes[key]) for key in STRATEGY_STRUCTURE_AXIS_ORDER)
        / len(STRATEGY_STRUCTURE_AXIS_ORDER),
        2,
    )

    tags: list[str] = []
    if trend_context >= 6.0:
        tags.append("trend_gated")
    if event_func_count > 0:
        tags.append("event_trigger")
    if volume_qualified:
        tags.append("volume_qualified")
    if max_days is not None:
        tags.append("has_time_stop")
    if explicit_exit_count >= 2:
        tags.append("multi_exit")
    if len(raw_blocks_seen) >= 3 or len(blocks) >= 3:
        tags.append("multi_block")
    if len(indicator_families) <= 1:
        tags.append("single_indicator_family")

    return {
        "structure_score": structure_score,
        "structure_axes": axes,
        "structure_tags": tags,
        "axis_order": list(STRATEGY_STRUCTURE_AXIS_ORDER),
    }
