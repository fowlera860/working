// TimePhaseShipments
let
    Source = CombinedOutgoing,
    #"Removed Columns1" = Table.RemoveColumns(Source,{"Src", "OrdNum", "OrdLine", "UOM", "PromDt", "Product_Specs.RollSize", "LF", "ProdOrder", "AsgQty", "RsvQty", "PendingProd"}),
    // Keep only weeks 1-13
    Filtered = Table.SelectRows(#"Removed Columns1", each [WeeksOut] >= 1 and [WeeksOut] <= 13),
    #"Renamed Columns" = Table.RenameColumns(Filtered,{{"Qty", "FtToShip"}}),

   
    // Create a list of all weeks 1..13 as text "Week 01".."Week 13"
    AllWeeksText = List.Transform({1..13}, each "SH W " & Text.PadStart(Text.From(_), 2, "0")),

    // Create a table with all weeks and a dummy value
    DummyRowsTemp = Table.FromList({1..13}, Splitter.SplitByNothing(), {"WeeksOut"}),
    DummyRows = Table.AddColumn(DummyRowsTemp, "FtToShip", each 0, Int64.Type),

    // Combine dummy rows with real data
    Combined = Table.Combine({#"Renamed Columns", DummyRows}),

    // Format all WeeksOut values once as "Week 01".."Week 13"
    CombinedFormatted = Table.TransformColumns(
        Combined,
        {{"WeeksOut", each "SH W " & Text.PadStart(Text.From(_), 2, "0"), type text}}
    ),

    // Pivot the table
    #"Pivoted Column" = Table.Pivot(
        CombinedFormatted,
        List.Distinct(CombinedFormatted[WeeksOut]),
        "WeeksOut",
        "FtToShip",
        List.Sum
    ),

    // Replace any nulls with 0
    #"Replaced Nulls" = Table.ReplaceValue(
        #"Pivoted Column",
        null,
        0,
        Replacer.ReplaceValue,
        Table.ColumnNames(#"Pivoted Column")
    ),

    // Reorder columns Week 01..Week 13
    #"Reordered Columns" = Table.ReorderColumns(
        #"Replaced Nulls",
        AllWeeksText
    ),
    #"Filtered Rows" = Table.SelectRows(#"Reordered Columns", each ([Style] <> 0))
in
    #"Filtered Rows"
