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
    // Prior-period anchor values
    testPriorWeekStart = Date.AddDays(testWeekStart, -7),
    testPriorMonth = if testMonth > 1 then testMonth - 1 else 12,
    testPriorMonthYear = if testMonth > 1 then testFiscalYear else testFiscalYear - 1,
    testPriorQuarter = if testQuarter > 1 then testQuarter - 1 else 4,
    testPriorQuarterYear = if testQuarter > 1 then testFiscalYear else testFiscalYear - 1,
    source = DixieCalendar,

    // Is* columns based on dateToTest
    #"Added isDay" = Table.AddColumn(source, "isDay", each if [Date] = dateToTest then true else null, type logical),
    #"Added isWeek" = Table.AddColumn(#"Added isDay", "isWeek", each if [Year] = testFiscalYear and [#"Week Number"] = testWeekNumber then true else null, type logical),
    #"Added isMonth" = Table.AddColumn(#"Added isWeek", "isMonth", each if [Year] = testFiscalYear and [Month] = testMonth then true else null, type logical),
    #"Added isQuarter" = Table.AddColumn(#"Added isMonth", "isQuarter", each if [Year] = testFiscalYear and [Quarter] = testQuarter then true else null, type logical),
    #"Added isYear" = Table.AddColumn(#"Added isQuarter", "isYear", each if [Year] = testFiscalYear then true else null, type logical),

    // Prior period flags
    #"Added is Prior Week" = Table.AddColumn(#"Added isYear", "is Prior Week", each
        if [Week Start Date] = testPriorWeekStart then true else null, type logical),

    #"Added is Prior Month" = Table.AddColumn(#"Added is Prior Week", "is Prior Month", each
        if [Year] = testPriorMonthYear and [Month] = testPriorMonth then true else null, type logical),

    #"Added is Prior Quarter" = Table.AddColumn(#"Added is Prior Month", "is Prior Quarter", each
        if [Year] = testPriorQuarterYear and [Quarter] = testPriorQuarter then true else null, type logical),

    // Year-to-date (fiscal year start through dateToTest, inclusive)
    #"Added is YTD" = Table.AddColumn(#"Added is Prior Quarter", "is YTD", each
        if [Year] = testFiscalYear and [Date] <= dateToTest then true else null, type logical),

    // Rolling 12-month flags (current period and the 51/11/3 prior periods)
    #"Added is Rolling 12 Month Week" = Table.AddColumn(#"Added is YTD", "is Rolling 12 Month Week", each
        let weekDiff = Int64.From(Duration.Days([Week Start Date] - testWeekStart) / 7)
        in if weekDiff >= -51 and weekDiff <= 0 then true else null, type logical),

    #"Added is Rolling 12 Month Month" = Table.AddColumn(#"Added is Rolling 12 Month Week", "is Rolling 12 Month Month", each
        let monthDiff = ([Year] - testFiscalYear) * 12 + ([Month] - testMonth)
        in if monthDiff >= -11 and monthDiff <= 0 then true else null, type logical),

    #"Added is Rolling 12 Month Quarter" = Table.AddColumn(#"Added is Rolling 12 Month Month", "is Rolling 12 Month Quarter", each
        let quarterDiff = ([Year] - testFiscalYear) * 4 + ([Quarter] - testQuarter)
        in if quarterDiff >= -3 and quarterDiff <= 0 then true else null, type logical),

    // Relative distance from the passed-in date
    #"Added Days From Today" = Table.AddColumn(#"Added is Rolling 12 Month Quarter", "Days From Today", each
        Int64.From(Duration.Days([Date] - dateToTest)), Int64.Type),

    #"Added Weeks From Current Week" = Table.AddColumn(#"Added Days From Today", "Weeks From Current Week", each
        Int64.From(Duration.Days([Week Start Date] - testWeekStart) / 7), Int64.Type),

    #"Added Months From Current Month" = Table.AddColumn(#"Added Weeks From Current Week", "Months From Current Month", each
        ([Year] - testFiscalYear) * 12 + ([Month] - testMonth), Int64.Type),

    #"Added Years From Current Year" = Table.AddColumn(#"Added Months From Current Month", "Years From Current Year", each
        [Year] - testFiscalYear, Int64.Type),

    // Prior Year Same Period (PYSP) flags
    #"Added is PYSP Week" = Table.AddColumn(#"Added Years From Current Year", "is Prior Year Same Week", each
        if [Year] = testFiscalYear - 1 and [#"Week Number"] = testWeekNumber then true else null, type logical),

    #"Added is PYSP Month" = Table.AddColumn(#"Added is PYSP Week", "is Prior Year Same Month", each
        if [Year] = testFiscalYear - 1 and [Month] = testMonth then true else null, type logical),

    #"Added is PYSP Quarter" = Table.AddColumn(#"Added is PYSP Month", "is Prior Year Same Quarter", each
        if [Year] = testFiscalYear - 1 and [Quarter] = testQuarter then true else null, type logical),

    // Prior Year to Date (same fiscal year - 1, through the same week number)
    #"Added is PYTD" = Table.AddColumn(#"Added is PYSP Quarter", "is Prior Year to Date", each
        if [Year] = testFiscalYear - 1 and [#"Week Number"] <= testWeekNumber then true else null, type logical),

    // Last complete period flags (most recently fully-finished period)
    #"Added is Last Complete Week" = Table.AddColumn(#"Added is PYTD", "is Last Complete Week", each
        if [Week Start Date] = testPriorWeekStart then true else null, type logical),

    #"Added is Last Complete Month" = Table.AddColumn(#"Added is Last Complete Week", "is Last Complete Month", each
        if [Year] = testPriorMonthYear and [Month] = testPriorMonth then true else null, type logical),

    #"Added is Last Complete Quarter" = Table.AddColumn(#"Added is Last Complete Month", "is Last Complete Quarter", each
        if [Year] = testPriorQuarterYear and [Quarter] = testPriorQuarter then true else null, type logical),

    // Quarters From Current Quarter
    #"Added Quarters From Current Quarter" = Table.AddColumn(#"Added is Last Complete Quarter", "Quarters From Current Quarter", each
        ([Year] - testFiscalYear) * 4 + ([Quarter] - testQuarter), Int64.Type),

    // Is Weekend (Sunday=0, Saturday=6)
    #"Added is Weekend" = Table.AddColumn(#"Added Quarters From Current Quarter", "is Weekend", each
        if [Day of Week] = 0 or [Day of Week] = 6 then true else null, type logical)
in
    #"Added is Weekend"