
let
    Source = Excel.CurrentWorkbook(){[Name="Establishments"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Establishment Name*", type text}, {"Address Line 1*", type text}, {"Address Line 2", type any}, {"City*", type text}, {"State*", type text}, {"ZIP Code*", Int64.Type}, {"NAICS Code*", Int64.Type}, {"Major Activity*", type text}})
in
    #"Changed Type"