"""
Shared utilities for Yarn Cycle Planner
"""

import json
import sys
from pathlib import Path


def get_base_path() -> Path:
    """
    Get the base path for the application.
    When running as a PyInstaller exe, use the exe directory.
    Otherwise use this script directory.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def load_config(config_path: str = None) -> dict:
    """Load configuration from config.json"""
    if config_path is None:
        config_path = get_base_path() / "config.json"
        if not config_path.exists():
            config_path = Path.cwd() / "config.json"

    with open(config_path, "r") as file:
        return json.load(file)


def ensure_export_folder(export_folder: Path) -> bool:
    """Ensure export folder exists"""
    try:
        export_folder.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as error:
        print(f"Error creating export folder {export_folder}: {error}")
        return False


def build_connection_string(database_config: dict) -> str:
    """
    Build an ODBC connection string from database config.
    Supports sqlserver and ibmi database types.
    """
    raw_connection_string = database_config.get("connection_string")
    if raw_connection_string:
        return raw_connection_string

    db_type = str(database_config.get("type", "")).lower()

    if db_type == "sqlserver":
        server = database_config["server"]
        database = database_config["database"]
        trusted = database_config.get("trusted_connection", "yes")
        driver = database_config.get("driver", "{ODBC Driver 17 for SQL Server}")
        return (
            f"DRIVER={driver};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"Trusted_Connection={trusted};"
        )

    if db_type == "ibmi":
        driver = database_config.get("driver", "{IBM i Access ODBC Driver}")
        system = database_config["system"]
        naming = database_config.get("naming", 0)
        database = database_config.get("database")
        default_libraries = database_config.get("default_libraries", "")
        dftpkglib = database_config.get("dftpkglib")
        languageid = database_config.get("languageid")
        pkg = database_config.get("pkg")
        qrystglmt = database_config.get("qrystglmt")

        parts = [
            f"DRIVER={driver}",
            f"SYSTEM={system}",
            f"NAM={naming}",
        ]

        if database:
            parts.append(f"DBQ={database}")
        if default_libraries:
            parts.append(f"DefaultLibraries={default_libraries}")
        if dftpkglib:
            parts.append(f"DFTPKGLIB={dftpkglib}")
        if languageid:
            parts.append(f"LANGUAGEID={languageid}")
        if pkg:
            parts.append(f"PKG={pkg}")
        if qrystglmt is not None:
            parts.append(f"QRYSTGLMT={qrystglmt}")

        return ";".join(parts) + ";"

    raise ValueError(f"Unsupported database type: {database_config.get('type')}")
