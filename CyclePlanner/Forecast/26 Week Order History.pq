// 26 Week Order History
let


    Today = DateTime.Date(DateTime.LocalNow()),
    YearSuffix = Text.End(Text.From(Date.Year(Today)), 2),
    WeekNum = Text.PadStart(Text.From(Date.WeekOfYear(Today)), 2, "0"),
    WeekCode = "[2.0" & YearSuffix & WeekNum & "E5]",
    MDXQuery = AnalysisServices.Database("dixiedw", "MarketingAnalysis", [Query=
        " SELECT NON EMPTY { [Measures].[Order Entry NET Syds] } ON COLUMNS, 
            NON EMPTY { ([Product].[Factory Physics SKU].[Factory Physics SKU].ALLMEMBERS *  [Product].[Inventory Color].[Inventory Color].ALLMEMBERS * [Product].[Inventory Backing].[Inventory Backing].ALLMEMBERS *
            [Calendar].[Week].[Week].ALLMEMBERS ) } DIMENSION PROPERTIES MEMBER_CAPTION ON ROWS
            FROM ( SELECT ( { [Product].[Running Line Flag].&[Running Line Style & Color] } ) ON COLUMNS 
            FROM ( SELECT ( LastPeriods(26, [Calendar].[Week].&" & WeekCode & ") ) ON COLUMNS 
            FROM ( SELECT ( { [Order Specific].[Internal-External Order].&[EXTERNAL] } ) ON COLUMNS 
            FROM ( SELECT ( { [Product].[Product Type].&[DIXIE HOME], [Product].[Product Type].&[INTERIOR LIFESTYLE], [Product].[Product Type].&[MASLAND RESIDENTIAL]} ) ON COLUMNS
            FROM ( SELECT ( { [Product].[Dye Type].&[SOLUTION DYED NYLON], [Product].[Dye Type].&[SOLUTION DYED POLY] } ) ON COLUMNS
            FROM [Marketing]))))) 
            WHERE ( [Product].[Product Type].CurrentMember, [Order Specific].[Internal-External Order].&[EXTERNAL] ) CELL PROPERTIES VALUE, BACK_COLOR, FORE_COLOR, FORMATTED_VALUE, FORMAT_STRING, FONT_NAME, FONT_SIZE, FONT_FLAGS",
        Implementation="2.0"]),
    #"Added to Column" = Table.TransformColumns(
    MDXQuery,
    {{"[Measures].[Order Entry NET Syds]", each if _ < 0 then 0 else _, type number}}
),
    // Split the [MEMBER_CAPTION] column into parts by space
    SplitWeek = Table.SplitColumn(
        #"Added to Column",
        "[Calendar].[Week].[Week].[MEMBER_CAPTION]",
        Splitter.SplitTextByDelimiter(" ", QuoteStyle.Csv),
        {"Year", "UnusedPart", "Week"}
    ),
    RemoveUnused = Table.RemoveColumns(SplitWeek,{"UnusedPart"}),
    // Calculate ISO week date to get proper week ordering across year boundaries
    AddedYearWeek = Table.AddColumn(RemoveUnused, "YearWeek", each [Year]&[Week]),
    ChangedYearWeekType = Table.TransformColumnTypes(AddedYearWeek,{{"YearWeek", Int64.Type}}),
    
    // Calculate the current week value (format: YYYYWW as integer)
    CurrentWeekValue = Date.Year(Today) * 100 + Date.WeekOfYear(Today),
    
    // Calculate week offset from current week, handling year boundaries
    AddOffsetWeekNum = Table.AddColumn(ChangedYearWeekType, "WeeksFromCurrent", each 
        let
            YearVal = Number.FromText([Year]),
            WeekVal = Number.FromText([Week]),
            YearWeekVal = YearVal * 100 + WeekVal,
            // Calculate approximate weeks difference
            YearDiff = (YearVal - Date.Year(Today)) * 52,
            WeekDiff = WeekVal - Date.WeekOfYear(Today),
            TotalWeeksDiff = YearDiff + WeekDiff
        in
            TotalWeeksDiff,
        type number),
    
    // Add WeekNum column where current week = 26, previous week = 25, etc.
    AddWeekNum = Table.AddColumn(AddOffsetWeekNum, "WeekNum", each 26 + [WeeksFromCurrent], Int64.Type),
    
    // Filter to only keep weeks 1-26 (the last 26 weeks)
    FilterWeeks = Table.SelectRows(AddWeekNum, each [WeekNum] >= 1 and [WeekNum] <= 26),
    
    RemoveColumns = Table.RemoveColumns(FilterWeeks,{"Year", "Week", "YearWeek", "WeeksFromCurrent", "[Product].[Inventory Color].[Inventory Color].[MEMBER_CAPTION]", "[Product].[Inventory Backing].[Inventory Backing].[MEMBER_CAPTION]"}),

    // Sort rows ascending by the new WeekNum
    SortByWeek = Table.Sort(RemoveColumns, {{"WeekNum", Order.Ascending}}),
    
    // Convert WeekNum to text for use as pivot column headers
    TextWeekNum = Table.TransformColumnTypes(SortByWeek, {{"WeekNum", type text}}, "en-US"),

    // Pivot the weeks into columns using WeekNum as column name
    PivotWeeks = Table.Pivot(
        TextWeekNum,
        List.Distinct(TextWeekNum[WeekNum]),
        "WeekNum",
        "[Measures].[Order Entry NET Syds]",
        List.Sum
    ),
    
    // Replace nulls in the pivoted table with 0
    ReplacedNulls = Table.ReplaceValue(
        PivotWeeks,
        null,
        0,
        Replacer.ReplaceValue,
        Table.ColumnNames(PivotWeeks)
    ),
    RenamedColumns = Table.RenameColumns(
        ReplacedNulls,
        List.Transform(
            List.Numbers(1, 26),
            each {Text.From(_), "Week " & Text.From(_)}
        )
    ),
    // Get all columns that start with "Week "
    weekColumns = List.Select(Table.ColumnNames(RenamedColumns), each Text.StartsWith(_, "Week ")),

    // Add the Weekly Total column by summing dynamically
    SumWeeks = Table.AddColumn(
        RenamedColumns,
        "Weekly Total",
        each List.Sum(Record.ToList(Record.SelectFields(_, weekColumns))),
        Number.Type
    ),
    SplitSKU = Table.SplitColumn(SumWeeks, "[Product].[Factory Physics SKU].[Factory Physics SKU].[MEMBER_CAPTION]", Splitter.SplitTextByDelimiter("-", QuoteStyle.Csv), {"Style", "Size", "Back", "Color"})
in
    SplitSKU