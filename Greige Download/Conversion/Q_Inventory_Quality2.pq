let
    // Get configuration and style filter
    Config = Q_Config,
    StyleFilter = Q_StyleFilter,
    MinLength = Config[Min_Roll_Length_FT],
    
    SQL = "
        SELECT G1STYL, 
               ROUND(SUM(((G1CLTF*12 + G1CLTI) * (G1CWTF*12 + G1CWTI)) / 1296), 0) as SQYD,
               COUNT(G1ROLL) AS ROLLS
        FROM CAMS.GIP010
        WHERE G1STYL IN (" & StyleFilter & ")
          AND G1QLTY NOT IN(1,7,5)
          AND G1ACT NOT IN (7, 9)
          AND G1ATLF > 1
          AND G1CLR = ''
          AND G1CLTF >= " & Number.ToText(MinLength) & "
          AND G1SCLR < '1'
          AND G1DDTE < 1
          AND G1DPRT <> 'Y'
          AND G1DLOT < '1'
          AND G1LOC <> 'LOST'
        GROUP BY G1STYL
    ",
    Source = Odbc.Query("DRIVER={Client Access ODBC Driver (32-bit)};SYSTEM=TDG-SA-DTS;DBQ=CAMS;DFTPKGLIB=QGPL;LANGUAGEID=ENU;PKG=QGPL/DEFAULT(IBM),2,0,1,0,512;QRYSTGLMT=-1;", SQL),
    // Force types and trim
    TypedSource = Table.TransformColumnTypes(Source, {{"G1STYL", type text}}),
    TextColumnList = List.Select(Table.ColumnNames(TypedSource), each Value.Is(Table.Column(TypedSource, _){0}, type text)),
    CleanSource = Table.TransformColumns(TypedSource, List.Transform(TextColumnList, each {_, Text.Trim}))

in
    CleanSource
