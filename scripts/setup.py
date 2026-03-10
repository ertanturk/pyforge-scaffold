"""scripts.setup

Dynamic version setup for the project.

This script reads the project name from `pyproject.toml`, queries PyPI for the
latest released version of the package, and sets the version for the
current project.
"""

import json
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from setuptools import setup

IS_INITIAL_PUBLISH = True  # Set to True if this is the initial publish of the package


def read_project_name() -> str:
    """Read the project name from pyproject.toml.

    Opens the project's `pyproject.toml` and scans for a top-level
    `name = "..."` assignment, returning the name string without
    surrounding quotes.

    Returns:
        str: The project name as defined in `pyproject.toml`.

    Raises:
        FileNotFoundError: If `pyproject.toml` is not present in the
            current working directory.
        FileNotFoundError: If a `name =` line cannot be found in the file.
    """

    try:
        with open("pyproject.toml") as f:
            for line in f:
                if line.startswith("name ="):
                    return line.split("=")[1].strip().strip('"')
    except FileNotFoundError as err:
        raise FileNotFoundError(
            "pyproject.toml file not found. Please ensure it exists in the "
            "project root."
        ) from err
    raise FileNotFoundError("Project name not found in pyproject.toml")


def read_internal_cache_version() -> str | None:
    """Read the cached version from .version_cache file.

    This function attempts to read the version string from a local
    `.version_cache` file. If the file does not exist or cannot be read,
    it returns `None`.

    Returns:
        Optional[str]: The cached version string if available, otherwise
        `None`.
    """
    try:
        with open(".version_cache") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def fetch_latest_version(project_name: str) -> str | None:
    """Fetch the latest released version of a package from PyPI.

    Args:
        project_name (str): The package name to query on PyPI.

    Returns:
        Optional[str]: The latest released version string if available,
        otherwise `None` when the package is not found or a network
        error occurs.

    Notes:
        Network errors and non-200 HTTP responses are handled and result
        in `None` being returned.
    """

    url = f"https://pypi.org/pypi/{project_name}/json"
    try:
        with urlopen(url) as response:
            if response.status != 200:
                return None  # Project not found on PyPI
            data = response.read()

            json_data = json.loads(data)
            if isinstance(json_data, dict):
                json_obj = cast(dict[str, object], json_data)
                info_obj = json_obj.get("info")
                if isinstance(info_obj, dict):
                    info = cast(dict[str, object], info_obj)
                    version_obj = info.get("version")
                    if isinstance(version_obj, str):
                        return version_obj
            return None  # Unexpected JSON structure
    except HTTPError:
        return None  # Project not found on PyPI
    except URLError:
        return None  # Network error


def write_version_cache(version: str) -> None:
    """Write the given version string to the .version_cache file.

    Args:
        version (str): The version string to cache.

    This function creates or overwrites the `.version_cache` file in the
    current working directory with the provided version string.
    """
    with open(".version_cache", "w") as f:
        f.write(version)


def calculate_next_version(latest_version: str) -> str:
    """Calculate the next version string based on the latest version.

    This function takes the latest version string, splits it into its
    components (major, minor, patch), increments the patch number by 1,
    and returns the new version string.

    Args:
        latest_version (str): The latest version string in the format
            "major.minor.patch".

    Returns:
        str: The next version string with the patch number incremented.
    """
    major, minor, patch = map(int, latest_version.split("."))
    if patch < 20:
        patch += 1
    else:
        patch = 0
        if minor < 10:
            minor += 1
        else:
            minor = 0
            major += 1
    return f"{major}.{minor}.{patch}"


def dynamic_version() -> str:
    project_name = read_project_name()
    latest_version = fetch_latest_version(project_name)

    if latest_version is None:
        cached_version = read_internal_cache_version()
        if cached_version is not None:
            new_version = calculate_next_version(cached_version)
            write_version_cache(new_version)
            return new_version
        else:
            if IS_INITIAL_PUBLISH:
                new_version = "0.0.1"  # Starting version for initial publish
                write_version_cache(new_version)
                return new_version
            else:
                raise RuntimeError(
                    "Unable to determine the latest version from PyPI and no "
                    "cached version found. Please ensure the package has been "
                    "published at least once or set IS_INITIAL_PUBLISH to True."
                )
    else:
        new_version = calculate_next_version(latest_version)
        write_version_cache(new_version)
        return new_version


setup(version=dynamic_version())
