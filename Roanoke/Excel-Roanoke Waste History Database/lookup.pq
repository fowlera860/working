let
    Source = Excel.Workbook(File.Contents("\\tdg-sa-file\Atmore\Production Planning\Monday Reports\7. roanoke Production and Waste - Per Day - Standard vs Actual\roanoke Production and Waste - Per Day - Standard vs Actual.xlsm"), null, true),
    Database_Table = Source{[Item="Database",Kind="Table"]}[Data],
    #"Changed Type" = Table.TransformColumnTypes(Database_Table,{{"Week Ending", type date}, {"Total Lbs Produced", type number}, {"Total Std Cost", Currency.Type}, {"Std Cost/Lb", Currency.Type}, {"Std Waste Cost", Currency.Type}, {"Std Waste Cost/Lb", Currency.Type}, {"Actual Waste Cost", Currency.Type}, {"Actual Waste Cost/Lb", Currency.Type}, {"Undefined", Currency.Type}}),
    KnownColumns = {"Week Ending", "Total Lbs Produced", "Total Std Cost", "Std Cost/Lb", "Std Waste Cost", "Std Waste Cost/Lb", "Actual Waste Cost", "Actual Waste Cost/Lb", "Undefined"},
    DynamicColumns = List.Difference(Table.ColumnNames(#"Changed Type"), KnownColumns),
    #"Currency Dynamic" = Table.TransformColumnTypes(#"Changed Type", List.Transform(DynamicColumns, each {_, Currency.Type})),
    #"Filtered Rows" = Table.SelectRows(#"Currency Dynamic", each [Week Ending] >= From_Date and [Week Ending] <= To_Date),
    CablingCols  = List.Select(DynamicColumns, each Text.StartsWith(_, "Cabling") or Text.Contains(_, ".Cabling")),
    SuperbaCols  = List.Select(DynamicColumns, each not (Text.StartsWith(_, "Cabling") or Text.Contains(_, ".Cabling")) and Text.StartsWith(_, "Heat Set.") and Text.EndsWith(_, ".Superba")),
    GVACols      = List.Select(DynamicColumns, each not (Text.StartsWith(_, "Cabling") or Text.Contains(_, ".Cabling")) and Text.StartsWith(_, "Heat Set.") and Text.EndsWith(_, ".GVA")),
    HeatsetCols  = List.Select(DynamicColumns, each not (Text.StartsWith(_, "Cabling") or Text.Contains(_, ".Cabling")) and Text.StartsWith(_, "Heat Set.") and not Text.EndsWith(_, ".Superba") and not Text.EndsWith(_, ".GVA")),
    OtherCols    = List.Select(DynamicColumns, each not (Text.StartsWith(_, "Cabling") or Text.Contains(_, ".Cabling")) and not Text.StartsWith(_, "Heat Set.")),
    #"Add Cabling" = Table.AddColumn(#"Filtered Rows", "Cabling", each List.Sum(List.Transform(CablingCols, (col) => Record.Field(_, col))), Currency.Type),
    #"Add Superba" = Table.AddColumn(#"Add Cabling",  "Superba",  each List.Sum(List.Transform(SuperbaCols,  (col) => Record.Field(_, col))), Currency.Type),
    #"Add GVA"     = Table.AddColumn(#"Add Superba",  "GVA",      each List.Sum(List.Transform(GVACols,      (col) => Record.Field(_, col))), Currency.Type),
    #"Add Heatset" = Table.AddColumn(#"Add GVA",      "Heatset",  each List.Sum(List.Transform(HeatsetCols,  (col) => Record.Field(_, col))), Currency.Type),
    #"Add Other"   = Table.AddColumn(#"Add Heatset",  "Other",    each List.Sum(List.Transform(OtherCols,    (col) => Record.Field(_, col))), Currency.Type)
in
    #"Add Other"