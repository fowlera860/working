// Planning_Groups
let
    Path = Directory & "Planning Groups.xlsx",
    Source = Excel.Workbook(File.Contents(Path), null, true),
    Planning_Groups_Table = Source{[Item="Planning_Groups",Kind="Table"]}[Data],
    #"Filtered Rows" = Table.SelectRows(Planning_Groups_Table, each true)
in
    #"Filtered Rows"
