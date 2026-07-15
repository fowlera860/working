let
    FullMonthSource = #"Full_Month_List",
    JdeSource = #"JDE Enrollment",

    EnsureColumns = (tbl as table, cols as list) as table =>
        List.Accumulate(
            cols,
            tbl,
            (state as table, col as text) =>
                if List.Contains(Table.ColumnNames(state), col) then
                    state
                else
                    Table.AddColumn(state, col, each null)
        ),

    FullMonthRequired = {"Client Subscriber ID", "Billing Tier", "Rate"},
    JdeRequired = {"Employee Tax ID", "address Number_1", "Plan ID", "Explanation Alpha Name", "Add Opt", "Description"},

    FullMonthPrepared = Table.SelectColumns(EnsureColumns(FullMonthSource, FullMonthRequired), FullMonthRequired),
    JdePrepared = Table.SelectColumns(EnsureColumns(JdeSource, JdeRequired), JdeRequired),

    FullMonthRenamed = Table.RenameColumns(
        FullMonthPrepared,
        {
            {"Client Subscriber ID", "ID"},
            {"Billing Tier", "Full_Month_Billing_Tier"},
            {"Rate", "Full_Month_Rate"}
        }
    ),

    JdeRenamed = Table.RenameColumns(
        JdePrepared,
        {
            {"Employee Tax ID", "ID"},
            {"address Number_1", "JDE_address_Number_1"},
            {"Plan ID", "JDE_Plan_ID"},
            {"Explanation Alpha Name", "JDE_Explanation_Alpha_Name"},
            {"Add Opt", "JDE_Add_Opt"},
            {"Description", "JDE_Description"}
        }
    ),

    ComparisonNested = Table.NestedJoin(FullMonthRenamed, {"ID"}, JdeRenamed, {"ID"}, "JDE", JoinKind.FullOuter),
    Comparison = Table.ExpandTableColumn(
        ComparisonNested,
        "JDE",
        {
            "JDE_address_Number_1",
            "JDE_Plan_ID",
            "JDE_Explanation_Alpha_Name",
            "JDE_Add_Opt",
            "JDE_Description"
        },
        {
            "JDE_address_Number_1",
            "JDE_Plan_ID",
            "JDE_Explanation_Alpha_Name",
            "JDE_Add_Opt",
            "JDE_Description"
        }
    ),

    Final = Table.ReorderColumns(
        Comparison,
        {
            "ID",
            "Full_Month_Billing_Tier",
            "Full_Month_Rate",
            "JDE_address_Number_1",
            "JDE_Plan_ID",
            "JDE_Explanation_Alpha_Name",
            "JDE_Add_Opt",
            "JDE_Description"
        }
    )
in
    Final
