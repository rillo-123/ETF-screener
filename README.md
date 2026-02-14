# ETF-screener



## Quick Start

### Setup

```powershell
.\ensure-venv.ps1
`

### Run

```powershell
ETF_screener
`

### Test

```powershell
.\run_all_tests.ps1
`

## Development

- Code formatter: lack
- Import sorter: isort
- Linter: lake8
- Type checker: mypy

Run all checks:
```powershell
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
`
