let
    Source = OvertimeCalc,
    #"Grouped Rows" = Table.Group(Source, {"Alpha Name", "Employee Tax ID - SSN", "Company", " Tax Ident"}, {{"Exempt OT Paid", each List.Sum([#"Tax Red $ Total"]), type number}, {"Date", each List.Average([Check Date]), type nullable date}}),
    #"Reordered Columns" = Table.ReorderColumns(#"Grouped Rows",{"Alpha Name", "Employee Tax ID - SSN", "Date", "Company", " Tax Ident", "Exempt OT Paid"}),
    #"Transformed SSN" = Table.TransformColumns(#"Reordered Columns", {{"Employee Tax ID - SSN", each Text.End(_, 4), type text}}),
    #"Rounded OT Paid" = Table.TransformColumns(#"Transformed SSN", {{"Exempt OT Paid", each Number.Round(_, 2), type number}}),
    #"Average Year" = Date.Year(List.Average(List.RemoveMatchingItems(Table.Column(#"Rounded OT Paid", "Date"), {null}))),
    #"Year Only" = Table.TransformColumns(#"Rounded OT Paid", {{"Date", each #"Average Year", type number}})
in
    #"Year Only"