let
    Source = #"Deductions Detail",
    #"Grouped Rows" = Table.Group(Source, {"Plan ID", "Additional Option", "Explanation - Name Alpha - EXA"}, {{"Deduction", each List.Sum([Gross Pay]), type nullable number}, {"Count", each Table.RowCount(_), Int64.Type}}),
    #"Sorted Rows" = Table.Sort(#"Grouped Rows",{{"Plan ID", Order.Ascending}, {"Additional Option", Order.Ascending}}),
    GroupsIndexed = Table.AddIndexColumn(Groups, "GroupOrder", 0, 1),
    #"Merged Queries" = Table.NestedJoin(#"Sorted Rows", {"Plan ID"}, GroupsIndexed, {"PlanID"}, "Groups", JoinKind.LeftOuter),
    #"Expanded Groups" = Table.ExpandTableColumn(#"Merged Queries", "Groups", {"Group", "GroupOrder"}, {"Groups.Group", "GroupOrder"}),
    #"Reordered Columns" = Table.ReorderColumns(#"Expanded Groups",{"Groups.Group", "Plan ID", "Additional Option", "Deduction", "Count"}),
    #"Filtered Rows" = Table.SelectRows(#"Reordered Columns", each ([Groups.Group] <> null)),
    #"Reordered Columns1" = Table.ReorderColumns(#"Filtered Rows",{"Groups.Group", "Plan ID", "Additional Option", "Explanation - Name Alpha - EXA", "Deduction", "Count"}),
    #"Sorted By Group" = Table.Sort(#"Reordered Columns1", {{"GroupOrder", Order.Ascending}, {"Plan ID", Order.Ascending}}),
    #"Removed GroupOrder" = Table.RemoveColumns(#"Sorted By Group", {"GroupOrder"}),
    Cols = Table.ColumnNames(#"Removed GroupOrder"),
    #"Grouped For Subtotals" = Table.Group(#"Removed GroupOrder", {"Groups.Group"}, {{"SubTable", each _, type table}}),
    #"With Subtotals" = Table.AddColumn(#"Grouped For Subtotals", "Combined", (row) =>
        let
            grpName = row[#"Groups.Group"],
            sub = Table.TransformColumns(row[SubTable], {{"Groups.Group", each null}}),
            subtotalValues = {grpName, null, null, null, List.Sum(row[SubTable][Deduction]), List.Sum(row[SubTable][Count])},
            blankValues = List.Repeat({null}, List.Count(Cols)),
            subtotalRow = Table.FromRecords({Record.FromList(subtotalValues, Cols)}),
            blankRow = Table.FromRecords({Record.FromList(blankValues, Cols)})
        in
            Table.Combine({sub, subtotalRow, blankRow})
    ),
    Result = Table.Combine(#"With Subtotals"[Combined])
in
    Result