"""Shared helpers for parsing ETF strategy DSL files."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyBlock:
    """Structured representation of one logical DSL block."""

    name: str
    layer: int
    expressions: tuple[str, ...]


_DEFAULT_SECTION_LAYER = {"TRIGGER": 3, "ENTRY": 3, "FILTER": 2, "EXIT": 4}
_FALLBACK_BLOCK_NAMES = {1: "Context", 2: "Setup", 3: "Trigger", 4: "Risk"}
_CANONICAL_ALIAS = {
    "context": (1, "context"),
    "setup": (2, "setup"),
    "qualify": (2, "setup"),
    "trigger": (3, "trigger"),
    "risk": (4, "risk"),
    "invalidate": (4, "risk"),
    "entry": (3, "trigger"),
    "exit": (4, "risk"),
}
_CANONICAL_PREFIX_ORDER = [
    "context",
    "setup",
    "qualify",
    "trigger",
    "risk",
    "invalidate",
    "entry",
    "exit",
]


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

        if begin_prefix or begin_suffix:
            raw_name = (
                begin_prefix.group(1).strip()
                if begin_prefix
                else begin_suffix.group(1).strip()
            )
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
