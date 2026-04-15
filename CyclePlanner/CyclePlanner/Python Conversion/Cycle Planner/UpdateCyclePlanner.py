"""
Master CyclePlanner Converter
Runs all Phase 1 converters in sequence
"""

import sys
import importlib
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, TextIO

# Get base path (works for both normal execution and PyInstaller exe)
is_frozen = getattr(sys, 'frozen', False)
if is_frozen:
    # Running as compiled exe - use PyInstaller's temp directory
    base_path = Path(sys._MEIPASS)
else:
    # Running as normal Python script
    base_path = Path(__file__).parent

# Ensure the base path is in sys.path for imports
if str(base_path) not in sys.path:
    sys.path.insert(0, str(base_path))

from utils import load_config, ensure_export_folder

# Import all converters and their dependencies
import mill_order_production_assignment_converter
import mill_order_roll_assignment_converter
import unassigned_mill_orders_converter
import inventory_converter
import product_specs_converter
import yarnxref_converter
import sales_forecast_converter
import mill_orders_converter
import production_orders_converter
import time_phase_production_orders_converter
import time_phase_shipments_converter
import cycle_planner_prebuild_converter
import cycle_planner_yarn_demand_converter
import cycle_planner_tufting_demand_converter


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


def pause_before_exit() -> None:
    """No-op: log is exported to file, console no longer needs to stay open."""
    pass


def start_export_log() -> tuple[Optional[TextIO], Optional[TextIO], Optional[TextIO]]:
    try:
        config = load_config()
        export_folder = Path(config["paths"]["export_folder"])
        if not ensure_export_folder(export_folder):
            print("Warning: Unable to create export folder for log file.")
            return None, None, None

        log_path = export_folder / "UpdateCyclePlanner.log"
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


def stop_export_log(log_file: Optional[TextIO], original_stdout: Optional[TextIO], original_stderr: Optional[TextIO]) -> None:
    if original_stdout is not None:
        sys.stdout = original_stdout
    if original_stderr is not None:
        sys.stderr = original_stderr
    if log_file is not None:
        log_file.close()

# Reload modules to ensure latest version (including sub-modules)
importlib.reload(mill_order_production_assignment_converter)
importlib.reload(mill_order_roll_assignment_converter)
importlib.reload(unassigned_mill_orders_converter)
importlib.reload(inventory_converter)
importlib.reload(product_specs_converter)
importlib.reload(yarnxref_converter)
importlib.reload(sales_forecast_converter)
importlib.reload(mill_orders_converter)
importlib.reload(production_orders_converter)
importlib.reload(time_phase_production_orders_converter)
importlib.reload(time_phase_shipments_converter)
importlib.reload(cycle_planner_prebuild_converter)
importlib.reload(cycle_planner_yarn_demand_converter)
importlib.reload(cycle_planner_tufting_demand_converter)

def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def run_converter(converter_module, name: str) -> bool:
    """Run a converter and return success status"""
    print_header(name)
    try:
        result = converter_module.main()
        if result is False:
            print(f"✗ {name} failed")
            write_status(f"error: {name}: converter reported failure")
            return False
        print(f"✓ {name} completed successfully")
        return True
    except Exception as e:
        print(f"✗ {name} failed: {e}")
        write_status(f"error: {name}: {e}")
        return False

def load_previous_last_update(status_path: Path) -> str:
    """Load lastUpdate from the status file if it exists"""
    if not status_path.exists():
        return None

    try:
        with open(status_path, "r") as f:
            data = json.load(f)
        return data.get("lastUpdate")
    except Exception:
        return None

def write_status(status: str, mark_complete: bool = False) -> None:
    """Write update status to the export folder JSON file"""
    try:
        config = load_config()
        export_folder = Path(config["paths"]["export_folder"])
        if not ensure_export_folder(export_folder):
            print("Warning: Unable to create export folder for status file.")
            return

        status_path = export_folder / "update_status.json"
        last_update = load_previous_last_update(status_path)
        if mark_complete:
            last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        payload = {
            "status": status,
            "lastUpdate": last_update
        }

        with open(status_path, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception as e:
        print(f"Warning: Unable to write status file: {e}")

def main():
    """Run all converters"""
    start_time = datetime.now()
    log_file, original_stdout, original_stderr = start_export_log()

    try:
        write_status("updating CyclePlanner")
        
        print_header("CyclePlanner Update - All Phases")
        print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        converters = [
            # Phase 1: Foundation
            (inventory_converter, "Inventory"),
            (product_specs_converter, "Product Specifications"),
            (yarnxref_converter, "Yarn XRef"),
            (sales_forecast_converter, "Sales Forecast"),
            # Phase 2: Mill Orders
            (mill_orders_converter, "Mill Orders (Combined)"),
            # Phase 3: Production Orders & Time-Phased
            (production_orders_converter, "Production Orders"),
            (time_phase_production_orders_converter, "Time-Phase Production Orders"),
            (time_phase_shipments_converter, "Time-Phase Shipments"),
            # Phase 4: Master Consolidation
            (cycle_planner_prebuild_converter, "CyclePlanner Prebuild (Master)"),
            # Phase 5: Yarn Demand
            (cycle_planner_yarn_demand_converter, "Cycle Planner Yarn Demand"),
            (cycle_planner_tufting_demand_converter, "Cycle Planner Tufting Demand")
        ]
        
        results = {}
        
        for converter_module, name in converters:
            write_status(f"updating {name}")
            success = run_converter(converter_module, name)
            results[name] = success
        
        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print_header("Summary")
        print(f"Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {duration:.2f} seconds\n")
        
        for name, success in results.items():
            status = "✓ SUCCESS" if success else "✗ FAILED"
            print(f"  {status}: {name}")
        
        # Exit with error if any failed
        if not all(results.values()):
            print("\n⚠ Some converters failed - check output above for details")
            pause_before_exit()
            sys.exit(1)
        else:
            write_status("update complete", mark_complete=True)
            print("\n✓ All converters completed successfully!")
            pause_before_exit()
            sys.exit(0)
    finally:
        stop_export_log(log_file, original_stdout, original_stderr)

if __name__ == "__main__":
    main()
