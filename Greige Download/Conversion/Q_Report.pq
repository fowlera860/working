let
    // Get style descriptions from FIP020
    StyleNames = FIP020,
    // Join with Input query to get Notes
    MergeInput = Table.NestedJoin(StyleNames, {"STYLE"}, Input, {"Style"}, "Input_Data", JoinKind.LeftOuter),
    ExpandInput = Table.ExpandTableColumn(MergeInput, "Input_Data", {"Notes", "B/O"}, {"Notes", "B/O"}),
    
    // Join with quality 1 inventory
    MergeQ1 = Table.NestedJoin(ExpandInput, {"STYLE"}, Q_Inventory_Quality1, {"G1STYL"}, "Q1_Data", JoinKind.LeftOuter),
    ExpandQ1 = Table.ExpandTableColumn(MergeQ1, "Q1_Data", {"SQYD", "ROLLS"}, {"Inv.", "Rolls"}),
    
    // Join with quality 7 inventory
    MergeQ7 = Table.NestedJoin(ExpandQ1, {"STYLE"}, Q_Inventory_Quality7, {"G1STYL"}, "Q7_Data", JoinKind.LeftOuter),
    ExpandQ7 = Table.ExpandTableColumn(MergeQ7, "Q7_Data", {"SQYD", "ROLLS"}, {"Quality 7 Inv.", "Q7_Rolls"}),
    
    // Join with other qualities inventory
    MergeOther = Table.NestedJoin(ExpandQ7, {"STYLE"}, Q_Inventory_Quality2, {"G1STYL"}, "Other_Data", JoinKind.LeftOuter),
    ExpandOther = Table.ExpandTableColumn(MergeOther, "Other_Data", {"SQYD", "ROLLS"}, {"Quality 2,3,4,6,8 & 9 Inv.", "Other_Rolls"}),
    
    // Ensure numeric columns are the right type
    FinalTypes = Table.TransformColumnTypes(ExpandOther, {
        {"Inv.", Int64.Type},
        {"Rolls", Int64.Type},
        {"Quality 7 Inv.", Int64.Type},
        {"Q7_Rolls", Int64.Type},
        {"Quality 2,3,4,6,8 & 9 Inv.", Int64.Type},
        {"Other_Rolls", Int64.Type}
    }),
    Removed = Table.RemoveColumns(FinalTypes,{"Q7_Rolls","Other_Rolls"}),
    
    // Join with Planned inventory from WIP
    MergePlanned = Table.NestedJoin(Removed, {"STYLE"}, Q_Planned, {"STYLE"}, "Planned_Data", JoinKind.LeftOuter),
    ExpandPlanned = Table.ExpandTableColumn(MergePlanned, "Planned_Data", {"PLANNED"}, {"Planned"}),
    
    // Join with Usage from sales history
    MergeUsage = Table.NestedJoin(ExpandPlanned, {"STYLE"}, Q_Usage, {"STYLE"}, "Usage_Data", JoinKind.LeftOuter),
    ExpandUsage = Table.ExpandTableColumn(MergeUsage, "Usage_Data", {"USAGE"}, {"Usage"}),
    
    // Replace nulls with 0
    ReplacedNulls = Table.ReplaceValue(ExpandUsage, null, 0, Replacer.ReplaceValue, {"Inv.", "Rolls", "Quality 7 Inv.", "Quality 2,3,4,6,8 & 9 Inv.", "Usage","B/O"}),
    // Add Wks column (Inv/Usage)
    AddWks = Table.AddColumn(ReplacedNulls, "Wks", each if [Usage] = 0
then null
else Number.Round(([#"Inv."]-[#"B/O"]*1.333) / [Usage], 2)),
    
    #"Reordered Columns" = Table.ReorderColumns(AddWks,{"STYLE", "STYLENAME", "Notes", "MCH", "MCHNAME", "Planned", "Usage", "B/O", "Inv.", "Wks", "Rolls", "Quality 2,3,4,6,8 & 9 Inv.", "Quality 7 Inv.",  "PLANT"}),
    #"Wks Sort Key" = Table.AddColumn(#"Reordered Columns", "Wks_Sort", each if [Wks] = null then 1 else 0, Int64.Type),
    #"Sorted Rows" = Table.Sort(#"Wks Sort Key",{{"Wks_Sort", Order.Ascending}, {"Wks", Order.Ascending}}),
    #"Removed Wks Sort" = Table.RemoveColumns(#"Sorted Rows",{"Wks_Sort"})

in
    #"Removed Wks Sort"