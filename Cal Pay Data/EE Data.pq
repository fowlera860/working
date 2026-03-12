let
    Salary_Date = Date.From(Excel.CurrentWorkbook(){[Name="Salary_Date"]}[Content]{0}[Column1]),
    Hourly_Date = Date.From(Excel.CurrentWorkbook(){[Name="Hourly_Date"]}[Content]{0}[Column1]),
    Dir = Excel.CurrentWorkbook(){[Name="CurrentDirectory"]}[Content]{0}[Column1],
    File = Excel.CurrentWorkbook(){[Name="FileName"]}[Content]{0}[Column1],
    Source = Excel.Workbook(File.Contents(Dir & File), null, true),
    Sheet1_Sheet = Source{[Item="Sheet1",Kind="Sheet"]}[Data],
    #"Promoted Headers" = Table.PromoteHeaders(Sheet1_Sheet, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{"Address Number", Int64.Type}, {"Alpha Name", type text}, {"Co ", Int64.Type}, {"Business Unit", Int64.Type}, {"Business Unit_1", type text}, {"Home Business Unit", Int64.Type}, {"Home Business Unit_2", type text}, {"Sex ", type text}, {"EEO Job", Int64.Type}, {"EEO Job_3", type text}, {"EEO Min", Int64.Type}, {"EEO Min_4", type text}, {"F0116 ADDS", type text}, {"Date Started", type date}, {"Check Date", type date}, {"PDBA Code", Int64.Type}, {"PDBA Code_5", type text}, {"Date Term.", type any}, {"Pay Freq", type text}, {"FY ", Int64.Type}, {"Medicare Taxable Wages - MCWG", type number}, {"Hours ", type number}}),
    #"Added Custom" = Table.AddColumn(#"Changed Type", "Worked Weeks.1", each if [Worked Weeks] > 53 then 53 else [Worked Weeks]),
    #"Removed Columns" = Table.RemoveColumns(#"Added Custom",{"Worked Weeks"}),
    #"Renamed Columns" = Table.RenameColumns(#"Removed Columns",{{"Worked Weeks.1", "Worked Weeks"}}),
    #"Added Custom1" = Table.AddColumn(#"Renamed Columns", "Establishment", each if ([Business Unit] = 60 and [EEO Job] <> 4) then "Porterville Plant" else if ([Business Unit] = 22 and [EEO Job] <> 4) then "Susan Street Plant" else if  [F0116 ADDS] = "CA" then "Sales - CA" else  null),
    #"Filtered Rows" = Table.SelectRows(#"Added Custom1", each ([Establishment] <> null)),
    #"Address Date Flags" = Table.Group(
        #"Filtered Rows",
        {"Address Number"},
        {
            {"HasHourlyDate", each List.Contains(List.Transform(List.RemoveNulls([Check Date]), each Date.From(_)), Hourly_Date), type logical},
            {"HasSalaryDate", each List.Contains(List.Transform(List.RemoveNulls([Check Date]), each Date.From(_)), Salary_Date), type logical}
        }
    ),
    #"Merged Address Flags" = Table.NestedJoin(#"Filtered Rows", {"Address Number"}, #"Address Date Flags", {"Address Number"}, "AddressFlags", JoinKind.LeftOuter),
    #"Expanded Address Flags" = Table.ExpandTableColumn(#"Merged Address Flags", "AddressFlags", {"HasHourlyDate", "HasSalaryDate"}, {"HasHourlyDate", "HasSalaryDate"}),
    #"Added Emp_on_date" = Table.AddColumn(
        #"Expanded Address Flags",
        "Emp_on_date",
           each if Text.Trim([Pay Freq]) = "W" and [HasHourlyDate] then "Y"
               else if Text.Trim([Pay Freq]) = "S" and [HasSalaryDate] then "Y"
             else "N",
        type text
    ),
    #"Removed Helper Columns" = Table.RemoveColumns(#"Added Emp_on_date",{"HasHourlyDate", "HasSalaryDate"})
in
    #"Removed Helper Columns"