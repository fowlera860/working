let
    SQL = "
        SELECT  W2WCDE, W2WDSC, W2ROLL, W2GROL, W2BLTF, W2BLTI, 
                W2BWTF, W2BWTI, W2ADTE, W2AJUL, W2STYL, W2WHSE, 
                W2CODE, W2TIME, W2USER
        FROM WIP020
        WHERE W2AJUL >= " & Number.ToText(LastDte) & "
    ",
    Source = Odbc.Query("DRIVER={Client Access ODBC Driver (32-bit)};SYSTEM=TDG-SA-DTS;DBQ=CAMS;DFTPKGLIB=QGPL;LANGUAGEID=ENU;PKG=QGPL/DEFAULT(IBM),2,0,1,0,512;QRYSTGLMT=-1;", SQL),
    TextColumnList = List.Select(Table.ColumnNames(Source), each Value.Is(Table.Column(Source, _){0}, type text)),
    CleanSource = Table.TransformColumns(Source, List.Transform(TextColumnList, each {_, Text.Trim}))

in
    CleanSource