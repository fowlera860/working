"""
Diagnostic script to check mill order converter imports
Run this in C:\python\ to diagnose the import issue
"""

import sys
import os

print("=" * 70)
print("Mill Order Converter Import Diagnostics")
print("=" * 70)
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Python path: {sys.path[:3]}")
print()

# Test 1: Check if files exist
print("Test 1: Checking if files exist...")
files = [
    'mill_order_production_assignment_converter.py',
    'mill_order_roll_assignment_converter.py',
    'unassigned_mill_orders_converter.py'
]

for filename in files:
    exists = os.path.exists(filename)
    size = os.path.getsize(filename) if exists else 0
    print(f"  {filename}: {'EXISTS' if exists else 'MISSING'} ({size} bytes)")
print()

# Test 2: Check for syntax errors
print("Test 2: Checking for syntax errors...")
for filename in files:
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8', errors='replace') as f:
                code = f.read()
            compile(code, filename, 'exec')
            print(f"  {filename}: ✓ Syntax OK")
        except SyntaxError as e:
            print(f"  {filename}: ✗ SYNTAX ERROR at line {e.lineno}: {e.msg}")
            print(f"    Text: {e.text}")
print()

# Test 3: Try importing
print("Test 3: Attempting imports...")
try:
    import mill_order_production_assignment_converter as mo_pa
    print("  mill_order_production_assignment_converter: ✓ IMPORTED")
    print(f"    Available functions: {[x for x in dir(mo_pa) if not x.startswith('_') and callable(getattr(mo_pa, x))]}")
    print(f"    Has fetch_mill_order_production_assignment: {hasattr(mo_pa, 'fetch_mill_order_production_assignment')}")
except Exception as e:
    print(f"  mill_order_production_assignment_converter: ✗ FAILED - {e}")
print()

try:
    import mill_order_roll_assignment_converter as mo_ra
    print("  mill_order_roll_assignment_converter: ✓ IMPORTED")
    print(f"    Has fetch_mill_order_roll_assignment: {hasattr(mo_ra, 'fetch_mill_order_roll_assignment')}")
except Exception as e:
    print(f"  mill_order_roll_assignment_converter: ✗ FAILED - {e}")
print()

try:
    import unassigned_mill_orders_converter as umo
    print("  unassigned_mill_orders_converter: ✓ IMPORTED")
    print(f"    Has fetch_unassigned_mill_orders: {hasattr(umo, 'fetch_unassigned_mill_orders')}")
except Exception as e:
    print(f"  unassigned_mill_orders_converter: ✗ FAILED - {e}")
print()

# Test 4: Check for .pyc cache issues
print("Test 4: Checking for cached .pyc files...")
pycache_dir = '__pycache__'
if os.path.exists(pycache_dir):
    pyc_files = [f for f in os.listdir(pycache_dir) if f.endswith('.pyc')]
    print(f"  Found {len(pyc_files)} cached files in __pycache__")
    for pyc in pyc_files[:5]:  # Show first 5
        print(f"    - {pyc}")
    if len(pyc_files) > 5:
        print(f"    ... and {len(pyc_files) - 5} more")
    print("  Recommendation: Delete __pycache__ directory and try again")
else:
    print("  No __pycache__ directory found")
print()

print("=" * 70)
print("Diagnosis complete!")
print("=" * 70)
