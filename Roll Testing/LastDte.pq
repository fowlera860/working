let
    Source = Excel.CurrentWorkbook(),
    LastDte = Source{[Name="LastDte"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(LastDte,{{"Column1", Int64.Type}}),
    Column1 = #"Changed Type"{0}[Column1]
in
    Column1