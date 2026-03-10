"""Unit tests for scripts.setup module."""

import builtins
import json
from collections.abc import Callable
from email.message import Message
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock
from urllib.error import HTTPError, URLError

import pytest
from pytest import MonkeyPatch


def _import_setup_module() -> dict[str, Any]:
    """Import setup.py functions without executing setup() call.

    Returns:
        dict[str, Any]: Namespace containing setup module functions.
    """
    project_root = Path(__file__).resolve().parents[1]
    setup_path = project_root / "scripts" / "setup.py"
    source = setup_path.read_text(encoding="utf8")

    # Filter out setuptools import and setup() call
    lines = [
        line
        for line in source.splitlines()
        if not line.strip().startswith("setup(")
        and "from setuptools import" not in line
    ]

    def mock_setup(**kwargs: Any) -> None:
        pass

    # Provide necessary items in namespace (mock setuptools.setup)
    namespace: dict[str, Any] = {
        "__builtins__": builtins.__dict__,
        "setup": mock_setup,
    }
    exec("\n".join(lines), namespace)  # noqa: S102
    return namespace


class TestReadProjectName:
    """Tests for read_project_name()."""

    def test_reads_valid_project_name(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Test reading valid project name from pyproject.toml."""
        tmp_path.joinpath("pyproject.toml").write_text(
            'name = "my-project"', encoding="utf8"
        )
        monkeypatch.chdir(tmp_path)

        ns = _import_setup_module()
        read_name = cast(Callable[[], str], ns["read_project_name"])
        assert read_name() == "my-project"

    def test_raises_when_file_missing(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Test FileNotFoundError when pyproject.toml is missing."""
        monkeypatch.chdir(tmp_path)

        ns = _import_setup_module()
        read_name = cast(Callable[[], str], ns["read_project_name"])
        with pytest.raises(FileNotFoundError, match="pyproject.toml file not found"):
            read_name()

    def test_raises_when_name_not_found(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Test FileNotFoundError when name field is missing."""
        tmp_path.joinpath("pyproject.toml").write_text(
            '[project]\nversion = "1.0.0"', encoding="utf8"
        )
        monkeypatch.chdir(tmp_path)

        ns = _import_setup_module()
        read_name = cast(Callable[[], str], ns["read_project_name"])
        with pytest.raises(FileNotFoundError, match="Project name not found"):
            read_name()


class TestFetchLatestVersion:
    """Tests for fetch_latest_version()."""

    def test_fetches_version_successfully(self) -> None:
        """Test successful fetch of version from PyPI."""
        ns = _import_setup_module()

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(
            {"info": {"version": "1.2.3"}}
        ).encode("utf8")

        # Explicitly return the mock itself when entering the context manager
        mock_response.__enter__.return_value = mock_response

        def mock_urlopen(*args: Any, **kwargs: Any) -> MagicMock:
            return mock_response

        ns["urlopen"] = mock_urlopen
        fetch = cast(Callable[[str], str | None], ns["fetch_latest_version"])
        assert fetch("test-package") == "1.2.3"

    def test_returns_none_on_404(self) -> None:
        """Test that None is returned for package not found."""
        ns = _import_setup_module()

        def mock_urlopen_404(*args: Any, **kwargs: Any) -> MagicMock:
            raise HTTPError("http://test", 404, "Not Found", Message(), None)

        ns["urlopen"] = mock_urlopen_404
        fetch = cast(Callable[[str], str | None], ns["fetch_latest_version"])
        assert fetch("missing-package") is None

    def test_returns_none_on_network_error(self) -> None:
        """Test that None is returned on network error."""
        ns = _import_setup_module()

        def mock_urlopen_error(*args: Any, **kwargs: Any) -> MagicMock:
            raise URLError("Connection failed")

        ns["urlopen"] = mock_urlopen_error
        fetch = cast(Callable[[str], str | None], ns["fetch_latest_version"])
        assert fetch("test-package") is None


class TestCalculateNextVersion:
    """Tests for calculate_next_version()."""

    def test_increments_patch_version(self) -> None:
        """Test patch version increments."""
        ns = _import_setup_module()
        calc = cast(Callable[[str], str], ns["calculate_next_version"])

        assert calc("1.0.0") == "1.0.1"
        assert calc("2.3.15") == "2.3.16"

    def test_rolls_over_patch_to_minor(self) -> None:
        """Test patch rollover at 20."""
        ns = _import_setup_module()
        calc = cast(Callable[[str], str], ns["calculate_next_version"])

        assert calc("1.0.20") == "1.1.0"

    def test_rolls_over_minor_to_major(self) -> None:
        """Test minor rollover at 10."""
        ns = _import_setup_module()
        calc = cast(Callable[[str], str], ns["calculate_next_version"])

        assert calc("1.10.20") == "2.0.0"


class TestReadInternalCacheVersion:
    """Tests for read_internal_cache_version()."""

    def test_reads_cached_version(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Test reading version from cache file."""
        tmp_path.joinpath(".version_cache").write_text("0.5.2", encoding="utf8")
        monkeypatch.chdir(tmp_path)

        ns = _import_setup_module()
        read_cache = cast(Callable[[], str | None], ns["read_internal_cache_version"])
        assert read_cache() == "0.5.2"

    def test_returns_none_when_cache_missing(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Test None is returned when cache file doesn't exist."""
        monkeypatch.chdir(tmp_path)

        ns = _import_setup_module()
        read_cache = cast(Callable[[], str | None], ns["read_internal_cache_version"])
        assert read_cache() is None


class TestWriteVersionCache:
    """Tests for write_version_cache()."""

    def test_writes_version_to_cache(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Test writing version string to cache file."""
        monkeypatch.chdir(tmp_path)

        ns = _import_setup_module()
        write_cache = cast(Callable[[str], None], ns["write_version_cache"])
        write_cache("1.5.0")

        assert tmp_path.joinpath(".version_cache").read_text(encoding="utf8") == "1.5.0"


class TestDynamicVersion:
    """Tests for dynamic_version()."""

    def test_bumps_cached_version_when_pypi_unavailable(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Test version bump from cache when PyPI is unavailable."""
        tmp_path.joinpath("pyproject.toml").write_text(
            'name = "test-pkg"', encoding="utf8"
        )
        tmp_path.joinpath(".version_cache").write_text("0.0.5", encoding="utf8")
        monkeypatch.chdir(tmp_path)

        ns = _import_setup_module()

        def mock_fetch_none(name: str) -> str | None:
            return None

        ns["fetch_latest_version"] = mock_fetch_none

        dynamic = cast(Callable[[], str], ns["dynamic_version"])
        version = dynamic()

        assert version == "0.0.6"
        assert tmp_path.joinpath(".version_cache").read_text(encoding="utf8") == "0.0.6"

    def test_bumps_pypi_version(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test version bump from PyPI latest version."""
        tmp_path.joinpath("pyproject.toml").write_text(
            'name = "test-pkg"', encoding="utf8"
        )
        monkeypatch.chdir(tmp_path)

        ns = _import_setup_module()

        def mock_fetch_version(name: str) -> str | None:
            return "2.1.8"

        ns["fetch_latest_version"] = mock_fetch_version

        dynamic = cast(Callable[[], str], ns["dynamic_version"])
        version = dynamic()

        assert version == "2.1.9"
        assert tmp_path.joinpath(".version_cache").read_text(encoding="utf8") == "2.1.9"
