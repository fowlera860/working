let
    calendarDateTable = try Excel.CurrentWorkbook(){[Name="Calendar_Date"]}[Content] otherwise null,
    dateToTest = if calendarDateTable <> null then Date.From(calendarDateTable{0}[Column1]) else Date.From(DateTime.LocalNow()),
    // Derive fiscal properties of dateToTest for Is* comparisons
    testWeekStart = Date.AddDays(dateToTest, -Date.DayOfWeek(dateToTest, Day.Sunday)),
    testCalYear = Date.Year(testWeekStart),
    testNextYearStart = Date.AddDays(#date(testCalYear + 1, 1, 1), -Date.DayOfWeek(#date(testCalYear + 1, 1, 1), Day.Sunday)),
    testFiscalYear = if testWeekStart >= testNextYearStart then testCalYear + 1 else testCalYear,
    testYearStart = Date.AddDays(#date(testFiscalYear, 1, 1), -Date.DayOfWeek(#date(testFiscalYear, 1, 1), Day.Sunday)),
    testWeekNumber = Int64.From(Duration.Days(testWeekStart - testYearStart) / 7) + 1,
    testMonth =
        if testWeekNumber <= 5 then 1
        else if testWeekNumber <= 9 then 2
        else if testWeekNumber <= 13 then 3
        else if testWeekNumber <= 17 then 4
        else if testWeekNumber <= 22 then 5
        else if testWeekNumber <= 26 then 6
        else if testWeekNumber <= 30 then 7
        else if testWeekNumber <= 34 then 8
        else if testWeekNumber <= 39 then 9
        else if testWeekNumber <= 43 then 10
        else if testWeekNumber <= 47 then 11
        else 12,
    testQuarter =
        if testMonth <= 3 then 1
        else if testMonth <= 6 then 2
        else if testMonth <= 9 then 3
        else 4,

    currentYear = Date.Year(DateTime.LocalNow()),
    StartDate = #date(currentYear - 3, 1, 1),
    EndDate = #date(currentYear + 1, 12, 31),
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
    
    // Remove helper columns
    #"Removed Helper Columns" = Table.RemoveColumns(#"Added Weeks in Month", {"Week Start Date", "Year Start Week"}),

    // Is* columns based on dateToTest
    #"Added isDay" = Table.AddColumn(#"Removed Helper Columns", "isDay", each if [Date] = dateToTest then true else null, type logical),
    #"Added isWeek" = Table.AddColumn(#"Added isDay", "isWeek", each if [Year] = testFiscalYear and [#"Week Number"] = testWeekNumber then true else null, type logical),
    #"Added isMonth" = Table.AddColumn(#"Added isWeek", "isMonth", each if [Year] = testFiscalYear and [Month] = testMonth then true else null, type logical),
    #"Added isQuarter" = Table.AddColumn(#"Added isMonth", "isQuarter", each if [Year] = testFiscalYear and [Quarter] = testQuarter then true else null, type logical),
    #"Added isYear" = Table.AddColumn(#"Added isQuarter", "isYear", each if [Year] = testFiscalYear then true else null, type logical)
in
    #"Added isYear"