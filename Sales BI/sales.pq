let
    // Connect to Analysis Services
    Source = AnalysisServices.Databases("dixiedw", [TypedMeasureColumns=true, Implementation="2.0"]),
    MarketingAnalysis = Source{[Name="MarketingAnalysis"]}[Data],
    Marketing = MarketingAnalysis{[Id="Marketing"]}[Data],
    #"Sales Only1" = Marketing{[Id="Sales Only"]}[Data],

    // Expand cube dimensions and measures
    #"Added Items" = Cube.Transform(
        #"Sales Only1",
        {
            {Cube.AddAndExpandDimensionColumn, "[Product]", {"[Product].[Product Category].[Product Category]"}, {"Product.Product Category"}},
            {Cube.AddAndExpandDimensionColumn, "[Sales Force]", {"[Sales Force].[Salesman Name].[Salesman Name]"}, {"Sales Force.Salesman Name"}},
            {Cube.AddMeasureColumn, "Net Sales", "[Measures].[Net Sales]"},
            {Cube.AddAndExpandDimensionColumn, "[Calendar]", {"[Calendar].[Day].[Day]"}, {"Calendar.Day"}}
        }
    ),

    // Convert Calendar.Day (text "YYYYMMDD") to actual date
    #"Converted to Date" = Table.TransformColumns(
        #"Added Items",
        {
            {"Calendar.Day", each Date.FromText(Text.Start(_,4) & "-" & Text.Middle(_,4,2) & "-" & Text.End(_,2)), type date}
        }
    ),

    // Optionally remove hierarchical columns if you want fully flat table
    #"Removed Hierarchy Columns" = Table.RemoveColumns(#"Converted to Date", {})
in
    #"Converted to Date"