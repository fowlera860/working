let
    currentYear = Date.Year(DateTime.LocalNow()),
    StartDate = #date(currentYear - 10, 1, 1),
    EndDate = #date(currentYear + 15, 12, 31),
    DayList = List.Dates(StartDate, Duration.Days(EndDate-StartDate)+1, #duration(1,0,0,0)),
    #"Converted to Table" = Table.FromList(DayList, Splitter.SplitByNothing(), {"Date"}, null, ExtraValues.Error),
    #"Added Columns" = Table.TransformColumns(#"Converted to Table", {{"Date", each _, type date}}),
    #"Added Year" = Table.AddColumn(#"Added Columns", "Calendar Year", each Date.Year([Date]), Int64.Type),
    #"Added Cal Month" = Table.AddColumn(#"Added Year", "Calendar Month", each Date.Month([Date]), Int64.Type),
    #"Added Cal Month Name" = Table.AddColumn(#"Added Cal Month", "Calendar Month Name", each Date.ToText([Date], "MMMM"), type text),
    
    // Calculate 5-4-4 Week Numbers (Sunday-Saturday weeks)
    #"Added Week Start Date" = Table.AddColumn(#"Added Cal Month Name", "Week Start Date", each
        let
            // Find the Sunday of the current week
            dayOfWeek = Date.DayOfWeek([Date], Day.Sunday), // 0=Sunday, 1=Monday, etc.
            weekStartDate = Date.AddDays([Date], -dayOfWeek)
        in
            weekStartDate, type date),
    
    #"Added Year Start Week" = Table.AddColumn(#"Added Week Start Date", "Year Start Week", each
        let
            wsDate = [Week Start Date],
            wsYear = Date.Year(wsDate),
            // Check if this week belongs to the next fiscal year
            nextJan1 = #date(wsYear + 1, 1, 1),
            nextYearStart = Date.AddDays(nextJan1, -Date.DayOfWeek(nextJan1, Day.Sunday)),
            fiscalYear = if wsDate >= nextYearStart then wsYear + 1 else wsYear,
            // Find the Sunday on/before Jan 1 of the fiscal year
            fiscalJan1 = #date(fiscalYear, 1, 1),
            yearStartWeek = Date.AddDays(fiscalJan1, -Date.DayOfWeek(fiscalJan1, Day.Sunday))
        in
            yearStartWeek, type date),
    
    #"Added Week of Year" = Table.AddColumn(#"Added Year Start Week", "Week Number", each
        let
            weeksDiff = Duration.Days([Week Start Date] - [Year Start Week]) / 7
        in
            weeksDiff + 1, Int64.Type),
    
    #"Added Week Year" = Table.AddColumn(#"Added Week of Year", "Year", each
        let
            wsDate = [Week Start Date],
            wsYear = Date.Year(wsDate),
            nextJan1 = #date(wsYear + 1, 1, 1),
            nextYearStart = Date.AddDays(nextJan1, -Date.DayOfWeek(nextJan1, Day.Sunday)),
            fiscalYear = if wsDate >= nextYearStart then wsYear + 1 else wsYear
        in
            fiscalYear, Int64.Type),
    
    // Add Month based on Week of Year (544 schedule)
    #"Added Month" = Table.AddColumn(#"Added Week Year", "Month", each
        let
            weekOfYear = [Week Number]
        in
            if weekOfYear <= 5 then 1      // Weeks 1-5 = January (5 weeks)
            else if weekOfYear <= 9 then 2   // Weeks 6-9 = February (4 weeks)
            else if weekOfYear <= 13 then 3  // Weeks 10-13 = March (4 weeks)
            else if weekOfYear <= 18 then 4  // Weeks 14-18 = April (5 weeks)
            else if weekOfYear <= 22 then 5  // Weeks 19-22 = May (4 weeks)
            else if weekOfYear <= 26 then 6  // Weeks 23-26 = June (4 weeks)
            else if weekOfYear <= 31 then 7  // Weeks 27-31 = July (5 weeks)
            else if weekOfYear <= 35 then 8  // Weeks 32-35 = August (4 weeks)
            else if weekOfYear <= 39 then 9  // Weeks 36-39 = September (4 weeks)
            else if weekOfYear <= 44 then 10 // Weeks 40-44 = October (5 weeks)
            else if weekOfYear <= 48 then 11 // Weeks 45-48 = November (4 weeks)
            else 12,                         // Weeks 49-52/53 = December (4/5 weeks)
        Int64.Type),
    
    // Add Month Name based on Month
    #"Added Month Name" = Table.AddColumn(#"Added Month", "Month Name", each
        let
            monthNum = [Month],
            monthNames = {"January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"}
        in
            monthNames{monthNum - 1},
        type text),
    
    // Calculate Week of Month - derived directly from Week Number and known 5-4-4 month start weeks
    #"Added Week of Month" = Table.AddColumn(#"Added Month Name", "Week of Month", each
        let
            monthFirstWeek =
                if [Month] = 1 then 1
                else if [Month] = 2 then 6
                else if [Month] = 3 then 10
                else if [Month] = 4 then 14
                else if [Month] = 5 then 19
                else if [Month] = 6 then 23
                else if [Month] = 7 then 27
                else if [Month] = 8 then 32
                else if [Month] = 9 then 36
                else if [Month] = 10 then 40
                else if [Month] = 11 then 45
                else 49
        in
            [#"Week Number"] - monthFirstWeek + 1, Int64.Type),
    
    // Add Quarter information for clarity
    #"Added Quarter" = Table.AddColumn(#"Added Week of Month", "Quarter", each 
        if [Month] >= 1 and [Month] <= 3 then 1
        else if [Month] >= 4 and [Month] <= 6 then 2
        else if [Month] >= 7 and [Month] <= 9 then 3
        else 4, Int64.Type),
    
    // Add Weeks in Month (integer count)
    // December gets whatever weeks remain after 48 weeks for Jan-Nov (52 or 53 week fiscal year)
    #"Added Weeks in Month" = Table.AddColumn(#"Added Quarter", "Weeks in Month", each 
        if [Month] = 1 or [Month] = 4 or [Month] = 7 or [Month] = 10 then 5
        else if [Month] = 12 then
            let
                thisYearStart = Date.AddDays(#date([Year], 1, 1), -Date.DayOfWeek(#date([Year], 1, 1), Day.Sunday)),
                nextYearStart = Date.AddDays(#date([Year] + 1, 1, 1), -Date.DayOfWeek(#date([Year] + 1, 1, 1), Day.Sunday)),
                totalWeeksInYear = Int64.From(Duration.Days(nextYearStart - thisYearStart) / 7)
            in
                totalWeeksInYear - 48
        else 4, Int64.Type),
    
    // --- New attributes ---

    // Day of Week (0=Sunday, 1=Monday, ..., 6=Saturday)
    #"Added Day of Week" = Table.AddColumn(#"Added Weeks in Month", "Day of Week", each 
        Date.DayOfWeek([Date], Day.Sunday), Int64.Type),

    // Day of Week Name (e.g., "Monday")
    #"Added Day of Week Name" = Table.AddColumn(#"Added Day of Week", "Day of Week Name", each 
        Date.ToText([Date], "dddd"), type text),

    // Day of Month (1-28 or 1-35 based on fiscal 4/5-week months)
    #"Added Day of Month" = Table.AddColumn(#"Added Day of Week Name", "Day of Month", each 
        ([Week of Month] - 1) * 7 + [Day of Week] + 1, Int64.Type),

    // Day of Year (1-364 on 52-week years, 1-371 on 53-week years)
    #"Added Day of Year" = Table.AddColumn(#"Added Day of Month", "Day of Year", each 
        ([#"Week Number"] - 1) * 7 + [Day of Week] + 1, Int64.Type),

    // Week End Date (Saturday of the current week)
    #"Added Week End Date" = Table.AddColumn(#"Added Day of Year", "Week End Date", each 
        Date.AddDays([Week Start Date], 6), type date),

    // Month-Year label (e.g., "Jan 2026")
    #"Added Month-Year" = Table.AddColumn(#"Added Week End Date", "Month-Year", each 
        Text.Start([Month Name], 3) & " " & Number.ToText([Year]), type text),

    // Year-Month Key (e.g., 202601)
    #"Added Year-Month Key" = Table.AddColumn(#"Added Month-Year", "Year-Month Key", each 
        [Year] * 100 + [Month], Int64.Type),

    // Week-Year label (e.g., "2026 Week 1")
    #"Added Week-Year" = Table.AddColumn(#"Added Year-Month Key", "Week-Year", each 
        Number.ToText([Year]) & " Week " & Number.ToText([#"Week Number"]), type text),

    // Week-Year Key (e.g., "2026W01")
    #"Added Week-Year Key" = Table.AddColumn(#"Added Week-Year", "Week-Year Key", each 
        Number.ToText([Year]) & "W" & Text.PadStart(Number.ToText([#"Week Number"]), 2, "0"), type text),

    // Month Start Date (first day of the fiscal month)
    #"Added Month Start Date" = Table.AddColumn(#"Added Week-Year Key", "Month Start Date", each 
        let
            monthFirstWeek =
                if [Month] = 1 then 1
                else if [Month] = 2 then 6
                else if [Month] = 3 then 10
                else if [Month] = 4 then 14
                else if [Month] = 5 then 19
                else if [Month] = 6 then 23
                else if [Month] = 7 then 27
                else if [Month] = 8 then 32
                else if [Month] = 9 then 36
                else if [Month] = 10 then 40
                else if [Month] = 11 then 45
                else 49
        in
            Date.AddDays([Year Start Week], (monthFirstWeek - 1) * 7), type date),

    // Month End Date (last day of the fiscal month)
    #"Added Month End Date" = Table.AddColumn(#"Added Month Start Date", "Month End Date", each 
        Date.AddDays([Month Start Date], [Weeks in Month] * 7 - 1), type date),

    // Quarter Start Date (first day of the fiscal quarter)
    #"Added Quarter Start Date" = Table.AddColumn(#"Added Month End Date", "Quarter Start Date", each 
        let
            quarterFirstWeek = 
                if [Quarter] = 1 then 1
                else if [Quarter] = 2 then 14
                else if [Quarter] = 3 then 27
                else 40
        in
            Date.AddDays([Year Start Week], (quarterFirstWeek - 1) * 7), type date),

    // Quarter End Date (last day of the fiscal quarter; Q4 accounts for 52/53-week years)
    #"Added Quarter End Date" = Table.AddColumn(#"Added Quarter Start Date", "Quarter End Date", each 
        let
            quarterWeekCount =
                if [Quarter] = 1 then 13
                else if [Quarter] = 2 then 13
                else if [Quarter] = 3 then 13
                else
                    let
                        nextYearStart = Date.AddDays(#date([Year] + 1, 1, 1), -Date.DayOfWeek(#date([Year] + 1, 1, 1), Day.Sunday)),
                        totalWeeksInYear = Int64.From(Duration.Days(nextYearStart - [Year Start Week]) / 7)
                    in
                        totalWeeksInYear - 39
        in
            Date.AddDays([Quarter Start Date], quarterWeekCount * 7 - 1), type date),

    // Quarter-Year label (e.g., "2026 Q1")
    #"Added Quarter-Year" = Table.AddColumn(#"Added Quarter End Date", "Quarter-Year", each 
        Number.ToText([Year]) & " Q" & Number.ToText([Quarter]), type text),

    // Quarter-Year Key (e.g., "2026Q01")
    #"Added Quarter-Year Key" = Table.AddColumn(#"Added Quarter-Year", "Quarter-Year Key", each 
        Number.ToText([Year]) & "Q0" & Number.ToText([Quarter]), type text),

    // Remove helper column (Year Start Week; Week Start Date is now a kept output column)
    #"Removed Helper Columns" = Table.RemoveColumns(#"Added Quarter-Year Key", {"Year Start Week"})
in
    #"Removed Helper Columns"