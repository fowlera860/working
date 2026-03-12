// TimePhaseProductionOrders
let
    Source = ProductionOrders,
    #"Removed Columns" = Table.RemoveColumns(Source,{"ProdNum", "ProdDate", "PromDate", "WH"}),

    // Keep only weeks 1-13
    Filtered = Table.SelectRows(#"Removed Columns", each [WeeksOut] >= 1 and [WeeksOut] <= 13),

   
    // Create a list of all weeks 1..13 as text "Week 01".."Week 13"
    AllWeeksText = List.Transform({1..13}, each "PD W " & Text.PadStart(Text.From(_), 2, "0")),

    // Create a table with all weeks and a dummy value
    DummyRowsTemp = Table.FromList({1..13}, Splitter.SplitByNothing(), {"WeeksOut"}),
    DummyRows = Table.AddColumn(DummyRowsTemp, "FtOrdered", each 0, Int64.Type),

    // Combine dummy rows with real data
    Combined = Table.Combine({Filtered, DummyRows}),

    // Format all WeeksOut values once as "Week 01".."Week 13"
    CombinedFormatted = Table.TransformColumns(
        Combined,
        {{"WeeksOut", each "PD W " & Text.PadStart(Text.From(_), 2, "0"), type text}}
    ),

    // Pivot the table
    #"Pivoted Column" = Table.Pivot(
        CombinedFormatted,
        List.Distinct(CombinedFormatted[WeeksOut]),
        "WeeksOut",
        "FtOrdered",
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
