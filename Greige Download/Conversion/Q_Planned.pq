let
    // WIP (Work In Progress) inventory from YAP070
    StyleFilter = Q_StyleFilter,
    SQL = "
        SELECT Y7STYL, 
               ROUND(SUM(((Y7FTSC-Y7FTFT)*12)*((Y7WTHF*12)+Y7WTHI))/1296,0) as PLANNED
        FROM CAMS.YAP070
        WHERE Y7STYL IN (" & StyleFilter & ")
          AND Y7ACT = 0 
          AND Y7CLR = ''
        GROUP BY Y7STYL
    ",
    Source = Odbc.Query("DRIVER={Client Access ODBC Driver (32-bit)};SYSTEM=TDG-SA-DTS;DBQ=CAMS;DFTPKGLIB=QGPL;LANGUAGEID=ENU;PKG=QGPL/DEFAULT(IBM),2,0,1,0,512;QRYSTGLMT=-1;", SQL),
    TypedSource = Table.TransformColumnTypes(Source, {{"Y7STYL", type text}}),
    TextColumnList = List.Select(Table.ColumnNames(TypedSource), each Value.Is(Table.Column(TypedSource, _){0}, type text)),
    CleanSource = Table.TransformColumns(TypedSource, List.Transform(TextColumnList, each {_, Text.Trim})),
    RenamedColumns = Table.RenameColumns(CleanSource, {{"Y7STYL", "STYLE"}})
in
    RenamedColumns
