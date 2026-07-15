let
    Source = Excel.CurrentWorkbook(){[Name="Demo_Codes"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Sex ", type text}, {"EEO Min Code", Int64.Type}, {"CA Code Race Ethnicity Sex", type text}, {"EEO Min", type text}})
in
    #"Changed Type"