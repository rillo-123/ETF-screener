"""Safe interpreter for the initial candle-oriented DSLX strategy subset.

DSLX intentionally has its own parser and evaluator.  It never delegates source
text to Python ``eval`` and does not alter the legacy ``.dsl`` execution path.
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

    def as_dict(self) -> dict[str, object]:
        return {
            "strategy": self.strategy,
            "ticker": self.ticker,
            "timestamp": self.timestamp,
            "age": self.age,
            "open": self.candle.open,
            "high": self.candle.high,
            "low": self.candle.low,
            "close": self.candle.close,
            "volume": self.candle.volume,
        }


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
    entry: Lambda
    exit: Lambda | None = None
    entry_execution: str = "next_open"
    exit_execution: str = "next_open"
    source: str = "universe.selected"
    timeframe: str = "1d"
    candle_style: str = "regular"
    scan: str = "latest"


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
        entry: Lambda | None = None
        exit_rule: Lambda | None = None
        entry_execution = "next_open"
        exit_execution = "next_open"
        source = "universe.selected"
        timeframe = "1d"
        candle_style = "regular"
        scan = "latest"
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
            elif keyword in {"entry", "exit", "match"}:
                self.expect("when")
                expression = self.parse_expression()
                if not isinstance(expression, Lambda):
                    raise DSLXSyntaxError(
                        f"{keyword} rule must use a lambda such as 'candle => candle.close > candle.ema(20)'"
                    )
                if keyword in {"entry", "match"}:
                    if entry is not None:
                        raise DSLXSyntaxError("A strategy can define only one match/entry rule")
                    entry = expression
                else:
                    if exit_rule is not None:
                        raise DSLXSyntaxError("A strategy can define only one exit rule")
                    exit_rule = expression
            else:
                raise DSLXSyntaxError(f"Unknown strategy section '{keyword}'")
            self.accept(";")
        if require_eof and self.current.kind != "eof":
            raise DSLXSyntaxError(f"Unexpected token at offset {self.current.offset}")
        if entry is None:
            raise DSLXSyntaxError("A strategy needs an entry rule")
        return Strategy(
            name, entry, exit_rule, entry_execution, exit_execution,
            source, timeframe, candle_style, scan,
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
    """A numeric indicator value anchored to one focal candle."""

    def __new__(cls, value: float, slope: float):
        instance = float.__new__(cls, value)
        instance._slope = slope
        return instance

    @property
    def slope(self) -> float:
        """One-finalized-candle change in this indicator value."""
        return self._slope


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

    def indicator(self, name: str, index: int, *args: object) -> IndicatorValue:
        if not args or not isinstance(args[-1], int) or args[-1] <= 0:
            raise DSLXEvaluationError(f"{name} requires a positive integer period")
        period = int(args[-1])
        source = "close"
        if name in {"ema", "sma"} and len(args) == 2:
            source = str(args[0]).lower()
        elif len(args) != 1:
            raise DSLXEvaluationError(f"Invalid arguments for {name}")
        values = pd.Series(
            [self.value(row, source) for row in range(len(self.frame))], dtype=float
        )
        if index + 1 < period:
            raise InsufficientHistory(f"{name}({period}) needs {period} candles")
        if name == "volume_ema":
            source = "volume"
            values = pd.Series([self.value(row, source) for row in range(len(self.frame))], dtype=float)
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
            high = pd.Series([self.value(row, "high") for row in range(len(self.frame))])
            low = pd.Series([self.value(row, "low") for row in range(len(self.frame))])
            close = pd.Series([self.value(row, "close") for row in range(len(self.frame))])
            true_range = pd.concat(
                [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1
            ).max(axis=1)
            result = true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        else:
            raise DSLXEvaluationError(f"Unsupported indicator '{name}'")
        value = result.iloc[index]
        if pd.isna(value):
            raise InsufficientHistory(f"{name}({period}) is unavailable at this candle")
        prior = result.iloc[index - 1] if index else np.nan
        slope = float(value - prior) if pd.notna(prior) else 0.0
        return IndicatorValue(float(value), slope)


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

    def ema(self, *args: object) -> IndicatorValue:
        return self.series.indicator("ema", self.index, *args)

    def sma(self, *args: object) -> IndicatorValue:
        return self.series.indicator("sma", self.index, *args)

    def rsi(self, period: int) -> IndicatorValue:
        return self.series.indicator("rsi", self.index, period)

    def atr(self, period: int) -> IndicatorValue:
        return self.series.indicator("atr", self.index, period)

    def volume_ema(self, period: int) -> IndicatorValue:
        return self.series.indicator("volume_ema", self.index, period)


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
            "previous", "window", "ema", "sma", "rsi", "atr", "volume_ema",
        },
        CandleWindow: {"all", "any", "count", "high", "low", "close", "volume"},
        ValueSequence: {"max", "min", "average"},
        IndicatorValue: {"slope"},
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


class DSLXInterpreter:
    """Compile and evaluate one DSLX strategy against finalized candles."""

    def __init__(self, source: str):
        self.strategy = parse_strategy(source)

    def matches_entry(self, frame: pd.DataFrame, endpoint: int | None = None) -> bool:
        return self._matches(self.strategy.entry, frame, endpoint, self.strategy.candle_style)

    def matches_exit(self, frame: pd.DataFrame, endpoint: int | None = None) -> bool:
        if self.strategy.exit is None:
            return False
        return self._matches(self.strategy.exit, frame, endpoint, self.strategy.candle_style)

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
                    matched = bool(LambdaValue(self.strategy.entry, {})(candle))
                except InsufficientHistory:
                    matched = False
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
                    )
                )
        return MatchList(matches)

    @staticmethod
    def _matches(
        rule: Lambda, frame: pd.DataFrame, endpoint: int | None, candle_style: str = "regular"
    ) -> bool:
        series = CandleSeries(frame, style=candle_style)
        candle = series.last if endpoint is None else series.candle_at(endpoint)
        try:
            return bool(LambdaValue(rule, {})(candle))
        except InsufficientHistory:
            return False


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
