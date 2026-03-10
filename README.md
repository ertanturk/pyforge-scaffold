# pyforge

`pyforge` is a CLI tool that scaffolds modern Python projects with sensible defaults for packaging, linting, testing, typing, and CI.

> **Note:** This is a personal/educational project. It is not intended to compete with established
> scaffold tools.

[![PyPI version](https://img.shields.io/pypi/v/pyforge-benchmark.svg)](https://pypi.org/project/pyforge-scaffold/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## What It Generates

- Interactive project setup with input validation
- `src/`-layout package structure
- PEP 621-compliant `pyproject.toml`
- Optional dynamic versioning helper in `scripts/setup.py`
- Optional GitHub Actions workflow
- Ready-to-use quality tooling configuration

## Installation

### Install from source (development)

```bash
python -m pip install -e .
```

### Install for CLI usage

Linux/macOS:

```bash
python3 -m pip install --user pyforge-scaffold

```

Windows:

```powershell
py -m pip install --user pyforge-scaffold
```

With `pipx`:

```bash
pipx install pyforge-scaffold
```

## Usage

Run:

```bash
pyforge
```

Follow the prompts, review the summary, and confirm project generation.

The generated project can optionally include a local virtual environment and install:

- `-e .[dev]` when recommended packages are enabled
- `-e .` otherwise

## Development

```bash
python -m pip install -e .[dev]
pre-commit install
```

## Build Distributions

```bash
python -m pip install --upgrade pip setuptools wheel build
python3 scripts/setup.py sdist bdist_wheel
```

Build artifacts are written to `dist/`.

## Validate Distributions

```bash
python -m twine check dist/*
```

## Publish to PyPI

1. Create a PyPI API token.
2. Export credentials:

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-XXXXXXXXXXXXXXXXXXXXXXXX
```

3. Upload distributions:

```bash
python -m twine upload dist/*
```

Optional TestPyPI dry run:

```bash
python -m twine upload --repository testpypi dist/*
```
