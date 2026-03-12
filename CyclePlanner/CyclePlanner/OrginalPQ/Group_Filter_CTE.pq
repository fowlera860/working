// Group_Filter_CTE
let
    Source = Planning_Groups,

    // Convert each row to a string like: ('9223','00310','1200','08','NG-Wool','00310')
    RowStrings = Table.ToRows(Source),
    QuotedRows = List.Transform(RowStrings, each "('" & Text.Combine(List.Transform(_, each Text.From(_)), "','") & "')"),

    // Combine all rows with commas and newlines
    ValuesBlock = Text.Combine(QuotedRows, ",#(lf)"),

    // Build full CTE text
    CTE = 
"WITH FilterList AS (
    SELECT *
    FROM (VALUES
" & ValuesBlock & "
    ) AS v(style, color, size, back, planningGroup, colorGroup)
)"
in
    CTE
