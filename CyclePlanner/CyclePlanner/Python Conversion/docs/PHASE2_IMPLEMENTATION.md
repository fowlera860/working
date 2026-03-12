# Phase 2 Implementation - Mill Orders Converters

## Summary

Successfully implemented Phase 2 with 4 mill order converters:
1. **MillOrderProductionAssignment** - Production order assignments from PRP010/FIP010
2. **MillOrderRollAssignment** - Roll reserve assignments from FIP010/OPP010
3. **UnassignedMillOrders** - Unassigned orders from OPP010
4. **MillOrders (Combined)** - All three combined with WeeksOut calculation

## Files Created

### Individual Converters
- **mill_order_production_assignment_converter.py**
  - Queries PRP010 (production records) with SUM of reserved feet
  - Calculates PendingProd (assigned - reserved)
  - Output: `mill_orders_production_assignment.csv`

- **mill_order_roll_assignment_converter.py**
  - Queries FIP010 (inventory assigned to orders)
  - Left joins with OPP010 for promise dates
  - Output: `mill_orders_roll_assignment.csv`

- **unassigned_mill_orders_converter.py**
  - Queries OPP010 (orders) with exclude criteria
  - Filters for orders not in production assignment
  - Output: `mill_orders_unassigned.csv`

### Combined Converter
- **mill_orders_converter.py**
  - Calls all three individual converters
  - Combines results with proper column normalization
  - Adds WeeksOut calculation
  - Output: `mill_orders.csv`

### Testing
- **test_phase2_converters.py**
  - Mock data tests for combine and WeeksOut logic
  - ✓ Test complete: 7 rows combined from 3 sources
  - ✓ WeeksOut calculation verified (1-3 weeks)

## Updated Files

- **UpdateCyclePlanner.py** - Added mill_orders_converter to main script
- Now runs: Phase 1 (3 converters) + Phase 2 (1 combined converter)

## Test Results

```
Phase 2 Workflow Test
✓ Production Assignments: 3 rows
✓ Roll Assignments: 2 rows
✓ Unassigned Orders: 2 rows
✓ Combined Total: 7 rows
✓ WeeksOut calculation: 1-3 weeks
✓ CSV export/import verified
```

## Column Structure

**mill_orders.csv output:**
- Style, Color, Size, Back - Product identifiers
- Src - Source (Production Assignment / Roll Reserve / Unassigned)
- OrdNum, OrdLine - Order number and line
- Qty - Order quantity
- UOM - Unit of measure (for unassigned orders)
- PromDt - Promise date
- RsvQty, PendingProd, AsgQty, ProdOrder, LF - Source-specific fields
- WeeksOut - Calculated weeks from current week

## How to Run

**Test with mock data:**
```bash
python test_phase2_converters.py
```

**Production (requires database):**
```bash
python mill_orders_converter.py
```

**All converters (Phase 1 + 2):**
```bash
python UpdateCyclePlanner.py
```

## Architecture

Each converter follows this pattern:
1. Load Planning_Groups Excel
2. Build SQL CTE from planning groups
3. Query database
4. Add source/calculation columns
5. Export to CSV with fallback

The combined mill_orders_converter imports the individual converters and:
1. Calls each to get their data
2. Normalizes column names across sources
3. Combines with pd.concat()
4. Adds WeeksOut calculation
5. Exports combined result

## Next Steps (Phase 3)

Ready to implement:
1. **ProductionOrders** - Production order details
2. **TimePhaseProductionOrders** - Pivot to weekly format
3. **TimePhaseShipments** - Shipments pivoted to weekly

These will build on the existing patterns and use the same utilities.
