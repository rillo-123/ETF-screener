"""Safe interpreter for the initial candle-oriented DSLX strategy subset.

DSLX intentionally has its own parser and evaluator.  It never delegates source
text to Python ``eval`` and does not alter the separate legacy ``.dsl`` execution
path.  DSLX strategies themselves use named candle definitions and ordered
``entrystruct`` / ``exitstruct`` patterns only.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable, cast

import numpy as np
import pandas as pd


class DSLXError(ValueError):
    """Base class for DSLX parse and evaluation errors."""


class DSLXSyntaxError(DSLXError):
    """Raised when DSLX source cannot be parsed."""


class DSLXEvaluationError(DSLXError):
    """Raised for a valid expression that cannot be evaluated."""


class InsufficientHistory(DSLXEvaluationError):
    """Raised when a candle operation needs bars before the series begins."""


@dataclass(frozen=True)
class Match:
    """One strategy match, retaining the ticker and focal candle provenance."""

    strategy: str
    ticker: str
    candle: "Candle"
    age: int
    timestamp: object | None = None
    pattern: tuple[tuple[str, "Candle"], ...] = ()

    def as_dict(self) -> dict[str, object]:
        try:
            rsi = float(self.candle.rsi(14))
        except InsufficientHistory:
            rsi = None
        record: dict[str, object] = {
            "strategy": self.strategy,
            "ticker": self.ticker,
            "timestamp": self.timestamp,
            "age": self.age,
            "open": self.candle.open,
            "high": self.candle.high,
            "low": self.candle.low,
            "close": self.candle.close,
            "volume": self.candle.volume,
            "rsi": rsi,
        }
        if self.pattern:
            record["candles"] = [
                {
                    "name": name,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                }
                for name, candle in self.pattern
            ]
        return record


class MatchList(tuple[Match, ...]):
    """Immutable strategy-result collection that preserves match provenance."""

    def __new__(cls, matches: Iterable[Match] = ()) -> "MatchList":
        return super().__new__(cls, tuple(matches))

    def __add__(self, other: object) -> "MatchList":
        if not isinstance(other, MatchList):
            return NotImplemented
        return MatchList((*self, *other))

    def show(self) -> list[dict[str, object]]:
        """Return host-renderable records; the dashboard owns visual display."""
        return [match.as_dict() for match in self]


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    offset: int


_TOKEN_RE = re.compile(
    r"\s+|//[^\n]*|#[^\n]*|"
    r"(?P<number>\d+(?:_\d{3})*(?:\.\d+)?)|"
    r"(?P<string>\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*')|"
    r"(?P<operator>=>|&&|\|\||>=|<=|==|!=|>|<|[=+\-*/!])|"
    r"(?P<punct>[{}()\[\].,:;])|"
    r"(?P<identifier>[A-Za-z_][A-Za-z0-9_]*)"
)


def tokenize(source: str) -> list[Token]:
    """Turn DSLX source into tokens, rejecting unknown characters."""
    tokens: list[Token] = []
    position = 0
    while position < len(source):
        match = _TOKEN_RE.match(source, position)
        if not match:
            raise DSLXSyntaxError(f"Unexpected character at offset {position}")
        position = match.end()
        kind = match.lastgroup
        if kind is None:
            continue
        tokens.append(Token(kind, match.group(kind), match.start(kind)))
    tokens.append(Token("eof", "", len(source)))
    return tokens


@dataclass(frozen=True)
class Literal:
    value: object


@dataclass(frozen=True)
class Name:
    value: str


@dataclass(frozen=True)
class Attribute:
    target: object
    name: str


@dataclass(frozen=True)
class Call:
    target: object
    args: tuple[object, ...]


@dataclass(frozen=True)
class Unary:
    operator: str
    value: object


@dataclass(frozen=True)
class Binary:
    operator: str
    left: object
    right: object


@dataclass(frozen=True)
class Lambda:
    parameter: str
    body: object


@dataclass(frozen=True)
class Strategy:
    name: str
    entry_price: object | None = None
    entry_execution: str = "next_open"
    exit_execution: str = "next_open"
    source: str = "universe.selected"
    timeframe: str = "1d"
    candle_style: str = "regular"
    scan: str = "latest"
    candle_definitions: tuple["CandleDefinition", ...] = ()
    entry_struct: tuple[str, ...] | None = None
    exit_struct: tuple[str, ...] | None = None


@dataclass(frozen=True)
class CandleDefinition:
    """A named candle predicate whose time position is assigned by a struct."""

    name: str
    condition: object


@dataclass(frozen=True)
class LiquidityClause:
    """One lookback-based liquidity condition for a named universe."""

    metric: str
    sessions: int
    operator: str
    value: float


@dataclass(frozen=True)
class UniverseDefinition:
    """A reusable, pre-strategy universe narrowed by market eligibility."""

    name: str
    source: str
    liquidity: tuple[LiquidityClause, ...]


@dataclass(frozen=True)
class Program:
    universes: tuple[UniverseDefinition, ...]
    strategies: tuple[Strategy, ...]
    runs: tuple[tuple[str, str], ...]
    merges: tuple[tuple[str, str, str], ...]
    shows: tuple[str, ...]


_ROLLING_CALL_COSTS = {
    "ema": 20,
    "sma": 20,
    "volume_ema": 20,
    "rsi": 30,
    "atr": 35,
}


def _expression_cost(expression: object) -> int:
    """Estimate evaluation work so pure conjunctions can reject cheaply."""
    if isinstance(expression, Literal):
        return 0
    if isinstance(expression, Name):
        return 1
    if isinstance(expression, Attribute):
        return _expression_cost(expression.target) + 1
    if isinstance(expression, Call):
        call_name = (
            expression.target.value
            if isinstance(expression.target, Name)
            else expression.target.name
            if isinstance(expression.target, Attribute)
            else ""
        )
        period_cost = 0
        if call_name in _ROLLING_CALL_COSTS and expression.args:
            period = expression.args[-1]
            if isinstance(period, Literal) and isinstance(period.value, int):
                period_cost = period.value
        return (
            _ROLLING_CALL_COSTS.get(call_name, 8)
            + period_cost
            + _expression_cost(expression.target)
            + sum(_expression_cost(argument) for argument in expression.args)
        )
    if isinstance(expression, Unary):
        return 1 + _expression_cost(expression.value)
    if isinstance(expression, Binary):
        return 1 + _expression_cost(expression.left) + _expression_cost(expression.right)
    if isinstance(expression, Lambda):
        return _expression_cost(expression.body)
    return 1


def _conjunction_terms(expression: object) -> list[object]:
    if isinstance(expression, Binary) and expression.operator == "and":
        return [*_conjunction_terms(expression.left), *_conjunction_terms(expression.right)]
    return [expression]


def _optimize_conjunctions(expression: object) -> object:
    """Put cheap terms first in side-effect-free ``and`` expressions."""
    if isinstance(expression, Attribute):
        return Attribute(_optimize_conjunctions(expression.target), expression.name)
    if isinstance(expression, Call):
        return Call(
            _optimize_conjunctions(expression.target),
            tuple(_optimize_conjunctions(argument) for argument in expression.args),
        )
    if isinstance(expression, Unary):
        return Unary(expression.operator, _optimize_conjunctions(expression.value))
    if isinstance(expression, Lambda):
        return Lambda(expression.parameter, _optimize_conjunctions(expression.body))
    if not isinstance(expression, Binary):
        return expression
    left = _optimize_conjunctions(expression.left)
    right = _optimize_conjunctions(expression.right)
    optimized = Binary(expression.operator, left, right)
    if expression.operator != "and":
        return optimized
    terms = sorted(_conjunction_terms(optimized), key=_expression_cost)
    result = terms[0]
    for term in terms[1:]:
        result = Binary("and", result, term)
    return result


_IMPLICIT_CANDLE_NAMES = {
    "open", "high", "low", "close", "volume",
    "is_green", "is_red", "is_doji", "color",
    "total_length", "range", "body_length",
    "upper_wick_length", "lower_wick_length",
    "body_ratio", "upper_wick_ratio", "lower_wick_ratio",
    "previous", "window", "within_ema_band", "ema", "sma", "rsi", "atr",
    "volume_ema",
}


def _expression_names(expression: object | None) -> set[str]:
    """Collect bare identifiers from an expression for semantic validation."""
    if expression is None or isinstance(expression, Literal):
        return set()
    if isinstance(expression, Name):
        return {expression.value}
    if isinstance(expression, Attribute):
        return _expression_names(expression.target)
    if isinstance(expression, Call):
        names = _expression_names(expression.target)
        for argument in expression.args:
            names.update(_expression_names(argument))
        return names
    if isinstance(expression, Unary):
        return _expression_names(expression.value)
    if isinstance(expression, Binary):
        return _expression_names(expression.left) | _expression_names(expression.right)
    if isinstance(expression, Lambda):
        return _expression_names(expression.body) - {expression.parameter}
    return set()


class _Parser:
    def __init__(self, source: str):
        self.tokens = tokenize(source)
        self.index = 0

    @property
    def current(self) -> Token:
        return self.tokens[self.index]

    def accept(self, value: str) -> bool:
        if self.current.value == value:
            self.index += 1
            return True
        return False

    def expect(self, value: str) -> Token:
        if not self.accept(value):
            found = self.current.value or "end of input"
            raise DSLXSyntaxError(
                f"Expected '{value}' at offset {self.current.offset}, found '{found}'"
            )
        return self.tokens[self.index - 1]

    def expect_identifier(self) -> str:
        token = self.current
        if token.kind != "identifier":
            raise DSLXSyntaxError(f"Expected identifier at offset {token.offset}")
        self.index += 1
        return token.value

    def parse_strategy(self, *, require_eof: bool = True) -> Strategy:
        if self.expect_identifier().lower() != "strategy":
            raise DSLXSyntaxError("DSLX source must start with 'strategy'")
        name = self.expect_identifier()
        self.expect("{")
        entry_price: object | None = None
        entry_execution = "next_open"
        exit_execution = "next_open"
        source = "universe.selected"
        timeframe = "1d"
        candle_style = "regular"
        scan = "latest"
        candle_definitions: list[CandleDefinition] = []
        entry_struct: tuple[str, ...] | None = None
        exit_struct: tuple[str, ...] | None = None
        while not self.accept("}"):
            keyword = self.expect_identifier().lower()
            if keyword == "execution":
                entry_execution, exit_execution = self.parse_execution()
            elif keyword == "source":
                source = self.parse_dotted_name()
            elif keyword == "candles":
                if self.expect_identifier().lower() != "timeframe":
                    raise DSLXSyntaxError("candles requires a timeframe")
                if self.current.kind != "string":
                    raise DSLXSyntaxError("candle timeframe must be a string such as \"1d\"")
                timeframe = self.current.value[1:-1]
                self.index += 1
                if self.expect_identifier().lower() != "as":
                    raise DSLXSyntaxError("candles requires 'as regular' or 'as heikin_ashi'")
                candle_style = self.expect_identifier().lower()
                if candle_style not in {"regular", "heikin_ashi"}:
                    raise DSLXSyntaxError("candle style must be regular or heikin_ashi")
            elif keyword == "scan":
                scan = self.expect_identifier().lower()
                if scan == "within":
                    if self.current.kind != "number" or "." in self.current.value:
                        raise DSLXSyntaxError("scan within requires a positive candle count")
                    count = int(self.current.value)
                    self.index += 1
                    if count < 1 or self.expect_identifier().lower() != "candles":
                        raise DSLXSyntaxError("scan within requires '<positive count> candles'")
                    scan = f"within:{count}"
                elif scan != "latest":
                    raise DSLXSyntaxError("scan must be latest or within <count> candles")
            elif keyword == "candle":
                candle_definitions.append(self.parse_candle_definition())
            elif keyword in {"entrystruct", "exitstruct"}:
                members, struct_price_expression = self.parse_pattern_struct(
                    allow_price=keyword == "entrystruct"
                )
                if keyword == "entrystruct":
                    if entry_struct is not None:
                        raise DSLXSyntaxError("A strategy can define only one entrystruct")
                    entry_struct = members
                    entry_price = struct_price_expression
                else:
                    if exit_struct is not None:
                        raise DSLXSyntaxError("A strategy can define only one exitstruct")
                    exit_struct = members
            elif keyword in {"entry", "exit", "match"}:
                raise DSLXSyntaxError(
                    f"Legacy '{keyword} when candle =>' rules are no longer supported; "
                    "define named candle objects and use entrystruct/exitstruct"
                )
            else:
                raise DSLXSyntaxError(f"Unknown strategy section '{keyword}'")
            self.accept(";")
        if require_eof and self.current.kind != "eof":
            raise DSLXSyntaxError(f"Unexpected token at offset {self.current.offset}")
        if entry_struct is None:
            raise DSLXSyntaxError("A strategy needs an entrystruct")
        if exit_struct is None:
            raise DSLXSyntaxError(
                "A strategy needs an exitstruct; use 'exitstruct { pass }' for a no-op exit"
            )
        strategy = Strategy(
            name=name,
            entry_price=entry_price,
            entry_execution=entry_execution,
            exit_execution=exit_execution,
            source=source,
            timeframe=timeframe,
            candle_style=candle_style,
            scan=scan,
            candle_definitions=tuple(candle_definitions),
            entry_struct=entry_struct,
            exit_struct=exit_struct,
        )
        self.validate_pattern_structs(strategy)
        return strategy

    def parse_candle_definition(self) -> CandleDefinition:
        """Parse ``candle name { when => <implicit-candle expression> }``."""
        name = self.expect_identifier()
        self.expect("{")
        if self.expect_identifier().lower() != "when":
            raise DSLXSyntaxError(f"Candle '{name}' requires a when condition")
        self.expect("=>")
        condition = _optimize_conjunctions(self.parse_expression())
        self.accept(";")
        self.expect("}")
        return CandleDefinition(name, condition)

    def parse_pattern_struct(self, *, allow_price: bool) -> tuple[tuple[str, ...], object | None]:
        """Parse an ordered list of named candles; the last member is newest."""
        self.expect("{")
        members: list[str] = []
        price_expression: object | None = None
        passed = False
        while not self.accept("}"):
            name = self.expect_identifier()
            if name.lower() == "at":
                if not allow_price:
                    raise DSLXSyntaxError("Only entrystruct can declare an entry price")
                if price_expression is not None:
                    raise DSLXSyntaxError("entrystruct can declare only one entry price")
                price_expression = self.parse_expression()
            elif name.lower() == "pass":
                passed = True
            else:
                members.append(name)
            self.accept(",")
            self.accept(";")
        if passed and members:
            raise DSLXSyntaxError("pass cannot be combined with candles in a struct")
        if not members and not passed:
            raise DSLXSyntaxError("A candle struct cannot be empty")
        if allow_price and passed:
            raise DSLXSyntaxError("entrystruct cannot be pass")
        return tuple(members), price_expression

    @staticmethod
    def validate_pattern_structs(strategy: Strategy) -> None:
        """Resolve candle references before a strategy is allowed to run."""
        definitions = {item.name: item for item in strategy.candle_definitions}
        if len(definitions) != len(strategy.candle_definitions):
            raise DSLXSyntaxError("Candle names must be unique within a strategy")
        for label, members in (
            ("entrystruct", strategy.entry_struct or ()),
            ("exitstruct", strategy.exit_struct or ()),
        ):
            if len(members) != len(set(members)):
                raise DSLXSyntaxError(f"{label} cannot contain the same candle more than once")
            for index, member in enumerate(members):
                definition = definitions.get(member)
                if definition is None:
                    raise DSLXSyntaxError(f"{label} references unknown candle '{member}'")
                for reference in _expression_names(definition.condition):
                    if reference == "position":
                        if label != "exitstruct":
                            raise DSLXSyntaxError(
                                f"{label} candle '{member}' cannot reference position"
                            )
                        continue
                    if reference in _IMPLICIT_CANDLE_NAMES or reference == member:
                        continue
                    if reference not in definitions:
                        raise DSLXSyntaxError(
                            f"{label} candle '{member}' references unknown name '{reference}'"
                        )
                    if reference not in members:
                        raise DSLXSyntaxError(
                            f"{label} candle '{member}' references '{reference}', "
                            "but it is not a member of this structure"
                        )
                    if members.index(reference) > index:
                        raise DSLXSyntaxError(
                            f"{label} candle '{member}' cannot reference later candle '{reference}'"
                        )
            if label == "entrystruct" and strategy.entry_struct is not None:
                for reference in _expression_names(strategy.entry_price):
                    if reference not in members and reference not in _IMPLICIT_CANDLE_NAMES:
                        raise DSLXSyntaxError(
                            f"entrystruct price references unavailable candle '{reference}'"
                        )

    def parse_program(self) -> Program:
        universes: list[UniverseDefinition] = []
        strategies: list[Strategy] = []
        runs: list[tuple[str, str]] = []
        merges: list[tuple[str, str, str]] = []
        shows: list[str] = []
        while self.current.kind != "eof":
            keyword = self.current.value.lower()
            if keyword == "universe":
                universes.append(self.parse_universe())
                self.accept(";")
                continue
            if keyword == "strategy":
                strategies.append(self.parse_strategy(require_eof=False))
                self.accept(";")
                continue
            if keyword == "let":
                self.index += 1
                target = self.expect_identifier()
                self.expect("=")
                value_name = self.expect_identifier()
                if self.accept("."):
                    if self.expect_identifier().lower() != "run":
                        raise DSLXSyntaxError("A let binding can only call strategy.run()")
                    self.expect("(")
                    self.expect(")")
                    runs.append((target, value_name))
                elif self.accept("+"):
                    merges.append((target, value_name, self.expect_identifier()))
                else:
                    raise DSLXSyntaxError("A let binding must run a strategy or combine two MatchLists")
            else:
                list_name = self.expect_identifier()
                self.expect(".")
                if self.expect_identifier().lower() != "show":
                    raise DSLXSyntaxError("Only MatchList.show() is allowed at program level")
                self.expect("(")
                self.expect(")")
                shows.append(list_name)
            self.accept(";")
        names = [universe.name for universe in universes]
        if len(names) != len(set(names)):
            raise DSLXSyntaxError("Universe names must be unique within a program")
        return Program(
            tuple(universes), tuple(strategies), tuple(runs), tuple(merges), tuple(shows)
        )

    def parse_universe(self) -> UniverseDefinition:
        """Parse a top-level, data-eligibility universe declaration."""
        if self.expect_identifier().lower() != "universe":
            raise DSLXSyntaxError("Expected a universe declaration")
        name = self.expect_identifier()
        self.expect("{")
        source: str | None = None
        liquidity: list[LiquidityClause] = []
        while not self.accept("}"):
            keyword = self.expect_identifier().lower()
            if keyword == "from":
                if source is not None:
                    raise DSLXSyntaxError("A universe can define only one source")
                source = self.parse_dotted_name()
            elif keyword == "require":
                if self.expect_identifier().lower() != "liquidity":
                    raise DSLXSyntaxError("A universe requirement must be 'liquidity'")
                self.expect("{")
                while not self.accept("}"):
                    metric = self.expect_identifier().lower()
                    if metric not in {"avg_turnover", "median_turnover", "active_sessions"}:
                        raise DSLXSyntaxError(
                            "liquidity supports avg_turnover, median_turnover, and active_sessions"
                        )
                    self.expect("(")
                    if self.current.kind != "number" or "." in self.current.value:
                        raise DSLXSyntaxError("liquidity lookback must be a positive integer")
                    sessions = int(self.current.value)
                    self.index += 1
                    if sessions < 1:
                        raise DSLXSyntaxError("liquidity lookback must be positive")
                    self.expect(")")
                    if self.current.value not in {">", ">=", "<", "<=", "==", "!="}:
                        raise DSLXSyntaxError("liquidity condition requires a comparison operator")
                    operator = self.current.value
                    self.index += 1
                    if self.current.kind != "number":
                        raise DSLXSyntaxError("liquidity condition requires a numeric threshold")
                    value = float(self.current.value)
                    self.index += 1
                    if value < 0:
                        raise DSLXSyntaxError("liquidity threshold must be non-negative")
                    liquidity.append(LiquidityClause(metric, sessions, operator, value))
                    self.accept(";")
            else:
                raise DSLXSyntaxError(f"Unknown universe section '{keyword}'")
            self.accept(";")
        if source is None:
            raise DSLXSyntaxError("A universe requires 'from universe.<source>'")
        if not liquidity:
            raise DSLXSyntaxError("A universe requires at least one liquidity condition")
        return UniverseDefinition(name, source, tuple(liquidity))

    def parse_dotted_name(self) -> str:
        parts = [self.expect_identifier()]
        while self.accept("."):
            parts.append(self.expect_identifier())
        return ".".join(parts)

    def parse_execution(self) -> tuple[str, str]:
        self.expect("{")
        values = {"entry": "next_open", "exit": "next_open"}
        while not self.accept("}"):
            key = self.expect_identifier().lower()
            if key not in values:
                raise DSLXSyntaxError("execution accepts only entry and exit settings")
            self.expect(":")
            value = self.expect_identifier().lower()
            if value not in {"next_open", "close"}:
                raise DSLXSyntaxError("execution values must be next_open or close")
            values[key] = value
            self.accept(",")
            self.accept(";")
        return values["entry"], values["exit"]

    def parse_expression(self) -> object:
        return self.parse_or()

    def parse_or(self) -> object:
        expression = self.parse_and()
        while self.current.value.lower() == "or" or self.current.value == "||":
            self.index += 1
            expression = Binary("or", expression, self.parse_and())
        return expression

    def parse_and(self) -> object:
        expression = self.parse_comparison()
        while self.current.value.lower() == "and" or self.current.value == "&&":
            self.index += 1
            expression = Binary("and", expression, self.parse_comparison())
        return expression

    def parse_comparison(self) -> object:
        expression = self.parse_sum()
        comparisons: list[tuple[str, object]] = []
        while self.current.value in {">", ">=", "<", "<=", "==", "!="}:
            operator = self.current.value
            self.index += 1
            comparisons.append((operator, self.parse_sum()))
        if not comparisons:
            return expression
        left = expression
        result: object | None = None
        for operator, right in comparisons:
            comparison = Binary(operator, left, right)
            result = comparison if result is None else Binary("and", result, comparison)
            left = right
        return result

    def parse_sum(self) -> object:
        expression = self.parse_product()
        while self.current.value in {"+", "-"}:
            operator = self.current.value
            self.index += 1
            expression = Binary(operator, expression, self.parse_product())
        return expression

    def parse_product(self) -> object:
        expression = self.parse_unary()
        while self.current.value in {"*", "/"}:
            operator = self.current.value
            self.index += 1
            expression = Binary(operator, expression, self.parse_unary())
        return expression

    def parse_unary(self) -> object:
        if self.current.value in {"-", "+"}:
            operator = self.current.value
            self.index += 1
            return Unary(operator, self.parse_unary())
        if self.current.value.lower() == "not" or self.current.value == "!":
            self.index += 1
            return Unary("not", self.parse_unary())
        return self.parse_lambda_or_postfix()

    def parse_lambda_or_postfix(self) -> object:
        if (
            self.current.kind == "identifier"
            and self.tokens[self.index + 1].value == "=>"
        ):
            parameter = self.current.value
            self.index += 2
            return Lambda(parameter, self.parse_expression())
        return self.parse_postfix()

    def parse_postfix(self) -> object:
        expression = self.parse_primary()
        while True:
            if self.accept("."):
                expression = Attribute(expression, self.expect_identifier())
            elif self.accept("("):
                arguments: list[object] = []
                if not self.accept(")"):
                    while True:
                        arguments.append(self.parse_expression())
                        if self.accept(")"):
                            break
                        self.expect(",")
                expression = Call(expression, tuple(arguments))
            else:
                return expression

    def parse_primary(self) -> object:
        token = self.current
        if token.kind == "number":
            self.index += 1
            return Literal(float(token.value) if "." in token.value else int(token.value))
        if token.kind == "string":
            self.index += 1
            return Literal(token.value[1:-1])
        if token.kind == "identifier":
            self.index += 1
            value = token.value.lower()
            if value == "true":
                return Literal(True)
            if value == "false":
                return Literal(False)
            if value == "pass":
                return Literal(False)
            return Name(token.value)
        if self.accept("("):
            expression = self.parse_expression()
            self.expect(")")
            return expression
        raise DSLXSyntaxError(f"Expected expression at offset {token.offset}")


def parse_strategy(source: str) -> Strategy:
    """Parse one DSLX strategy declaration."""
    return _Parser(source).parse_strategy()


def parse_program(source: str) -> Program:
    """Parse a DSLX module containing strategies and run/show statements."""
    return _Parser(source).parse_program()


class ValueSequence:
    """A safe, ordered sequence of numeric candle values."""

    def __init__(self, values: Iterable[float]):
        self.values = tuple(float(value) for value in values)

    def max(self) -> float:
        if not self.values:
            raise InsufficientHistory("Cannot take max of an empty candle window")
        return max(self.values)

    def min(self) -> float:
        if not self.values:
            raise InsufficientHistory("Cannot take min of an empty candle window")
        return min(self.values)

    def average(self) -> float:
        if not self.values:
            raise InsufficientHistory("Cannot average an empty candle window")
        return float(np.mean(self.values))


class CandleWindow:
    """A contiguous chronological window ending at one candle."""

    def __init__(self, candles: tuple["Candle", ...]):
        self.candles = candles

    def __getitem__(self, index: int) -> "Candle":
        return self.candles[index]

    def all(self, predicate: LambdaValue) -> bool:
        return all(bool(predicate(candle)) for candle in self.candles)

    def any(self, predicate: LambdaValue) -> bool:
        return any(bool(predicate(candle)) for candle in self.candles)

    def count(self, predicate: LambdaValue) -> int:
        return sum(1 for candle in self.candles if bool(predicate(candle)))

    @property
    def high(self) -> ValueSequence:
        return ValueSequence(candle.high for candle in self.candles)

    @property
    def low(self) -> ValueSequence:
        return ValueSequence(candle.low for candle in self.candles)

    @property
    def close(self) -> ValueSequence:
        return ValueSequence(candle.close for candle in self.candles)

    @property
    def volume(self) -> ValueSequence:
        return ValueSequence(candle.volume for candle in self.candles)


class IndicatorValue(float):
    """A numeric indicator value anchored to one focal candle.

    EMA and SMA values also retain their focal candle so strategies can express
    visual relationships such as ``candle.ema(20).within_body`` directly.
    """

    def __new__(cls, value: float, slope: float, candle: "Candle | None" = None):
        instance = float.__new__(cls, value)
        instance._slope = slope
        instance._candle = candle
        return instance

    @property
    def slope(self) -> float:
        """One-finalized-candle change in this indicator value."""
        return self._slope

    def _within(self, lower: float, upper: float, *, include_lower: bool = True,
                include_upper: bool = True) -> bool:
        if self._candle is None:
            raise DSLXEvaluationError("Candle-region predicates require a candle indicator")
        value = float(self)
        lower_match = value >= lower if include_lower else value > lower
        upper_match = value <= upper if include_upper else value < upper
        return lower_match and upper_match

    @property
    def within_body(self) -> bool:
        """Whether the indicator lies in the inclusive open-to-close body."""
        candle = self._candle
        if candle is None:
            raise DSLXEvaluationError("Candle-region predicates require a candle indicator")
        return self._within(min(candle.open, candle.close), max(candle.open, candle.close))

    @property
    def not_within_body(self) -> bool:
        """Whether the indicator lies strictly outside the open-to-close body."""
        return not self.within_body

    @property
    def within_upper_wick(self) -> bool:
        """Whether the indicator lies above the body and up to the candle high."""
        candle = self._candle
        if candle is None:
            raise DSLXEvaluationError("Candle-region predicates require a candle indicator")
        return self._within(max(candle.open, candle.close), candle.high, include_lower=False)

    @property
    def within_lower_wick(self) -> bool:
        """Whether the indicator lies from the candle low up to below the body."""
        candle = self._candle
        if candle is None:
            raise DSLXEvaluationError("Candle-region predicates require a candle indicator")
        return self._within(candle.low, min(candle.open, candle.close), include_upper=False)


class EMABand:
    """A high/low EMA channel anchored to one focal candle."""

    def __init__(self, candle: "Candle", upper_source: str, lower_source: str, period: int):
        self.candle = candle
        self.upper_source = upper_source
        self.lower_source = lower_source
        self.period = period

    @property
    def contains(self) -> bool:
        """Whether the focal candle, including wicks, lies inside this EMA band."""
        first = float(
            self.candle.series.indicator("ema", self.candle.index, self.upper_source, self.period)
        )
        second = float(
            self.candle.series.indicator("ema", self.candle.index, self.lower_source, self.period)
        )
        lower, upper = min(first, second), max(first, second)
        return self.candle.low >= lower and self.candle.high <= upper


class CandleSeries:
    """Immutable chronological OHLCV data exposed to DSLX evaluation."""

    def __init__(self, frame: pd.DataFrame, *, style: str = "regular"):
        self.frame = frame.reset_index(drop=True).copy()
        if style not in {"regular", "heikin_ashi"}:
            raise DSLXEvaluationError(f"Unsupported candle style '{style}'")
        columns = {str(column).lower(): str(column) for column in self.frame.columns}
        self.columns = columns
        required = {"open", "high", "low", "close", "volume"}
        missing = required.difference(columns)
        if missing:
            raise DSLXEvaluationError(
                "Candle data is missing required columns: " + ", ".join(sorted(missing))
            )
        if style == "heikin_ashi":
            self._apply_heikin_ashi()
            self.columns = {str(column).lower(): str(column) for column in self.frame.columns}
        self._source_series_cache: dict[str, pd.Series] = {}
        self._indicator_series_cache: dict[tuple[str, str, int], pd.Series] = {}

    def _apply_heikin_ashi(self) -> None:
        """Replace OHLC with the Heikin-Ashi candle series, preserving volume."""
        open_ = pd.to_numeric(self.frame[self.columns["open"]], errors="coerce")
        high = pd.to_numeric(self.frame[self.columns["high"]], errors="coerce")
        low = pd.to_numeric(self.frame[self.columns["low"]], errors="coerce")
        close = pd.to_numeric(self.frame[self.columns["close"]], errors="coerce")
        ha_close = (open_ + high + low + close) / 4
        ha_open = ha_close.copy()
        if len(ha_open):
            ha_open.iloc[0] = (open_.iloc[0] + close.iloc[0]) / 2
            for row in range(1, len(ha_open)):
                ha_open.iloc[row] = (ha_open.iloc[row - 1] + ha_close.iloc[row - 1]) / 2
        self.frame[self.columns["open"]] = ha_open
        self.frame[self.columns["close"]] = ha_close
        self.frame[self.columns["high"]] = pd.concat([high, ha_open, ha_close], axis=1).max(axis=1)
        self.frame[self.columns["low"]] = pd.concat([low, ha_open, ha_close], axis=1).min(axis=1)

    @property
    def last(self) -> "Candle":
        if self.frame.empty:
            raise InsufficientHistory("Candle series is empty")
        return Candle(self, len(self.frame) - 1)

    def candle_at(self, index: int) -> "Candle":
        if index < 0 or index >= len(self.frame):
            raise InsufficientHistory("Requested candle is outside available history")
        return Candle(self, index)

    def value(self, index: int, field: str) -> float:
        column = self.columns.get(field.lower())
        if column is None:
            raise DSLXEvaluationError(f"Unknown candle field '{field}'")
        value = self.frame.iloc[index][column]
        if pd.isna(value):
            raise InsufficientHistory(f"Candle field '{field}' is unavailable")
        return float(value)

    def _source_series(self, source: str) -> pd.Series:
        """Return one numeric OHLCV series, materialized once per ticker."""
        normalized = source.lower()
        cached = self._source_series_cache.get(normalized)
        if cached is None:
            cached = pd.Series(
                [self.value(row, normalized) for row in range(len(self.frame))], dtype=float
            )
            self._source_series_cache[normalized] = cached
        return cached

    def _indicator_series(self, name: str, source: str, period: int) -> pd.Series:
        """Calculate a rolling indicator once and reuse it at every endpoint."""
        key = (name, source, period)
        cached = self._indicator_series_cache.get(key)
        if cached is not None:
            return cached
        values = self._source_series(source)
        if name == "volume_ema":
            result = values.ewm(span=period, adjust=False, min_periods=period).mean()
        elif name == "ema":
            result = values.ewm(span=period, adjust=False, min_periods=period).mean()
        elif name == "sma":
            result = values.rolling(period, min_periods=period).mean()
        elif name == "rsi":
            delta = values.diff()
            gains = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
            losses = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
            relative_strength = gains / losses.replace(0, np.nan)
            result = 100 - (100 / (1 + relative_strength))
            # A series with gains but no losses is maximally overbought, not
            # unknown. Keep the all-flat case undefined.
            result = result.where(losses != 0, np.where(gains > 0, 100.0, np.nan))
        elif name == "atr":
            high = self._source_series("high")
            low = self._source_series("low")
            close = self._source_series("close")
            true_range = pd.concat(
                [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1
            ).max(axis=1)
            result = true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        else:
            raise DSLXEvaluationError(f"Unsupported indicator '{name}'")
        self._indicator_series_cache[key] = result
        return result

    def indicator(self, name: str, index: int, *args: object) -> IndicatorValue:
        if not args or not isinstance(args[-1], int) or args[-1] <= 0:
            raise DSLXEvaluationError(f"{name} requires a positive integer period")
        period = int(args[-1])
        source = "close"
        if name in {"ema", "sma"} and len(args) == 2:
            source = str(args[0]).lower()
        elif len(args) != 1:
            raise DSLXEvaluationError(f"Invalid arguments for {name}")
        if index + 1 < period:
            raise InsufficientHistory(f"{name}({period}) needs {period} candles")
        if name == "volume_ema":
            source = "volume"
        result = self._indicator_series(name, source, period)
        value = result.iloc[index]
        if pd.isna(value):
            raise InsufficientHistory(f"{name}({period}) is unavailable at this candle")
        prior = result.iloc[index - 1] if index else np.nan
        slope = float(value - prior) if pd.notna(prior) else 0.0
        candle = Candle(self, index) if name in {"ema", "sma"} else None
        return IndicatorValue(float(value), slope, candle)


class Candle:
    """One immutable finalized candle, with access only to earlier candles.

    Geometry is derived exclusively from this candle's OHLC values.  Therefore
    the same properties describe either regular or Heikin-Ashi candles: create
    the series with the corresponding OHLC values and the visual measurements
    follow naturally.
    """

    def __init__(self, series: CandleSeries, index: int):
        self.series = series
        self.index = index

    @property
    def open(self) -> float:
        return self.series.value(self.index, "open")

    @property
    def high(self) -> float:
        return self.series.value(self.index, "high")

    @property
    def low(self) -> float:
        return self.series.value(self.index, "low")

    @property
    def close(self) -> float:
        return self.series.value(self.index, "close")

    @property
    def volume(self) -> float:
        return self.series.value(self.index, "volume")

    @property
    def is_green(self) -> bool:
        return self.close > self.open

    @property
    def is_red(self) -> bool:
        return self.close < self.open

    @property
    def is_doji(self) -> bool:
        """Whether the candle has no real body (open equals close)."""
        return self.close == self.open

    @property
    def color(self) -> str:
        """The visible candle colour: ``green``, ``red``, or ``doji``."""
        if self.is_green:
            return "green"
        if self.is_red:
            return "red"
        return "doji"

    @property
    def total_length(self) -> float:
        """Full high-to-low length of the candle, including both wicks."""
        return self.high - self.low

    @property
    def range(self) -> float:
        """Alias for :attr:`total_length`."""
        return self.total_length

    @property
    def body_length(self) -> float:
        """Absolute real-body length, independent of candle colour."""
        return abs(self.close - self.open)

    @property
    def upper_wick_length(self) -> float:
        """Length from the top of the body to the high."""
        return self.high - max(self.open, self.close)

    @property
    def lower_wick_length(self) -> float:
        """Length from the low to the bottom of the body."""
        return min(self.open, self.close) - self.low

    def _proportion_of_total_length(self, length: float) -> float:
        """Return a visible part as a fraction of the full candle length."""
        total_length = self.total_length
        return length / total_length if total_length else 0.0

    @property
    def body_ratio(self) -> float:
        """Real-body length divided by the full high-to-low length."""
        return self._proportion_of_total_length(self.body_length)

    @property
    def upper_wick_ratio(self) -> float:
        """Upper-wick length divided by the full high-to-low length."""
        return self._proportion_of_total_length(self.upper_wick_length)

    @property
    def lower_wick_ratio(self) -> float:
        """Lower-wick length divided by the full high-to-low length."""
        return self._proportion_of_total_length(self.lower_wick_length)

    def previous(self, bars: int = 1) -> "Candle":
        if not isinstance(bars, int) or bars < 1:
            raise DSLXEvaluationError("previous() requires a positive integer")
        return self.series.candle_at(self.index - bars)

    def window(self, size: int) -> CandleWindow:
        if not isinstance(size, int) or size < 1:
            raise DSLXEvaluationError("window() requires a positive integer")
        start = self.index - size + 1
        if start < 0:
            raise InsufficientHistory(f"window({size}) needs {size} candles")
        return CandleWindow(tuple(self.series.candle_at(row) for row in range(start, self.index + 1)))

    def within_ema_band(self, period: int) -> bool:
        """Whether the entire candle fits inside its EMA low/high band.

        The lower boundary is ``ema("low", period)`` and the upper boundary
        is ``ema("high", period)``.  Both wicks are included, so a candle
        only matches when ``low >= lower`` and ``high <= upper``.
        """
        return EMABand(self, "high", "low", period).contains

    def ema(self, *args: object) -> IndicatorValue | EMABand:
        if len(args) == 3 and isinstance(args[0], str) and isinstance(args[1], str):
            period = args[2]
            if not isinstance(period, int) or period <= 0:
                raise DSLXEvaluationError("ema band requires a positive integer period")
            return EMABand(self, args[0].lower(), args[1].lower(), period)
        return self.series.indicator("ema", self.index, *args)

    def sma(self, *args: object) -> IndicatorValue:
        return self.series.indicator("sma", self.index, *args)

    def rsi(self, period: int) -> IndicatorValue:
        return self.series.indicator("rsi", self.index, period)

    def atr(self, period: int) -> IndicatorValue:
        return self.series.indicator("atr", self.index, period)

    def volume_ema(self, period: int) -> IndicatorValue:
        return self.series.indicator("volume_ema", self.index, period)


@dataclass(frozen=True)
class Position:
    """The open long position available only while evaluating an exit rule."""

    entry_price: float


class LambdaValue:
    """Callable closure created from a DSLX lambda node."""

    def __init__(self, expression: Lambda, environment: dict[str, object]):
        self.expression = expression
        self.environment = dict(environment)

    def __call__(self, value: object) -> object:
        scope = dict(self.environment)
        scope[self.expression.parameter] = value
        return _evaluate(self.expression.body, scope)


def _attribute(value: object, name: str) -> object:
    allowed = {
        Candle: {
            "open", "high", "low", "close", "volume",
            "is_green", "is_red", "is_doji", "color",
            "total_length", "range", "body_length",
            "upper_wick_length", "lower_wick_length",
            "body_ratio", "upper_wick_ratio", "lower_wick_ratio",
            "previous", "window", "within_ema_band", "ema", "sma", "rsi", "atr", "volume_ema",
        },
        Position: {"entry_price"},
        CandleWindow: {"all", "any", "count", "high", "low", "close", "volume"},
        ValueSequence: {"max", "min", "average"},
        IndicatorValue: {
            "slope", "within_body", "not_within_body",
            "within_upper_wick", "within_lower_wick",
        },
        EMABand: {"contains"},
    }
    for value_type, names in allowed.items():
        if isinstance(value, value_type):
            if name not in names:
                raise DSLXEvaluationError(f"'{name}' is not available on {value_type.__name__}")
            return getattr(value, name)
    raise DSLXEvaluationError(f"Cannot access '{name}' on this value")


def _evaluate(expression: object, environment: dict[str, object]) -> object:
    if isinstance(expression, Literal):
        return expression.value
    if isinstance(expression, Name):
        if expression.value not in environment:
            raise DSLXEvaluationError(f"Unknown name '{expression.value}'")
        return environment[expression.value]
    if isinstance(expression, Attribute):
        return _attribute(_evaluate(expression.target, environment), expression.name)
    if isinstance(expression, Call):
        target = _evaluate(expression.target, environment)
        if not callable(target):
            raise DSLXEvaluationError("Only approved DSLX methods can be called")
        return target(*[_evaluate(argument, environment) for argument in expression.args])
    if isinstance(expression, Lambda):
        return LambdaValue(expression, environment)
    if isinstance(expression, Unary):
        value = _evaluate(expression.value, environment)
        if expression.operator == "not":
            return not bool(value)
        numeric_value = cast(Any, value)
        return -numeric_value if expression.operator == "-" else +numeric_value
    if isinstance(expression, Binary):
        left = _evaluate(expression.left, environment)
        if expression.operator == "and":
            return bool(left) and bool(_evaluate(expression.right, environment))
        if expression.operator == "or":
            return bool(left) or bool(_evaluate(expression.right, environment))
        right = _evaluate(expression.right, environment)
        left_value = cast(Any, left)
        right_value = cast(Any, right)
        operations = {
            "+": lambda: left_value + right_value,
            "-": lambda: left_value - right_value,
            "*": lambda: left_value * right_value,
            "/": lambda: left_value / right_value,
            ">": lambda: left_value > right_value,
            ">=": lambda: left_value >= right_value,
            "<": lambda: left_value < right_value,
            "<=": lambda: left_value <= right_value,
            "==": lambda: left_value == right_value,
            "!=": lambda: left_value != right_value,
        }
        return operations[expression.operator]()
    raise DSLXEvaluationError("Unsupported DSLX syntax node")


def _implicit_candle_environment(candle: Candle) -> dict[str, object]:
    """Expose the safe Candle surface without requiring a repeated object prefix."""
    return {name: _attribute(candle, name) for name in _IMPLICIT_CANDLE_NAMES}


def _match_pattern(
    strategy: Strategy,
    members: tuple[str, ...],
    series: CandleSeries,
    endpoint: int,
    *,
    position: Position | None = None,
) -> tuple[bool, dict[str, object], tuple[tuple[str, Candle], ...]]:
    """Bind an ordered struct to consecutive candles ending at ``endpoint``."""
    if not members:
        return False, {}, ()
    first_index = endpoint - len(members) + 1
    if first_index < 0:
        raise InsufficientHistory(f"Pattern needs {len(members)} consecutive candles")
    definitions = {item.name: item for item in strategy.candle_definitions}
    pattern = tuple(
        (name, series.candle_at(first_index + offset))
        for offset, name in enumerate(members)
    )
    bindings: dict[str, object] = dict(pattern)
    if position is not None:
        bindings["position"] = position
    for name, candle in pattern:
        environment = dict(bindings)
        environment.update(_implicit_candle_environment(candle))
        if not bool(_evaluate(definitions[name].condition, environment)):
            return False, environment, pattern
    final_environment = dict(bindings)
    final_environment.update(_implicit_candle_environment(pattern[-1][1]))
    return True, final_environment, pattern


def _structured_take_profit_fill_price(
    strategy: Strategy, environment: dict[str, object]
) -> float | None:
    """Recognize a position-relative target in a matched exit candle predicate."""
    definitions = {item.name: item for item in strategy.candle_definitions}
    for name in reversed(strategy.exit_struct or ()):
        expression = definitions[name].condition
        if not (
            isinstance(expression, Binary)
            and expression.operator in {">", ">="}
            and "position" in _expression_names(expression.right)
        ):
            continue
        try:
            observed = float(_evaluate(expression.left, environment))
            target = float(_evaluate(expression.right, environment))
        except (DSLXEvaluationError, TypeError, ValueError):
            continue
        if np.isfinite(target) and observed >= target:
            return target
    return None


class DSLXInterpreter:
    """Compile and evaluate one DSLX strategy against finalized candles."""

    def __init__(self, source: str):
        self.strategy = parse_strategy(source)

    def matches_entry(self, frame: pd.DataFrame, endpoint: int | None = None) -> bool:
        series = CandleSeries(frame, style=self.strategy.candle_style)
        resolved_endpoint = len(series.frame) - 1 if endpoint is None else endpoint
        try:
            return _match_pattern(
                self.strategy, cast(tuple[str, ...], self.strategy.entry_struct), series, resolved_endpoint
            )[0]
        except InsufficientHistory:
            return False

    def matches_exit(self, frame: pd.DataFrame, endpoint: int | None = None) -> bool:
        if not self.strategy.exit_struct:
            return False
        series = CandleSeries(frame, style=self.strategy.candle_style)
        resolved_endpoint = len(series.frame) - 1 if endpoint is None else endpoint
        try:
            return _match_pattern(self.strategy, self.strategy.exit_struct, series, resolved_endpoint)[0]
        except InsufficientHistory:
            return False

    def run(self, frames: dict[str, pd.DataFrame]) -> MatchList:
        """Evaluate this strategy over provided ticker frames and return matches."""
        matches: list[Match] = []
        for ticker, frame in frames.items():
            series = CandleSeries(frame, style=self.strategy.candle_style)
            if series.frame.empty:
                continue
            if self.strategy.scan == "latest":
                endpoints = (len(series.frame) - 1,)
            else:
                count = int(self.strategy.scan.split(":", 1)[1])
                endpoints = range(max(0, len(series.frame) - count), len(series.frame))
            for endpoint in endpoints:
                candle = series.candle_at(endpoint)
                try:
                    if self.strategy.entry_struct is not None:
                        matched, _environment, pattern = _match_pattern(
                            self.strategy, self.strategy.entry_struct, series, endpoint
                        )
                    else:
                        matched = bool(
                            LambdaValue(cast(Lambda, self.strategy.entry), {})(candle)
                        )
                        pattern = ()
                except InsufficientHistory:
                    matched = False
                    pattern = ()
                if not matched:
                    continue
                timestamp = next(
                    (
                        series.frame.iloc[endpoint][column]
                        for column in ("date", "Date", "timestamp", "Timestamp")
                        if column in series.frame
                    ),
                    None,
                )
                matches.append(
                    Match(
                        self.strategy.name,
                        str(ticker),
                        candle,
                        len(series.frame) - 1 - endpoint,
                        timestamp,
                        pattern,
                    )
                )
        return MatchList(matches)

def _liquidity_clause_matches(frame: pd.DataFrame, clause: LiquidityClause) -> bool:
    """Evaluate one universe-level liquidity clause from finalized OHLCV bars."""
    close_column = next((name for name in ("Close", "close") if name in frame), None)
    volume_column = next((name for name in ("Volume", "volume") if name in frame), None)
    if close_column is None or volume_column is None:
        return False
    close = pd.to_numeric(frame[close_column], errors="coerce").tail(clause.sessions)
    volume = pd.to_numeric(frame[volume_column], errors="coerce").tail(clause.sessions)
    if len(close) < clause.sessions or len(volume) < clause.sessions:
        return False
    turnover = (close * volume).replace([np.inf, -np.inf], np.nan)
    if clause.metric == "avg_turnover":
        observed = float(turnover.mean()) if turnover.notna().all() else float("nan")
    elif clause.metric == "median_turnover":
        observed = float(turnover.median()) if turnover.notna().all() else float("nan")
    else:
        observed = float(((volume > 0) & close.notna() & volume.notna()).sum())
    if not np.isfinite(observed):
        return False
    comparisons = {
        ">": observed > clause.value,
        ">=": observed >= clause.value,
        "<": observed < clause.value,
        "<=": observed <= clause.value,
        "==": observed == clause.value,
        "!=": observed != clause.value,
    }
    return comparisons[clause.operator]


def _filter_universe(
    frames: dict[str, pd.DataFrame], definition: UniverseDefinition
) -> dict[str, pd.DataFrame]:
    """Keep only instruments that meet every declared eligibility condition."""
    return {
        ticker: frame
        for ticker, frame in frames.items()
        if all(_liquidity_clause_matches(frame, clause) for clause in definition.liquidity)
    }


class DSLXProgramInterpreter:
    """Execute a parsed DSLX module against host-provided universes."""

    def __init__(self, source: str):
        self.program = parse_program(source)
        self.strategies = {strategy.name: strategy for strategy in self.program.strategies}
        if len(self.strategies) != len(self.program.strategies):
            raise DSLXSyntaxError("Strategy names must be unique within a program")

    def run(
        self,
        *,
        selected: dict[str, pd.DataFrame],
        universes: dict[str, dict[str, pd.DataFrame]] | None = None,
    ) -> dict[str, MatchList]:
        """Run program bindings; hosts render the lists named by ``show()``."""
        available_universes = dict(universes or {})
        available_universes["universe.selected"] = selected
        for definition in self.program.universes:
            source_frames = available_universes.get(definition.source)
            if source_frames is None:
                raise DSLXEvaluationError(
                    f"Universe '{definition.source}' required by '{definition.name}' is unavailable"
                )
            available_universes[f"universe.{definition.name}"] = _filter_universe(
                source_frames, definition
            )
        values: dict[str, MatchList] = {}
        for target, strategy_name in self.program.runs:
            strategy = self.strategies.get(strategy_name)
            if strategy is None:
                raise DSLXEvaluationError(f"Unknown strategy '{strategy_name}'")
            frames = available_universes.get(strategy.source)
            if frames is None:
                raise DSLXEvaluationError(f"Universe '{strategy.source}' is unavailable")
            runner = object.__new__(DSLXInterpreter)
            runner.strategy = strategy
            values[target] = runner.run(frames)
        for target, left, right in self.program.merges:
            if left not in values or right not in values:
                raise DSLXEvaluationError("MatchList combination refers to an unknown list")
            values[target] = values[left] + values[right]
        for name in self.program.shows:
            if name not in values:
                raise DSLXEvaluationError(f"Unknown MatchList '{name}'")
        return {name: values[name] for name in self.program.shows}


def backtest_signals(source: str, frame: pd.DataFrame, *, ticker: str = "BACKTEST") -> pd.DataFrame:
    """Evaluate one DSLX strategy across historical finalized candles.

    The returned frame contains entry/exit masks and an execution signal suitable
    for the existing trade simulator.  It deliberately evaluates each candle at
    its own endpoint, so no rule can read a later candle.
    """
    program = DSLXProgramInterpreter(source)
    if len(program.program.strategies) != 1:
        raise DSLXSyntaxError("A DSLX backtest program must declare exactly one strategy")
    strategy = program.program.strategies[0]
    available: dict[str, dict[str, pd.DataFrame]] = {
        "universe.selected": {ticker: frame},
    }
    for definition in program.program.universes:
        source_frames = available.get(definition.source)
        if source_frames is None:
            raise DSLXEvaluationError(
                f"Universe '{definition.source}' required by '{definition.name}' is unavailable"
            )
        available[f"universe.{definition.name}"] = _filter_universe(
            source_frames, definition
        )
    if ticker not in available.get(strategy.source, {}):
        result = frame.copy()
        result["entry_condition"] = False
        result["exit_condition"] = False
        result["signal"] = 0
        return result

    series = CandleSeries(frame, style=strategy.candle_style)
    entry_mask: list[bool] = []
    exit_mask: list[bool] = []
    signals: list[int] = []
    exit_fill_prices: list[float] = []
    entry_fill_prices: list[float] = []
    position: Position | None = None
    close_column = next((name for name in ("Close", "close") if name in frame), None)
    if close_column is None:
        raise DSLXEvaluationError("Candle data is missing Close for position entry pricing")
    raw_close = pd.to_numeric(frame[close_column], errors="coerce")
    for endpoint in range(len(frame)):
        candle = series.candle_at(endpoint)
        entry_environment: dict[str, object] = {"candle": candle}
        try:
            entered, entry_environment, _entry_pattern = _match_pattern(
                strategy, cast(tuple[str, ...], strategy.entry_struct), series, endpoint
            )
        except InsufficientHistory:
            entered = False
        entry_mask.append(entered)

        exited = False
        exit_fill_price: float | None = None
        if position is not None:
            try:
                if strategy.exit_struct:
                    exited, exit_environment, _exit_pattern = _match_pattern(
                        strategy,
                        strategy.exit_struct,
                        series,
                        endpoint,
                        position=position,
                    )
                    if exited:
                        exit_fill_price = _structured_take_profit_fill_price(
                            strategy, exit_environment
                        )
            except InsufficientHistory:
                exited = False
        exit_mask.append(exited)
        exit_fill_prices.append(float(exit_fill_price) if exit_fill_price is not None else np.nan)

        # Keep signal order identical to the one-position trade simulator: an
        # open position exits first; a fresh entry is accepted only while flat.
        if position is not None and exited:
            position = None
            signals.append(-1)
            entry_fill_prices.append(np.nan)
        elif position is None and entered:
            price = raw_close.iloc[endpoint]
            if strategy.entry_price is not None:
                try:
                    price = float(_evaluate(strategy.entry_price, entry_environment))
                except (DSLXEvaluationError, TypeError, ValueError):
                    price = np.nan
            if pd.notna(price):
                if float(price) <= 0:
                    raise DSLXEvaluationError("entry price must be positive")
                position = Position(float(price))
                signals.append(1)
                entry_fill_prices.append(float(price))
            else:
                signals.append(0)
                entry_fill_prices.append(np.nan)
        else:
            signals.append(0)
            entry_fill_prices.append(np.nan)
    result = frame.copy()
    result["entry_condition"] = entry_mask
    result["exit_condition"] = exit_mask
    result["exit_fill_price"] = exit_fill_prices
    result["entry_fill_price"] = entry_fill_prices
    result["signal"] = signals
    return result
