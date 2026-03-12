let
    currentYear = Date.Year(DateTime.LocalNow()),
    StartDate = #date(currentYear - 3, 1, 1),
    EndDate = #date(currentYear + 1, 12, 31),
    DayList = List.Dates(StartDate, Duration.Days(EndDate-StartDate)+1, #duration(1,0,0,0)),
    #"Converted to Table" = Table.FromList(DayList, Splitter.SplitByNothing(), {"Date"}, null, ExtraValues.Error),
    #"Added Columns" = Table.TransformColumns(#"Converted to Table", {{"Date", each _, type date}}),
    #"Added Year" = Table.AddColumn(#"Added Columns", "Year", each Date.Year([Date]), Int64.Type),
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
            year = Date.Year([Date]),
            jan1 = #date(year, 1, 1),
            jan1DayOfWeek = Date.DayOfWeek(jan1, Day.Sunday),
            // Find the Sunday that starts the first week of the year
            yearStartWeek = Date.AddDays(jan1, -jan1DayOfWeek)
        in
            yearStartWeek, type date),
    
    #"Added Week of Year" = Table.AddColumn(#"Added Year Start Week", "Week of Year", each
        let
            weeksDiff = Duration.Days([Week Start Date] - [Year Start Week]) / 7
        in
            weeksDiff + 1, Int64.Type),
    
    #"Added Week Year" = Table.AddColumn(#"Added Week of Year", "WeekYear", each
        Date.Year([Week Start Date]), Int64.Type),
    
    // Add Month based on Week of Year (544 schedule)
    #"Added Month" = Table.AddColumn(#"Added Week Year", "Month", each
        let
            weekOfYear = [Week of Year]
        in
            if weekOfYear <= 5 then 1      // Weeks 1-5 = January
            else if weekOfYear <= 9 then 2 // Weeks 6-9 = February
            else if weekOfYear <= 13 then 3 // Weeks 10-13 = March
            else if weekOfYear <= 17 then 4 // Weeks 14-17 = April
            else if weekOfYear <= 22 then 5 // Weeks 18-22 = May
            else if weekOfYear <= 26 then 6 // Weeks 23-26 = June
            else if weekOfYear <= 30 then 7 // Weeks 27-30 = July
            else if weekOfYear <= 34 then 8 // Weeks 31-34 = August
            else if weekOfYear <= 39 then 9 // Weeks 35-39 = September
            else if weekOfYear <= 43 then 10 // Weeks 40-43 = October
            else if weekOfYear <= 47 then 11 // Weeks 44-47 = November
            else 12,                         // Weeks 48-52 = December
        Int64.Type),
    
    // Add Month Name based on Month
    #"Added Month Name" = Table.AddColumn(#"Added Month", "Month Name", each
        let
            monthNum = [Month],
            monthNames = {"January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"}
        in
            monthNames{monthNum - 1},
        type text),
    
    // Calculate Week of Month (5-4-4 pattern with proper Sunday-Saturday weeks)
    #"Added Week of Month" = Table.AddColumn(#"Added Month Name", "Week of Month", each
        let
            month = [Month],
            year = [Year],
            
            // Get the first day of the month
            firstDayOfMonth = #date(year, month, 1),
            firstDayOfWeek = Date.DayOfWeek(firstDayOfMonth, Day.Sunday),
            
            // Find the Sunday that starts the first week of the month
            monthStartWeek = Date.AddDays(firstDayOfMonth, -firstDayOfWeek),
            
            // Calculate which week within the month this date belongs to
            weeksDiff = Duration.Days([Week Start Date] - monthStartWeek) / 7,
            weekOfMonth = weeksDiff + 1
        in
            weekOfMonth, Int64.Type),
    
    // Add Quarter information for clarity
    #"Added Quarter" = Table.AddColumn(#"Added Week of Month", "Quarter", each 
        if [Month] >= 1 and [Month] <= 3 then 1
        else if [Month] >= 4 and [Month] <= 6 then 2
        else if [Month] >= 7 and [Month] <= 9 then 3
        else 4, Int64.Type),
    
    // Add Month Type (5-week or 4-week) - now based on actual week boundaries
    #"Added Month Type" = Table.AddColumn(#"Added Quarter", "Month Type", each 
        if [Month] = 1 or [Month] = 4 or [Month] = 7 or [Month] = 10 then "5-week"
        else if [Month] = 12 then
            // For December, check if it actually spans 5 weeks based on Sunday-Saturday boundaries
            let
                firstDayOfDec = #date([Year], 12, 1),
                lastDayOfDec = #date([Year], 12, 31),
                firstSunday = Date.AddDays(firstDayOfDec, -Date.DayOfWeek(firstDayOfDec, Day.Sunday)),
                lastSaturday = Date.AddDays(lastDayOfDec, 6 - Date.DayOfWeek(lastDayOfDec, Day.Sunday)),
                totalWeeks = Duration.Days(lastSaturday - firstSunday) / 7 + 1
            in
                if totalWeeks > 4 then "5-week" else "4-week"
        else "4-week", type text),
    
    // Add Weeks in Month (integer count)
    #"Added Weeks in Month" = Table.AddColumn(#"Added Month Type", "Weeks in Month", each 
        if [Month] = 1 or [Month] = 4 or [Month] = 7 or [Month] = 10 then 5
        else if [Month] = 12 then
            // For December, calculate actual weeks based on Sunday-Saturday boundaries
            let
                firstDayOfDec = #date([Year], 12, 1),
                lastDayOfDec = #date([Year], 12, 31),
                firstSunday = Date.AddDays(firstDayOfDec, -Date.DayOfWeek(firstDayOfDec, Day.Sunday)),
                lastSaturday = Date.AddDays(lastDayOfDec, 6 - Date.DayOfWeek(lastDayOfDec, Day.Sunday)),
                totalWeeks = Duration.Days(lastSaturday - firstSunday) / 7 + 1
            in
                Number.RoundUp(totalWeeks)
        else 4, Int64.Type),
    
    // Remove helper columns
    #"Removed Helper Columns" = Table.RemoveColumns(#"Added Weeks in Month", {"Week Start Date", "Year Start Week"})
in
    #"Removed Helper Columns"