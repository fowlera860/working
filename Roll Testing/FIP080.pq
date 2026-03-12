let
    SQL = "
        SELECT  F8ROLL, F8GROL, F8BWTF, F8BWTI, F8BLTF, F8BLTI, 
                F8AWTF, F8AWTI, F8ALTF, F8ALTI, F8DATE, F8JUL, 
                F8USER, F8PRCS, F8WHSE
        FROM FIP080
        WHERE F8JUL >= " & Number.ToText(LastDte) & "
    ",
    Source = Odbc.Query("DRIVER={Client Access ODBC Driver (32-bit)};SYSTEM=TDG-SA-DTS;DBQ=CAMS;DFTPKGLIB=QGPL;LANGUAGEID=ENU;PKG=QGPL/DEFAULT(IBM),2,0,1,0,512;QRYSTGLMT=-1;", SQL),
    TextColumnList = List.Select(Table.ColumnNames(Source), each Value.Is(Table.Column(Source, _){0}, type text)),
    CleanSource = Table.TransformColumns(Source, List.Transform(TextColumnList, each {_, Text.Trim}))

in
    CleanSource