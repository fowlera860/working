let
    Source = Excel.CurrentWorkbook(){[Name="Input"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Style", type text}, {"Name", type any}, {"Notes", type text}})
in
    #"Changed Type"