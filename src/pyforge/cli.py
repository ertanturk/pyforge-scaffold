"""CLI module for pyforge."""

import re
import subprocess  # nosec B404
import sys
from datetime import datetime
from os import name as os_name
from pathlib import Path
from typing import TypedDict

# PEP 508 / PyPI-compatible package name: starts with a letter,
# then letters/digits/-/_/.
_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._\-]*$")
# Version specifier: operator followed by a dotted numeric version (e.g. >=3.12).
_VERSION_RE = re.compile(r"^(>=|<=|~=|==|!=|>|<)\d+(\.\d+){1,2}$")
# Minimal email sanity check: local@domain.tld
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")

_DEFAULT_AUTHOR = "Ertan Tunç Türk"
_DEFAULT_EMAIL = "ertantuncturk61@gmail.com"


def _print_banner() -> None:
    """Print a simple CLI banner for better readability."""

    print("\n" + "=" * 60)
    print("pyforge - Python project scaffolding")
    print("=" * 60)


def _prompt_non_empty(prompt: str, error: str) -> str:
    """Prompt until a non-empty value is entered."""

    while True:
        value = input(prompt).strip()
        if value:
            return value
        print(f"  Error: {error}")


def _prompt_yes_no(prompt: str, default_yes: bool = True) -> bool:
    """Prompt for a yes/no response with a default."""

    suffix = "Y/N, default Y" if default_yes else "Y/N, default N"
    default_value = "y" if default_yes else "n"
    while True:
        raw = input(f"{prompt} ({suffix}): ").strip().lower()
        if raw == "":
            raw = default_value
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("  Error: Please enter Y or N.")


def _prompt_choice(prompt: str, choices: set[str], default: str) -> str:
    """Prompt for a constrained choice value."""

    while True:
        value = input(prompt).strip() or default
        if value in choices:
            return value
        choices_text = ", ".join(sorted(choices))
        print(f"  Error: Please enter one of: {choices_text}.")


_DEV_PACKAGES = [
    "ruff",
    "mypy",
    "pytest",
    "pytest-cov",
    "bandit",
    "pip-audit",
    "pre-commit",
    "coverage",
    "build",
    "twine",
]


class ProjectDetails(TypedDict):
    """Collected project settings used to generate a scaffold."""

    name: str
    description: str
    python_version: str
    keywords: str
    author: str
    email: str
    license: str
    dynamic_versioning: bool
    install_recommended: bool
    github_workflow: bool
    create_venv: bool


def _normalize_module_name(project_name: str) -> str:
    """Convert package name to a safe Python module name."""

    module = project_name.replace("-", "_").replace(".", "_")
    if not module.isidentifier():
        module = re.sub(r"[^A-Za-z0-9_]", "_", module)
    return module


def _parse_keywords(keywords: str) -> list[str]:
    """Parse comma-separated keywords into a normalized list."""

    return [keyword.strip() for keyword in keywords.split(",") if keyword.strip()]


def _normalize_python_version_spec(version_input: str) -> str:
    """Normalize Python version specifier, defaulting bare versions to >=."""

    value = version_input.strip()
    if value and value[0].isdigit():
        return f">={value}"
    return value


def _extract_python_major_minor(version_spec: str) -> tuple[str, str]:
    """Extract major/minor version numbers from validated Python specifier."""

    match = re.search(r"(\d+)\.(\d+)", version_spec)
    if match is None:
        return "3", "12"
    return match.group(1), match.group(2)


def _license_metadata(
    license_choice: str, author: str
) -> tuple[str | None, str | None]:
    """Return SPDX license id and license file content from selected option."""

    year = datetime.now().year
    if license_choice == "1":
        mit_lines = [
            "MIT License",
            "",
            f"Copyright (c) {year} {author}",
            "",
            "Permission is hereby granted, free of charge, to any person",
            "obtaining a copy of this software and associated documentation",
            'files (the "Software"), to deal in the Software without',
            "restriction, including without limitation the rights to use,",
            "copy, modify, merge, publish, distribute, sublicense, and/or",
            "sell copies of the Software, and to permit persons to whom",
            "the Software is furnished to do so, subject to the following",
            "conditions:",
            "",
            "The above copyright notice and this permission notice shall",
            "be included in all copies or substantial portions of the",
            "Software.",
            "",
            'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY',
            "KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE",
            "WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR",
            "PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS",
            "OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR",
            "OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR",
            "OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE",
            "SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.",
        ]
        return "MIT", "\n".join(mit_lines) + "\n"

    if license_choice == "2":
        apache = (
            "Apache License\n"
            "Version 2.0, January 2004\n"
            "https://www.apache.org/licenses/\n\n"
            f"Copyright {year} {author}\n\n"
            'Licensed under the Apache License, Version 2.0 (the "License");\n'
            "you may not use this file except in compliance with the License.\n"
            "You may obtain a copy of the License at\n\n"
            "    http://www.apache.org/licenses/LICENSE-2.0\n\n"
            "Unless required by applicable law or agreed to in writing, software\n"
            'distributed under the License is distributed on an "AS IS" BASIS,\n'
            "WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n"
            "See the License for the specific language governing permissions and\n"
            "limitations under the License.\n"
        )
        return "Apache-2.0", apache

    return None, None


def _build_pyproject(details: ProjectDetails, module_name: str) -> str:
    """Build pyproject.toml for the generated project."""

    keywords = _parse_keywords(details["keywords"])
    keywords_block = "\n".join(f'  "{keyword}",' for keyword in keywords)
    if keywords_block:
        keywords_block = f"\n{keywords_block}\n"

    license_id, _ = _license_metadata(details["license"], details["author"])
    license_line = f'license = "{license_id}"\n' if license_id else ""

    py_major, py_minor = _extract_python_major_minor(details["python_version"])

    classifiers = [
        '    "Development Status :: 3 - Alpha",',
        '    "Intended Audience :: Developers",',
        '    "Intended Audience :: Education",',
    ]
    classifiers.extend(
        [
            '    "Operating System :: OS Independent",',
            '    "Programming Language :: Python :: 3",',
            f'    "Programming Language :: Python :: {py_major}.{py_minor}",',
            '    "Typing :: Typed",',
            '    "Topic :: Software Development :: Libraries",',
            '    "Topic :: Software Development :: Testing",',
            '    "Topic :: Software Development :: Build Tools",',
        ]
    )
    classifiers_block = "\n".join(classifiers)

    if details["dynamic_versioning"]:
        version_block = 'dynamic = ["version"]\n'
    else:
        version_block = 'version = "0.1.0"\n'

    if details["install_recommended"]:
        optional_deps = "\n".join(f'    "{pkg}",' for pkg in _DEV_PACKAGES)
    else:
        optional_deps = ""

    return (
        "[build-system]\n"
        'requires = ["setuptools>=68", "wheel"]\n'
        'build-backend = "setuptools.build_meta"\n\n'
        "[project]\n"
        f'name = "{details["name"]}"\n'
        f"{version_block}"
        f'description = "{details["description"]}"\n'
        'readme = "README.md"\n'
        f'requires-python = "{details["python_version"]}"\n'
        f"{license_line}"
        "dependencies = []\n"
        f"keywords = [{keywords_block}]\n\n"
        "authors = [\n"
        f'    {{ name = "{details["author"]}", email = "{details["email"]}" }},\n'
        "]\n\n"
        "maintainers = [\n"
        f'    {{ name = "{details["author"]}", email = "{details["email"]}" }},\n'
        "]\n\n"
        "classifiers = [\n"
        f"{classifiers_block}\n"
        "]\n\n"
        "[project.optional-dependencies]\n"
        "dev = [\n"
        f"{optional_deps}\n"
        "]\n\n"
        "[project.urls]\n"
        f'Homepage = "https://github.com/{details["author"]}/{details["name"]}"\n'
        f'Repository = "https://github.com/{details["author"]}/{details["name"]}"\n'
        f'Documentation = "https://github.com/{details["author"]}/{details["name"]}#readme"\n'
        f'Issues = "https://github.com/{details["author"]}/{details["name"]}/issues"\n\n'
        "[project.scripts]\n"
        f'{details["name"]} = "{module_name}.cli:main"\n\n'
        "[tool.ruff]\n"
        "line-length = 88\n"
        f'target-version = "py{py_major}{py_minor}"\n\n'
        "[tool.ruff.lint]\n"
        'select = ["E", "F", "I", "B", "UP"]\n'
        "ignore = []\n\n"
        "[tool.mypy]\n"
        f'python_version = "{py_major}.{py_minor}"\n'
        "strict = true\n"
        "ignore_missing_imports = true\n"
        "warn_unused_configs = true\n\n"
        "[tool.pytest.ini_options]\n"
        'addopts = "-v --tb=short"\n'
        'testpaths = ["tests"]\n'
        'minversion = "7.0"\n\n'
        "[tool.coverage.run]\n"
        "branch = true\n"
        'source = ["."]\n'
        'omit = ["tests/*", ".venv/*"]\n\n'
        "[tool.coverage.report]\n"
        "show_missing = true\n"
        "fail_under = 80\n\n"
        "[tool.bandit]\n"
        'exclude_dirs = ["tests", ".venv"]\n'
        'skips = ["B101"]\n'
    )


def _build_dynamic_setup() -> str:
    """Build scripts/setup.py content for dynamic versioning."""

    lines = [
        '"""Dynamic version setup for the project."""',
        "",
        "import json",
        "from urllib.error import HTTPError, URLError",
        "from urllib.request import urlopen",
        "",
        "from setuptools import setup",
        "",
        "IS_INITIAL_PUBLISH = True",
        "",
        "",
        "def read_project_name() -> str:",
        '    with open("pyproject.toml") as f:',
        "        for line in f:",
        '            if line.startswith("name ="):',
        '                return line.split("=")[1].strip().strip("\\"")',
        '    raise FileNotFoundError("Project name not found in pyproject.toml")',
        "",
        "",
        "def read_internal_cache_version() -> str | None:",
        "    try:",
        '        with open(".version_cache") as f:',
        "            return f.read().strip()",
        "    except FileNotFoundError:",
        "        return None",
        "",
        "",
        "def fetch_latest_version(project_name: str) -> str | None:",
        '    url = f"https://pypi.org/pypi/{project_name}/json"',
        "    try:",
        "        with urlopen(url) as response:  # nosec B310",
        '            if getattr(response, "status", 200) != 200:',
        "                return None",
        "            data = json.loads(response.read())",
        '            return data.get("info", {}).get("version")',
        "    except (HTTPError, URLError):",
        "        return None",
        "",
        "",
        "def write_version_cache(version: str) -> None:",
        '    with open(".version_cache", "w") as f:',
        "        f.write(version)",
        "",
        "",
        "def calculate_next_version(latest_version: str) -> str:",
        '    major, minor, patch = map(int, latest_version.split("."))',
        "    if patch < 20:",
        "        patch += 1",
        "    else:",
        "        patch = 0",
        "        if minor < 10:",
        "            minor += 1",
        "        else:",
        "            minor = 0",
        "            major += 1",
        '    return f"{major}.{minor}.{patch}"',
        "",
        "",
        "def dynamic_version() -> str:",
        "    project_name = read_project_name()",
        "    latest_version = fetch_latest_version(project_name)",
        "",
        "    if latest_version is None:",
        "        cached_version = read_internal_cache_version()",
        "        if cached_version is not None:",
        "            new_version = calculate_next_version(cached_version)",
        "            write_version_cache(new_version)",
        "            return new_version",
        "        if IS_INITIAL_PUBLISH:",
        '            new_version = "0.0.1"',
        "            write_version_cache(new_version)",
        "            return new_version",
        '        raise RuntimeError("Unable to determine version.")',
        "",
        "    new_version = calculate_next_version(latest_version)",
        "    write_version_cache(new_version)",
        "    return new_version",
        "",
        "",
        "setup(version=dynamic_version())",
    ]
    return "\n".join(lines) + "\n"


def _build_generated_cli(module_name: str) -> str:
    """Build src/<module>/cli.py content for scaffolded project."""

    return (
        f'"""CLI module for {module_name}."""\n\n'
        "\n"
        "def main() -> None:\n"
        '    """Main entry point for the generated CLI."""\n'
        f'    print("{module_name} CLI - Hello from your scaffolded project!")\n\n'
        "\n"
        'if __name__ == "__main__":\n'
        "    main()\n"
    )


def create_project_structure(details: ProjectDetails) -> Path:
    """Create a new project scaffold from user-provided details."""

    project_root = Path.cwd() / details["name"]
    module_name = _normalize_module_name(details["name"])
    py_major, py_minor = _extract_python_major_minor(details["python_version"])

    if project_root.exists():
        raise FileExistsError(
            f"Target directory already exists: {project_root}. Choose another name."
        )

    (project_root / "scripts").mkdir(parents=True, exist_ok=False)
    (project_root / "src" / module_name).mkdir(parents=True, exist_ok=False)
    (project_root / "tests").mkdir(parents=True, exist_ok=False)

    if details["github_workflow"]:
        (project_root / ".github" / "workflows").mkdir(parents=True, exist_ok=False)

    license_id, license_content = _license_metadata(
        details["license"], details["author"]
    )

    (project_root / "README.md").write_text(
        f"# {details['name']}\n\n{details['description']}\n", encoding="utf8"
    )
    (project_root / "MANIFEST.in").write_text(
        "# Include documentation files in source distribution\n"
        "include LICENSE\n"
        "include README.md\n"
        "include pyproject.toml\n"
        "include requirements-dev.txt\n\n"
        "# Include scripts\n"
        "include scripts/setup.py\n\n"
        "# Include type stubs marker\n"
        f"include src/{module_name}/py.typed\n\n"
        "# Exclude development/test artifacts\n"
        "prune .github\n"
        "global-exclude __pycache__\n"
        "global-exclude *.py[cod]\n"
        "global-exclude *.egg-info\n",
        encoding="utf8",
    )
    (project_root / ".gitignore").write_text(
        "*~\n.fuse_hidden*\n.directory\n.Trash-*\n.nfs*\n.DS_Store\nThumbs.db\n\n"
        "__pycache__/\n*.py[cod]\n*$py.class\n.mypy_cache/\n.pytest_cache/\n"
        ".ruff_cache/\n.pyre/\n.pytype/\n.hypothesis/\n\n"
        ".venv/\nvenv/\nenv/\n\n"
        "build/\ndist/\n*.egg-info/\n.eggs/\n*.egg\n*.whl\nMANIFEST\n\n"
        ".coverage\n.coverage.*\ncoverage.xml\nhtmlcov/\n\n"
        "*.log\n\n"
        ".vscode/*\n!.vscode/settings.json\n!.vscode/extensions.json\n"
        "!.vscode/launch.json\n!.vscode/tasks.json\n.history/\n\n"
        ".env\n.env.local\n",
        encoding="utf8",
    )
    (project_root / ".pre-commit-config.yaml").write_text(
        "repos:\n"
        "  - repo: https://github.com/astral-sh/ruff-pre-commit\n"
        "    rev: v0.3.2\n"
        "    hooks:\n"
        "      - id: ruff\n"
        '        args: [ "--fix" ]\n'
        "\n"
        "  - repo: https://github.com/pre-commit/mirrors-mypy\n"
        "    rev: v1.9.0\n"
        "    hooks:\n"
        "      - id: mypy\n"
        "        additional_dependencies: []\n"
        "\n"
        "  - repo: https://github.com/PyCQA/bandit\n"
        "    rev: 1.7.8\n"
        "    hooks:\n"
        "      - id: bandit\n"
        '        args: ["-c", "pyproject.toml"]\n'
        '        additional_dependencies: ["bandit[toml]"]\n'
        "\n"
        "  - repo: https://github.com/gitleaks/gitleaks\n"
        "    rev: v8.18.2\n"
        "    hooks:\n"
        "      - id: gitleaks\n",
        encoding="utf8",
    )
    (project_root / "requirements-dev.txt").write_text(
        "\n".join(_DEV_PACKAGES) + "\n", encoding="utf8"
    )
    (project_root / "pyproject.toml").write_text(
        _build_pyproject(details, module_name), encoding="utf8"
    )

    if license_id and license_content:
        (project_root / "LICENSE").write_text(license_content, encoding="utf8")

    if details["dynamic_versioning"]:
        (project_root / "scripts" / "setup.py").write_text(
            _build_dynamic_setup(), encoding="utf8"
        )

    (project_root / "src" / module_name / "__init__.py").write_text("", encoding="utf8")
    (project_root / "src" / module_name / "cli.py").write_text(
        _build_generated_cli(module_name), encoding="utf8"
    )
    (project_root / "src" / module_name / "py.typed").write_text("", encoding="utf8")

    (project_root / "tests" / "__init__.py").write_text("", encoding="utf8")
    (project_root / "tests" / "test_cli.py").write_text(
        '"""Tests for CLI module."""\n\n'
        f"from {module_name}.cli import main\n\n\n"
        "def test_main_runs() -> None:\n"
        "    main()\n",
        encoding="utf8",
    )
    if details["dynamic_versioning"]:
        (project_root / "tests" / "test_dynamic_versioning.py").write_text(
            '"""Unit tests for scripts.setup module."""\n\n'
            "def test_placeholder() -> None:\n"
            "    assert True\n",
            encoding="utf8",
        )

    if details["github_workflow"]:
        (project_root / ".github" / "workflows" / "ci.yml").write_text(
            "name: CI Pipeline\n\n"
            "on:\n"
            "  push:\n"
            '    branches: ["main"]\n'
            "  pull_request:\n"
            '    branches: ["main"]\n\n'
            "jobs:\n"
            "  qa:\n"
            "    runs-on: ubuntu-latest\n"
            "\n"
            "    steps:\n"
            "      - name: Checkout repository\n"
            "        uses: actions/checkout@v4\n"
            "\n"
            "      - name: Set up Python\n"
            "        uses: actions/setup-python@v5\n"
            "        with:\n"
            f'          python-version: "{py_major}.{py_minor}"\n'
            '          cache: "pip"\n'
            "\n"
            "      - name: Install dependencies\n"
            "        run: |\n"
            "          python -m pip install --upgrade pip\n"
            "          pip install -e .[dev]\n"
            "\n"
            "      - name: Run linting check (Ruff)\n"
            "        run: ruff check .\n"
            "\n"
            "      - name: Run type checking (Mypy)\n"
            "        run: mypy .\n"
            "\n"
            "      - name: Run security scan (Bandit)\n"
            "        run: bandit -c pyproject.toml -r .\n"
            "\n"
            "      - name: Run dependency vulnerability scan (pip-audit)\n"
            "        run: pip-audit\n"
            "\n"
            "      - name: Run tests with coverage (Pytest)\n"
            f"        run: pytest --cov=src/{module_name} --cov-report=term-missing\n",
            encoding="utf8",
        )

    return project_root


def _venv_python_path(project_root: Path) -> Path:
    """Resolve the Python executable path inside .venv for current OS."""

    if os_name == "nt":
        return project_root / ".venv" / "Scripts" / "python.exe"
    return project_root / ".venv" / "bin" / "python"


def _python_executable() -> str:
    """Return active Python executable path."""

    return sys.executable


def _run_checked(command: list[str], cwd: Path) -> None:
    """Run a trusted command list with check=True."""

    subprocess.run(command, cwd=cwd, check=True)  # nosec B603


def bootstrap_virtual_environment(details: ProjectDetails, project_root: Path) -> None:
    """Create and optionally initialize virtual environment for generated project."""

    if not details["create_venv"]:
        return

    print("\nBootstrapping virtual environment...")
    _run_checked([_python_executable(), "-m", "venv", ".venv"], cwd=project_root)

    venv_python = _venv_python_path(project_root)
    _run_checked(
        [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
        cwd=project_root,
    )

    install_target = ".[dev]" if details["install_recommended"] else "."
    _run_checked(
        [str(venv_python), "-m", "pip", "install", "-e", install_target],
        cwd=project_root,
    )


def prompt_for_project_details() -> ProjectDetails:
    """Prompt the user for project configuration details."""

    _print_banner()
    print("Answer the questions below to generate your project.\n")

    # --- Project name (required, PEP 508 format) ---
    while True:
        name = _prompt_non_empty("Project name: ", "Project name cannot be empty.")
        if not _NAME_RE.match(name):
            print(
                "  Error: Name must start with a letter and contain only "
                "letters, digits, hyphens, underscores, or periods."
            )
        else:
            break

    # --- Description (required) ---
    description = _prompt_non_empty(
        "Project description: ", "Project description cannot be empty."
    )

    # --- Python version specifier (default >=3.12) ---
    while True:
        python_version = _normalize_python_version_spec(
            input("Minimum Python version (default >=3.12): ").strip() or ">=3.12"
        )
        if not _VERSION_RE.match(python_version):
            print(
                "  Error: Invalid version specifier. "
                "Use formats like >=3.12, <=3.11, ~=3.10, ==3.9, or plain 3.12."
            )
        else:
            break

    # --- Keywords (optional, comma-separated) ---
    keywords = input("Project keywords (comma-separated): ").strip()

    # --- Author (optional, defaults to Ertan Tunç Türk) ---
    author = (
        input(f"Project author [default {_DEFAULT_AUTHOR}]: ").strip()
        or _DEFAULT_AUTHOR
    )

    # --- Email (required format, defaults to ertantuncturk61@gmail.com) ---
    while True:
        email = (
            input(f"Project author email [default {_DEFAULT_EMAIL}]: ").strip()
            or _DEFAULT_EMAIL
        )
        if not _EMAIL_RE.match(email):
            print("  Error: Invalid email address.")
        else:
            break

    # --- License choice (1/2/3, default 1) ---
    license_choice = _prompt_choice(
        "License (1: MIT, 2: Apache, 3: None) (default 1: MIT): ",
        {"1", "2", "3"},
        "1",
    )

    # --- Dynamic versioning (Y/N, default Y) ---
    use_dynamic_versioning = _prompt_yes_no("Use built-in dynamic versioning?")

    # --- Install recommended packages (Y/N, default Y) ---
    install_recommended = _prompt_yes_no("Do you want recommended packages installed?")

    # --- Github workflow (Y/N, default Y) ---
    use_github_workflow = _prompt_yes_no("Do you want a GitHub workflow for CI?")

    # --- Create local .venv and install package (Y/N, default Y) ---
    create_venv = _prompt_yes_no("Create .venv and install the generated project now?")

    print("\nConfiguration summary")
    print("-" * 60)
    print(f"Name: {name}")
    print(f"Description: {description}")
    print(f"Minimum Python: {python_version}")
    print(f"Keywords: {keywords or '(none)'}")
    print(f"Author: {author}")
    print(f"Email: {email}")
    print(f"License option: {license_choice}")
    print(f"Dynamic versioning: {use_dynamic_versioning}")
    print(f"Recommended packages: {install_recommended}")
    print(f"GitHub workflow: {use_github_workflow}")
    print(f"Bootstrap .venv: {create_venv}")
    print("-" * 60)

    if not _prompt_yes_no("Create project with these settings?", default_yes=True):
        raise SystemExit("Aborted by user.")

    return {
        "name": name,
        "description": description,
        "python_version": python_version,
        "keywords": keywords,
        "author": author,
        "email": email,
        "license": license_choice,
        "dynamic_versioning": use_dynamic_versioning,
        "install_recommended": install_recommended,
        "github_workflow": use_github_workflow,
        "create_venv": create_venv,
    }


def main() -> None:
    """Main entry point for pyforge CLI."""
    try:
        details = prompt_for_project_details()
        project_root = create_project_structure(details)
        bootstrap_virtual_environment(details, project_root)
        print(f"\nProject scaffold created at: {project_root}")
        print("Next steps:")
        print(f"  cd {project_root.name}")
        if details["create_venv"]:
            print("  Linux/macOS: source .venv/bin/activate")
            print(r"  Windows: .venv\Scripts\activate")
        else:
            print("  python -m pip install -e .[dev]")
    except FileExistsError as exc:
        print(f"Error: {exc}")
    except subprocess.CalledProcessError as exc:
        print(f"Error while setting up virtual environment: {exc}")


if __name__ == "__main__":
    main()
