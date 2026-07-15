let
    WorkedCodes = PayTypes,
    Source = HoursWorked,
    #"Replaced Value" = Table.ReplaceValue(Source,null,0,Replacer.ReplaceValue,{"Hours Worked"}),
    #"Merged Queries" = Table.NestedJoin(#"Replaced Value", {"PDBA Code"}, PayTypes, {"Pay Type"}, "PayTypes", JoinKind.LeftOuter),
    #"Expanded PayTypes" = Table.ExpandTableColumn(#"Merged Queries", "PayTypes", {"Rate"}, {"PayTypes.Rate"}),
    #"Filtered Rows1" = Table.SelectRows(#"Expanded PayTypes", each ([PayTypes.Rate] <> null)),
    #"Added Custom" = Table.AddColumn(#"Filtered Rows1", "Adjusted Pay Rate", each if [Hours Worked] = 0 then null 
  else Number.Round(Number.Abs([Gross Pay] / [Hours Worked] / [PayTypes.Rate]), 2)),
    #"Grouped Rows" = Table.Group(#"Added Custom", {"Address Number", "Alpha Name", "Check Date", "Co ", "Pay Per Date", "Employee Tax ID - SSN", "Company", " Tax Ident"}, {{"Hours Worked", each List.Sum([Hours Worked]), type nullable number}, {"AllRows", each _, type table [Address Number=nullable number, #"Employee Tax ID - SSN"=text, Alpha Name=nullable text, Check Date=nullable date, Pay Per Date=nullable date, #"Trans. No."=number, Business Unit=nullable text, Job Typ=nullable text, #"Co "=nullable number, Company=text, PDBA Code=nullable number, PDBA Code_1=nullable text, Hours Paid=nullable number, Hours Worked=nullable number, Gross Pay=number, #" Tax Ident"=text, PayTypes.Rate=number, Adjusted Pay Rate=nullable number]}, {"Hours Paid", each List.Sum([Hours Paid]), type nullable number}, {"Business Unit", each List.Min([Business Unit]), type nullable text}, {"Job Typ", each List.Min([Job Typ]), type nullable text}}),
    AddedRegOTHoursPaid = Table.AddColumn(#"Grouped Rows", "Reg Overtime Hours Paid", each List.Sum(Table.SelectRows([AllRows], (r) => List.Contains({100, 101, 105}, r[PDBA Code]))[#"Hours Paid"]) ?? 0),
    AddedDblOTHoursPaid = Table.AddColumn(AddedRegOTHoursPaid, "Dbl Overtime Hours Paid", each List.Sum(Table.SelectRows([AllRows], (r) => r[PDBA Code] = 102)[#"Hours Paid"]) ?? 0),
    AddedRegOTHoursWorked = Table.AddColumn(AddedDblOTHoursPaid, "Reg Overtime Hours Worked", each List.Sum(Table.SelectRows([AllRows], (r) => List.Contains({100, 101, 105}, r[PDBA Code]))[#"Hours Worked"]) ?? 0),
    AddedDblOTHoursWorked = Table.AddColumn(AddedRegOTHoursWorked, "Dbl Overtime Hours Worked", each List.Sum(Table.SelectRows([AllRows], (r) => r[PDBA Code] = 102)[#"Hours Worked"]) ?? 0),
    AddedRegOTPaid = Table.AddColumn(AddedDblOTHoursWorked, "Reg Overtime Paid", each List.Sum(Table.SelectRows([AllRows], (r) => List.Contains({100, 101, 105}, r[PDBA Code]) and (r[Hours Worked] ?? 0) <> 0)[Gross Pay]) ?? 0),
    AddedDblOTPaid = Table.AddColumn(AddedRegOTPaid, "Dbl Overtime Paid", each List.Sum(Table.SelectRows([AllRows], (r) => r[PDBA Code] = 102 and (r[Hours Paid] ?? 0) <> 0)[Gross Pay]) ?? 0),
    AddedRegOTAdjPaid = Table.AddColumn(AddedDblOTPaid, "Reg Overtime Adjustment Paid", each List.Sum(Table.SelectRows([AllRows], (r) => List.Contains({100, 101, 105}, r[PDBA Code]) and (r[Hours Worked] ?? 0) = 0)[Gross Pay]) ?? 0),
    AddedDblOTAdjPaid = Table.AddColumn(AddedRegOTAdjPaid, "Dbl Overtime Adjustment Paid", each List.Sum(Table.SelectRows([AllRows], (r) => r[PDBA Code] = 102 and (r[Hours Worked] ?? 0) = 0)[Gross Pay]) ?? 0),
    AddedOTTaxRedHours = Table.AddColumn(AddedDblOTAdjPaid, "OT Tax Red Hours", each List.Max({([Hours Worked] ?? 0) - 40, 0})-[Dbl Overtime Hours Paid]),
    AddedTaxRedRegOT = Table.AddColumn(AddedOTTaxRedHours, "Tax Red Reg OT", each if ([Reg Overtime Hours Paid] ?? 0) = 0 then 0 
        else (([OT Tax Red Hours] ?? 0) / ([Reg Overtime Hours Paid] ?? 0) * ([Reg Overtime Paid] ?? 0) /3) ?? 0),
    AddedTaxRedDTHours = Table.AddColumn(AddedTaxRedRegOT, "Tax Red DT Hours", each [Dbl Overtime Hours Paid]),
    AddedTaxRedDT = Table.AddColumn(AddedTaxRedDTHours, "Tax Red DT", each 
        if ([Dbl Overtime Paid] ?? 0) = 0 then 0 
        else (([Tax Red DT Hours] ?? 0) / ([Dbl Overtime Hours Paid] ?? 0) * ([Dbl Overtime Paid] ?? 0) * 0.25) ?? 0),
    AddedTaxRedTotal = Table.AddColumn(AddedTaxRedDT, "Tax Red $ Total", each ([Tax Red Reg OT] ?? 0) + ([Tax Red DT] ?? 0) + (([Reg Overtime Adjustment Paid] ?? 0)/3) + (([Dbl Overtime Adjustment Paid] ?? 0)/4)),
    AddedTotalHours= Table.AddColumn(
        AddedTaxRedTotal, 
        "Total Hours Worked", 
        each List.Sum([AllRows][Hours Worked])
    ),
    AddedPaidRates = Table.AddColumn(
        AddedTotalHours, 
        "Paid Rate", 
        each let
            rates = List.RemoveNulls([AllRows][Adjusted Pay Rate]),
            distinctRates = List.Distinct(rates)
        in
            if List.Count(distinctRates) = 0 then null
            else if List.Count(distinctRates) = 1 then distinctRates{0}
            else "Multiple Rates"
    ),
    AddedRateDiff = Table.AddColumn(
        AddedPaidRates,
        "Rate Difference",
        each let
            rates = List.RemoveNulls([AllRows][Adjusted Pay Rate])
        in
            if List.Count(rates) = 0 then null
            else List.Max(rates) - List.Min(rates)
    )
in
    AddedRateDiff