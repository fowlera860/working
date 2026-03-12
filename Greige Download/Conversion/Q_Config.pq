let
    // Read CONFIG table (should be a named Excel Table called "Config")
    Source = Excel.CurrentWorkbook(){[Name="Config"]}[Content],
    
    // Function to get a parameter value
    GetParameter = (paramName as text) => 
        let
            Filtered = Table.SelectRows(Source, each [Parameter] = paramName),
            Value = if Table.RowCount(Filtered) > 0 then Filtered{0}[Value] else null
        in
            Value,
    
    // Parse specific parameters with type conversion
    Config = [
        Min_Roll_Length_FT = Number.From(GetParameter("Min_Roll_Length_FT"))
    ]
in
    Config
