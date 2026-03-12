// CyclePlannerPrebuild
let
    Source = Product_Specs,
    MergedBackorders = Table.NestedJoin(Source, {"Style", "Color", "Size", "Back"}, MillOrderProductionAssignment, {"Style", "Color", "Size", "Back"}, "Backorders", JoinKind.LeftOuter),
    AddedAssigned = Table.AddColumn(MergedBackorders, "AsgQty", each List.Sum([Backorders][PendingProd])),
    AddedReserves = Table.AddColumn(AddedAssigned, "ReservedQty", each List.Sum([Backorders][RsvQty])),
    MergedMillOrders = Table.NestedJoin(AddedReserves, {"Style", "Color", "Size", "Back"}, UnassignedMillOrders, {"Style", "Color", "Size", "Back"}, "UnassignedMillOrders", JoinKind.LeftOuter),
    AddedBOs =
    Table.AddColumn(
        MergedMillOrders,
        "B/O",
        each
            let
                t = Table.AddColumn(
                        [UnassignedMillOrders],
                        "Calc",
                        (r) => if r[UOM] = "RL" then [RollSize] * r[Qty] else r[Qty],
                        type number
                    )
            in
                List.Sum(t[Calc])
    ),
    MergedInventory = Table.NestedJoin(AddedBOs, {"Style", "Color", "Size", "Back"}, Inventory, {"Style", "Color", "Size", "Back"}, "Inventory", JoinKind.LeftOuter),
    AddedOnHand = Table.AddColumn(MergedInventory, "OnHand", each List.Sum([Inventory][Feet])),
    MergedForecast = Table.NestedJoin(AddedOnHand, {"Style", "Color", "Size", "Back"}, SalesForecast, {"Style", "Color", "Size", "Back"}, "SalesForecast", JoinKind.LeftOuter),
    MergedProductions = Table.NestedJoin(MergedForecast, {"Style", "Color", "Size", "Back"}, TimePhaseProductionOrders, {"Style", "Color", "Size", "Back"}, "ProductionOrders", JoinKind.LeftOuter),
    MergedShipments = Table.NestedJoin(MergedProductions, {"Style", "Color", "Size", "Back"}, TimePhaseShipments, {"Style", "Color", "Size", "Back"}, "Shipments", JoinKind.LeftOuter),
    #"Replaced Value" = Table.ReplaceValue(MergedShipments,null,0,Replacer.ReplaceValue,{"OnHand"}),
    AddedTimePhase = Table.AddColumn(#"Replaced Value", "TimePhase", each 
        fnTimePhasedInventory(
            [OnHand],
            [SalesForecast],
            [ProductionOrders],
            [Shipments]
        )
    ),
    ExpandedTimePhase = Table.ExpandRecordColumn(AddedTimePhase, "TimePhase", {"Week 01", "Week 02", "Week 03", "Week 04", "Week 05", "Week 06", "Week 07", "Week 08", "Week 09", "Week 10", "Week 11", "Week 12"}),
    AddedAvgForecast = Table.AddColumn(ExpandedTimePhase, "Avg Forecast", each 
        let
            forecastRecord = if [SalesForecast] <> null and Table.RowCount([SalesForecast]) > 0 then [SalesForecast]{0} else null,
            fcValues = {
                try forecastRecord[#"FC W 01"] otherwise 0,
                try forecastRecord[#"FC W 02"] otherwise 0,
                try forecastRecord[#"FC W 03"] otherwise 0,
                try forecastRecord[#"FC W 04"] otherwise 0,
                try forecastRecord[#"FC W 05"] otherwise 0,
                try forecastRecord[#"FC W 06"] otherwise 0,
                try forecastRecord[#"FC W 07"] otherwise 0,
                try forecastRecord[#"FC W 08"] otherwise 0,
                try forecastRecord[#"FC W 09"] otherwise 0,
                try forecastRecord[#"FC W 10"] otherwise 0,
                try forecastRecord[#"FC W 11"] otherwise 0,
                try forecastRecord[#"FC W 12"] otherwise 0
            },
            total = List.Sum(fcValues)
        in
            total / 13
    ),
    AddedTotalProduction = Table.AddColumn(AddedAvgForecast, "Total Production", each 
        let
            prodRecord = if [ProductionOrders] <> null and Table.RowCount([ProductionOrders]) > 0 then [ProductionOrders]{0} else null,
            pdValues = {
                try prodRecord[#"PD W 01"] otherwise 0,
                try prodRecord[#"PD W 02"] otherwise 0,
                try prodRecord[#"PD W 03"] otherwise 0,
                try prodRecord[#"PD W 04"] otherwise 0,
                try prodRecord[#"PD W 05"] otherwise 0,
                try prodRecord[#"PD W 06"] otherwise 0,
                try prodRecord[#"PD W 07"] otherwise 0,
                try prodRecord[#"PD W 08"] otherwise 0,
                try prodRecord[#"PD W 09"] otherwise 0,
                try prodRecord[#"PD W 10"] otherwise 0,
                try prodRecord[#"PD W 11"] otherwise 0,
                try prodRecord[#"PD W 12"] otherwise 0,
                try prodRecord[#"PD W 13"] otherwise 0
            }
        in
            List.Sum(pdValues)
    )
in
    AddedTotalProduction
