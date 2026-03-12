let
    // Read INPUT table
    Source = Excel.CurrentWorkbook(){[Name="INPUT"]}[Content],
    
    // Get Style column as list
    StyleList = Source[Style],
    
    // Wrap each style in single quotes and join with commas
    QuotedStyles = List.Transform(StyleList, each "'" & Text.Trim(_) & "'"),
    StyleFilter = Text.Combine(QuotedStyles, ",")
in
    StyleFilter
