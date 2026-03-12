// CombinedOutgoing
let
    Source = Table.Combine({MillOrderRollAssignment, UnassignedMillOrders, MillOrderProductionAssignment}),
    #"Reordered Columns" = Table.ReorderColumns(Source,{"Style", "Color", "Size", "Back", "Src", "OrdNum", "OrdLine", "Qty", "UOM", "PromDt", "Product_Specs.RollSize", "LF", "ProdOrder", "AsgQty", "RsvQty", "PendingProd"}),
	#"Added WeeksOut" = Table.AddColumn(
		#"Reordered Columns",
		"WeeksOut",
		each let
			today = Date.From(DateTime.LocalNow()),
			currentWeekSunday = Date.AddDays(today, -Date.DayOfWeek(today, Day.Sunday)),
			weekDiff = Number.RoundDown(Duration.Days([PromDt] - currentWeekSunday) / 7)
		in
			if weekDiff <= 0 then 1 else weekDiff,
		Int64.Type
	)
in
    #"Added WeeksOut"
