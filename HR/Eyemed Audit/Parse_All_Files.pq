let
    FolderPath = Folder_Path,
    Source = Folder.Files(FolderPath),
    VisibleFiles = Table.SelectRows(Source, each [Attributes]?[Hidden]? <> true),
    ExcelFiles = Table.SelectRows(VisibleFiles, each List.Contains({".xlsx", ".xlsm", ".xlsb", ".xls"}, Text.Lower([Extension]))),
    ParsedData = Table.AddColumn(
        ExcelFiles,
        "ParsedTable",
        each
            let
                FileName = [Name],
                ParsedOrError = try
                    let
                        Workbook = Excel.Workbook([Content], null, true),
                        #"FULL MONTH LIST_Sheet" = Workbook{[Item="FULL MONTH LIST", Kind="Sheet"]}[Data],
                        #"Removed Top Rows" = Table.Skip(#"FULL MONTH LIST_Sheet", 10),
                        #"Promoted Headers" = Table.PromoteHeaders(#"Removed Top Rows", [PromoteAllScalars=true]),
                        #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"Rate", Currency.Type}}),
                        #"Removed Columns" = Table.RemoveColumns(#"Changed Type", {"Column9", "Column7", "Column3", "Column12", "Column13", "Column15", "Column16"}),
                        #"Added Source File" = Table.AddColumn(#"Removed Columns", "SourceFile", each FileName, type text)
                    in
                        #"Added Source File"
                otherwise
                    #table(type table [SourceFile = text], {{"<PARSE FAILED> " & FileName}})
            in
                ParsedOrError
    ),
    Combined = Table.Combine(ParsedData[ParsedTable]),
    #"Reordered Columns" = Table.ReorderColumns(Combined,{"SourceFile", "EM Subscriber ID", "Client Subscriber ID", "Last Name", "First Name", "Billing Tier", "Plan", "Rate", "Division Code", "Location Code", "Company Code"}),
    #"Filtered Rows" = Table.SelectRows(
        #"Reordered Columns",
        each Text.StartsWith(Text.From([SourceFile]), "<PARSE FAILED>") or [EM Subscriber ID] <> null
    )
in
    #"Filtered Rows"