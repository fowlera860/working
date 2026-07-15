"""
Master Yarn Production Cycle Planner updater
Starter pipeline for the Yarn Production Cycle Planner project.
"""

import json
import sys
import importlib
import struct
from pathlib import Path
from datetime import datetime
from typing import Optional, TextIO


is_frozen = getattr(sys, "frozen", False)
if is_frozen:
    base_path = Path(sys._MEIPASS)
else:
    base_path = Path(__file__).parent

if str(base_path) not in sys.path:
    sys.path.insert(0, str(base_path))

from utils import load_config, ensure_export_folder


class TeeStream:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
        return len(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()

    def isatty(self):
        return any(getattr(stream, "isatty", lambda: False)() for stream in self.streams)


def start_export_log() -> tuple[Optional[TextIO], Optional[TextIO], Optional[TextIO]]:
    try:
        config = load_config()
        export_folder = Path(config["paths"]["export_folder"])
        if not ensure_export_folder(export_folder):
            print("Warning: Unable to create export folder for log file.")
            return None, None, None

        log_path = export_folder / "UpdateYarnProductionCyclePlanner.log"
        log_file = open(log_path, "w", encoding="utf-8")

        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = TeeStream(original_stdout, log_file)
        sys.stderr = TeeStream(original_stderr, log_file)

        print(f"Logging to: {log_path}")
        return log_file, original_stdout, original_stderr
    except Exception as e:
        print(f"Warning: Unable to start run log: {e}")
        return None, None, None


def stop_export_log(
    log_file: Optional[TextIO],
    original_stdout: Optional[TextIO],
    original_stderr: Optional[TextIO],
) -> None:
    if original_stdout is not None:
        sys.stdout = original_stdout
    if original_stderr is not None:
        sys.stderr = original_stderr
    if log_file is not None:
        log_file.close()


def print_header(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def load_previous_last_update(status_path: Path) -> str:
    if not status_path.exists():
        return None

    try:
        with open(status_path, "r") as file:
            data = json.load(file)
        return data.get("lastUpdate")
    except Exception:
        return None


def write_status(status: str, mark_complete: bool = False) -> None:
    try:
        config = load_config()
        export_folder = Path(config["paths"]["export_folder"])

        if not ensure_export_folder(export_folder):
            print("Warning: Unable to create export folder for status file.")
            return

        status_path = export_folder / "yarn_production_update_status.json"
        last_update = load_previous_last_update(status_path)
        if mark_complete:
            last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        payload = {
            "status": status,
            "lastUpdate": last_update,
        }

        with open(status_path, "w") as file:
            json.dump(payload, file, indent=2)
    except Exception as error:
        print(f"Warning: Unable to write status file: {error}")


def validate_config(config: dict) -> list[str]:
    errors = []

    required_paths = [
        "export_folder",
        "yarn_alts_xlsx",
        "open_yarn_production_csv",
        "yarn_order_recommendation_csv",
    ]
    for path_key in required_paths:
        if path_key not in config.get("paths", {}):
            errors.append(f"Missing paths.{path_key}")

    dbs = config.get("databases", {})
    if "CAMS" not in dbs:
        errors.append("Missing databases.CAMS")
    if "CAMSY" not in dbs:
        errors.append("Missing databases.CAMSY")

    return errors


def validate_runtime_architecture(config: dict) -> list[str]:
    """
    Enforce Python bitness compatibility with configured ODBC drivers.
    If CAMSY uses a 32-bit driver, Python runtime must also be 32-bit.
    """
    errors = []
    camsy_cfg = config.get("databases", {}).get("CAMSY", {})
    conn_str = str(camsy_cfg.get("connection_string", "")).lower()
    driver_name = str(camsy_cfg.get("driver", "")).lower()

    requires_32_bit = "32-bit" in conn_str or "32-bit" in driver_name
    python_bits = struct.calcsize("P") * 8

    if requires_32_bit and python_bits != 32:
        errors.append(
            "CAMSY is configured with a 32-bit ODBC driver, but this runtime is "
            f"{python_bits}-bit. Use 32-bit Python / 32-bit EXE."
        )

    return errors


def run_converter(module_name: str, label: str) -> bool:
    print_header(label)
    try:
        module = importlib.import_module(module_name)
        importlib.reload(module)
        module.main()
        print(f"✓ {label} completed successfully")
        return True
    except ModuleNotFoundError:
        print(f"⚠ {label} skipped: module not found ({module_name}.py)")
        return True
    except Exception as error:
        print(f"✗ {label} failed: {error}")
        write_status(f"error: {label}: {error}")
        return False


def main() -> None:
    start_time = datetime.now()
    log_file, original_stdout, original_stderr = start_export_log()

    try:
        write_status("updating Yarn Production Cycle Planner")

        print_header("Yarn Production Cycle Planner Update")
        print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        config = load_config()
        config_errors = validate_config(config)
        runtime_errors = validate_runtime_architecture(config)
        if config_errors:
            print_header("Configuration Errors")
            for error in config_errors:
                print(f"  - {error}")
            write_status("error: invalid configuration")
            sys.exit(1)

        if runtime_errors:
            print_header("Runtime Architecture Error")
            for error in runtime_errors:
                print(f"  - {error}")
            write_status("error: runtime architecture mismatch")
            sys.exit(1)

        open_yarn_prod_csv = config.get("paths", {}).get("open_yarn_production_csv", "NOT SET")
        yarn_order_rec_csv = config.get("paths", {}).get("yarn_order_recommendation_csv", "NOT SET")
        print(f"\nOpen Yarn Production file:      {open_yarn_prod_csv}")
        print(f"Yarn Order Recommendation file: {yarn_order_rec_csv}")

        # Add converters here as they are developed
        converters = [
            ("open_yarn_production_converter",           "Open Yarn Production"),
            ("yarn_order_recommendation_converter",       "Yarn Order Recommendations"),
            ("yarn_production_prebuild_sku_converter",    "Yarn Production Prebuild SKU"),
            ("yarn_production_prebuild_group_converter",  "Yarn Production Prebuild Group"),
        ]

        results = {}
        for module_name, label in converters:
            write_status(f"updating {label}")
            results[label] = run_converter(module_name, label)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print_header("Summary")
        print(f"Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {duration:.2f} seconds\n")

        if results:
            for label, success in results.items():
                status = "✓ SUCCESS" if success else "✗ FAILED"
                print(f"  {status}: {label}")

            if not all(results.values()):
                print("\n⚠ One or more Yarn Production Cycle Planner steps failed")
                sys.exit(1)
        else:
            print("  (no converters registered)")

        write_status("update complete", mark_complete=True)
        print("\n✓ Yarn Production Cycle Planner update completed successfully!")
        sys.exit(0)
    finally:
        stop_export_log(log_file, original_stdout, original_stderr)


if __name__ == "__main__":
    main()
