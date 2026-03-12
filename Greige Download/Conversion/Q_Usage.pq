let
    // Get style filter
    StyleFilter = Q_StyleFilter,
    
    // Calculate date range: 91-day window from ~1 year ago
    Today = DateTime.Date(DateTime.LocalNow()),
    EDate = Date.AddDays(Today, -366 - 4),  // 370 days ago
    SDate = Date.AddDays(EDate, -91),   // 91 days before that
    
    // Convert dates to numbers for iSeries date comparison
    SDateNum = Number.From(SDate),
    EDateNum = Number.From(EDate),
    
    SQL = "
        WITH ASTYLES AS (
            -- Original styles mapping to themselves
            SELECT F2STYL AS ASTYLE, F2STYL AS OSTYLE, '' AS ACLR
            FROM CAMS.FIP020
            WHERE F2STYL IN (" & StyleFilter & ")
              AND F2CLR = ''
            
            UNION ALL
            
            -- Alternate styles from FIP028
            SELECT DISTINCT FXSTYL AS ASTYLE, F2STYL AS OSTYLE, FXCLR AS ACLR
            FROM CAMS.FIP028
            INNER JOIN CAMS.FIP020 
                ON FXOSTY = F2STYL
            WHERE F2STYL IN (" & StyleFilter & ")
              AND F2CLR = ''
        ),
        SYDS AS (
            -- RUN 1: Sales with exact color matches (ASTYLE=style AND ACLR=color)
            SELECT DISTINCT 
                OSTYLE AS SSTYLE, 
                ASTYLE, 
                ACLR, 
                SUM(S1SQYD) AS YDS
            FROM ASTYLES
            LEFT OUTER JOIN CAMS.SAP400 
                ON ASTYLE = S1ISTY
                AND ACLR = S1ICLR
                AND S1IJUL BETWEEN " & Text.From(SDateNum) & " AND " & Text.From(EDateNum) & "
                AND S1LPRC > 0
                AND S1WHSE IN ('59','06','BC','03','01','80')
                AND S1CRIN = 'I'
            WHERE NOT EXISTS(
                SELECT C1INHS FROM CAMS.CIP010 
                WHERE C1CST# = S1CST1 AND C1INHS = 'Y'
            )
            GROUP BY OSTYLE, ASTYLE, ACLR
            
            UNION ALL
            
            -- RUN 2: Sales with blank color in ASTYLES (any S1ICLR not already matched in RUN 1)
            SELECT DISTINCT 
                OSTYLE AS SSTYLE, 
                ASTYLE, 
                ACLR, 
                SUM(S1SQYD) AS YDS
            FROM ASTYLES
            LEFT OUTER JOIN CAMS.SAP400 
                ON ASTYLE = S1ISTY
                AND ASTYLES.ACLR = ''
                AND S1IJUL BETWEEN " & Text.From(SDateNum) & " AND " & Text.From(EDateNum) & "
                AND S1LPRC > 0
                AND S1WHSE IN ('59','06','BC','03','01','80')
                AND S1CRIN = 'I'
            WHERE NOT EXISTS(
                SELECT C1INHS FROM CAMS.CIP010 
                WHERE C1CST# = S1CST1 AND C1INHS = 'Y'
            )
            AND NOT EXISTS(
                SELECT ACLR FROM ASTYLES AS CHK
                WHERE CHK.ASTYLE = S1ISTY
                AND CHK.ACLR = S1ICLR
            )
            GROUP BY OSTYLE, ASTYLE, ACLR
        )
        SELECT 
            SSTYLE AS STYLE,
            ROUND(SUM(YDS)/13, 0) AS USAGE
        FROM SYDS
        GROUP BY SSTYLE
    ",
    Source = Odbc.Query("DRIVER={Client Access ODBC Driver (32-bit)};SYSTEM=TDG-SA-DTS;DBQ=CAMS;DFTPKGLIB=QGPL;LANGUAGEID=ENU;PKG=QGPL/DEFAULT(IBM),2,0,1,0,512;QRYSTGLMT=-1;", SQL),
    TypedSource = Table.TransformColumnTypes(Source, {{"STYLE", type text}}),
    TextColumnList = List.Select(Table.ColumnNames(TypedSource), each Value.Is(Table.Column(TypedSource, _){0}, type text)),
    CleanSource = Table.TransformColumns(TypedSource, List.Transform(TextColumnList, each {_, Text.Trim}))
in
    CleanSource