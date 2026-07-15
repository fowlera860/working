let
    Source = Excel.Workbook(File.Contents("C:\Users\arthur.fowler\Desktop\Eyemed\Eyemed Exports\The_Dixie_GroupAdairsville_2026_03_167241831_Prem_Roster.xlsx"), null, true),
    #"FULL MONTH LIST_Sheet" = Source{[Item="FULL MONTH LIST",Kind="Sheet"]}[Data],
    #"Removed Top Rows" = Table.Skip(#"FULL MONTH LIST_Sheet",10),
    #"Promoted Headers" = Table.PromoteHeaders(#"Removed Top Rows", [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{"Rate", Currency.Type}}),
    #"Removed Columns" = Table.RemoveColumns(#"Changed Type",{"Column9", "Column7", "Column3", "Column12", "Column13", "Column15", "Column16"})
in
    #"Removed Columns"