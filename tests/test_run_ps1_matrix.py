import json
import os
import shutil
import subprocess
import textwrap
from itertools import combinations
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_PS1 = REPO_ROOT / "run.ps1"
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")

LAUNCHER_SCRIPTS = [
    "run_dashboard.ps1",
    "run_all_tests.ps1",
    "run_discovery.ps1",
    "run_movie_scan.ps1",
    "run_custom_backtest.ps1",
    "run_churn.ps1",
    "run_churn_all.ps1",
    "run_filtered_plots.ps1",
    "run_vulture.ps1",
]


def _powershell_available() -> bool:
    return POWERSHELL is not None


def _make_sandbox(tmp_path: Path) -> Path:
    sandbox = tmp_path / "run_ps1_sandbox"
    sandbox.mkdir()
    shutil.copy2(RUN_PS1, sandbox / "run.ps1")

    scripts_dir = sandbox / "scripts"
    scripts_dir.mkdir()

    stub = textwrap.dedent("""
        param(
            [Parameter(ValueFromRemainingArguments = $true)]
            [object[]]$RemainingArgs
        )

        if ($env:RUN_PS1_MATRIX_LOG) {
            $payload = [pscustomobject]@{
                Script = $MyInvocation.MyCommand.Name
                Args = @($RemainingArgs)
            }
            Add-Content -LiteralPath $env:RUN_PS1_MATRIX_LOG -Value ($payload | ConvertTo-Json -Compress -Depth 4)
        }

        exit 0
        """).strip()

    for script_name in LAUNCHER_SCRIPTS:
        (scripts_dir / script_name).write_text(stub + "\n", encoding="utf-8")

    return sandbox


def _run_launcher(script_path: Path, args: list[str], env: dict[str, str], cwd: Path):
    return subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            *args,
        ],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )


def _read_json_lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


@pytest.mark.skipif(
    not _powershell_available(),
    reason="PowerShell is required for run.ps1 matrix tests",
)
@pytest.mark.parametrize(
    "args,expected_script,expected_fragments",
    [
        ([], "run_dashboard.ps1", []),
        (["-Dashboard"], "run_dashboard.ps1", []),
        (["-Screener"], "run_dashboard.ps1", []),
        (["-Dashboard", "-Screener"], "run_dashboard.ps1", []),
        (["-Tests"], "run_all_tests.ps1", []),
        (["-Tests", "-All"], "run_all_tests.ps1", ["-Full"]),
        (["-Tests", "-QualityGate"], "run_all_tests.ps1", ["-Full"]),
        (
            [
                "-Discovery",
                "-StrategyPath",
                "strategies/",
                "-TickerFilter",
                "ETF",
                "-Plot",
                "1",
                "-Lookback",
                "12",
                "-Show",
                "-PlotDash",
                "-Clean",
            ],
            "run_discovery.ps1",
            [
                "-StrategyPath",
                "strategies/",
                "-TickerFilter",
                "ETF",
                "-Plot",
                "1",
                "-Lookback",
                "12",
                "-Show",
                "-PlotDash",
                "-Clean",
            ],
        ),
        (
            [
                "-MovieScan",
                "-TickerFilter",
                "%ETF%",
                "-Lookback",
                "20",
                "-Show",
                "-Plot",
                "2",
            ],
            "run_movie_scan.ps1",
            ["-TickerFilter", "%ETF%", "-Lookback", "20", "-Show", "-Plot", "2"],
        ),
        (
            [
                "-Backtest",
                "-Entry",
                "(ema_10 -gt ema_30)",
                "-Exit",
                "(rsi_14 -gt 75)",
                "-Filter",
                "value",
                "-OpenResult",
            ],
            "run_custom_backtest.ps1",
            [
                "-Entry",
                "(ema_10 -gt ema_30)",
                "-Exit",
                "(rsi_14 -gt 75)",
                "-Filter",
                "value",
                "-OpenResult",
            ],
        ),
        (
            [
                "-Churn",
                "-StrategyPath",
                "strategies/",
                "-TickerFilter",
                "ETF",
                "-Plot",
                "1",
                "-Lookback",
                "30",
                "-Show",
                "-PlotDash",
                "-Clean",
            ],
            "run_churn.ps1",
            [
                "-StrategyPath",
                "strategies/",
                "-TickerFilter",
                "ETF",
                "-Plot",
                "1",
                "-Lookback",
                "30",
                "-Show",
                "-PlotDash",
                "-Clean",
            ],
        ),
        (["-ChurnAll"], "run_churn_all.ps1", []),
        (
            [
                "-FilteredPlots",
                "EXS1.DE",
                "EUNG.DE",
                "-TickerFilter",
                "ETF",
                "-Format",
                "csv",
                "-Lookback",
                "15",
                "-MaxTickers",
                "3",
                "-Quiet",
                "-Clean",
            ],
            "run_filtered_plots.ps1",
            [
                "EXS1.DE",
                "EUNG.DE",
                "-MovieScan",
                "-TickerFilter",
                "ETF",
                "-Format",
                "csv",
                "-Lookback",
                "15",
                "-MaxTickers",
                "3",
                "-Quiet",
                "-Clean",
            ],
        ),
        (
            [
                "-Vulture",
                "-MinConfidence",
                "80",
                "-OutFile",
                "logs/vulture_report.txt",
                "-Open",
                "-ExtraArgs",
                "--foo",
                "-Exclude",
                ".venv,.git",
                "-RunTests",
            ],
            "run_vulture.ps1",
            [
                "-MinConfidence",
                "80",
                "-OutFile",
                "logs/vulture_report.txt",
                "-Open",
                "-ExtraArgs",
                "--foo",
                "-Exclude",
                ".venv,.git",
                "-RunTests",
            ],
        ),
    ],
)
def test_run_ps1_launcher_modes_forward_expected_arguments(
    tmp_path, args, expected_script, expected_fragments
):
    sandbox = _make_sandbox(tmp_path)
    log_path = sandbox / "matrix.log"
    env = os.environ.copy()
    env["RUN_PS1_MATRIX_LOG"] = str(log_path)

    result = _run_launcher(sandbox / "run.ps1", args, env, sandbox)

    assert result.returncode == 0, result.stderr or result.stdout

    rows = _read_json_lines(log_path)
    assert rows, f"Expected a launcher script call for args: {args}"

    assert rows[0]["Script"] == expected_script
    launched_args = rows[0].get("Args") or []
    joined_args = " ".join(str(item) for item in launched_args)
    for fragment in expected_fragments:
        assert fragment in joined_args


@pytest.mark.skipif(
    not _powershell_available(),
    reason="PowerShell is required for run.ps1 matrix tests",
)
@pytest.mark.parametrize(
    "first,second",
    list(
        combinations(
            [
                "-Dashboard",
                "-Tests",
                "-Discovery",
                "-MovieScan",
                "-Backtest",
                "-Churn",
                "-ChurnAll",
                "-FilteredPlots",
                "-Vulture",
            ],
            2,
        )
    ),
)
def test_run_ps1_rejects_multiple_launcher_modes(tmp_path, first, second):
    sandbox = _make_sandbox(tmp_path)
    log_path = sandbox / "matrix.log"
    env = os.environ.copy()
    env["RUN_PS1_MATRIX_LOG"] = str(log_path)

    result = _run_launcher(sandbox / "run.ps1", [first, second], env, sandbox)

    assert result.returncode != 0
    assert "Choose only one launcher mode at a time." in (
        result.stderr or result.stdout
    )
    assert _read_json_lines(log_path) == []
