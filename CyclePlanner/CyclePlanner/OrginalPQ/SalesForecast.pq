// SalesForecast
let
    Source = Excel.Workbook(File.Contents("\\tdg-sa-file\Atmore\IE\Cycle Planner\SalesForecast.xlsx"), null, true),
    SalesForecast_Table = Source{[Item="SalesForecast",Kind="Table"]}[Data],
    RemoveColumns = Table.RemoveColumns(SalesForecast_Table,{"Week 1", "Week 2", "Week 3", "Week 4", "Week 5", "Week 6", "Week 7", "Week 8", "Week 9", "Week 10", "Week 11", "Week 12", "Week 13", 
        "Week 14", "Week 15", "Week 16", "Week 17", "Week 18", "Week 19", "Week 20", "Week 21", "Week 22", "Week 23", "Week 24", "Week 25", "Week 26", "Weekly Total", "Yards/Week", "WeeksToUse", 
        "Adjustment", "AdjustedSales", "Sales/Week", "Color Sales %", "ForecastOrSales"}),
    ChangeTypes = Table.TransformColumnTypes(
        RemoveColumns,
            {
                {"Style", type text}, 
                {"Size", type text}, 
                {"Back", type text}, 
                {"Color", type text}, 
                {"FC W 01", type number}, 
                {"FC W 02", type number}, 
                {"FC W 03", type number}, 
                {"FC W 04", type number}, 
                {"FC W 05", type number}, 
                {"FC W 06", type number}, 
                {"FC W 07", type number}, 
                {"FC W 08", type number}, 
                {"FC W 09", type number}, 
                {"FC W 10", type number}, 
                {"FC W 11", type number}, 
                {"FC W 12", type number}
            }
        ),
    InnerJoinGroups = Table.NestedJoin(ChangeTypes, {"Style", "Color", "Size", "Back"}, Planning_Groups, {"Style", "Color", "Size", "Back"}, "Planning_Groups", JoinKind.Inner),
    ExpandGroups = Table.ExpandTableColumn(InnerJoinGroups, "Planning_Groups", {"PlanGroup", "ColorGroup"}, {"PlanGroup", "ColorGroup"})
in
    ExpandGroups
