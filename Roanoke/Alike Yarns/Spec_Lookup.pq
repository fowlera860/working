let
    // 1. Load data from your SQL
    SQL = "
        SELECT DISTINCT 
            Y2FILE,
            Y2MET#,
            Y2TEXT,
            Y2CNT,
            Y2TPI,
            Y2WINSPD,
            Y2BARPRS,
            Y2BLTSPD,
            Y2TEMP,
            Y2DEWPT,
            FYBEAM,
            FYCID,
            FYCPCT
        FROM YAP302
        LEFT OUTER JOIN FIP027
            ON Y2MET# = FYFID
    ",
    Source = Odbc.Query(
        "DRIVER={Client Access ODBC Driver (32-bit)};SYSTEM=TDG-SA-DTS;DBQ=CAMSY;DFTPKGLIB=QGPL;LANGUAGEID=ENU;PKG=QGPL/DEFAULT(IBM),2,0,1,0,512;QRYSTGLMT=-1;", 
        SQL
    ),

    // 2. Keep text columns trimmed
    TextColumns = List.Select(Table.ColumnNames(Source), each Value.Is(Table.Column(Source, _){0}, type text)),
    CleanSource = Table.TransformColumns(Source, List.Transform(TextColumns, each {_, Text.Trim})),
    #"Grouped Rows" = Table.Group(CleanSource, {"Y2FILE", "Y2MET#", "Y2TEXT", "Y2CNT", "Y2TPI", "Y2WINSPD", "Y2BARPRS", "Y2BLTSPD", "Y2TEMP", "Y2DEWPT"}, {{"All_Rows", each _, type table [Y2FILE=number, #"Y2MET#"=nullable text, Y2TEXT=nullable text, Y2CNT=nullable text, Y2TPI=number, Y2WINSPD=number, Y2BARPRS=number, Y2BLTSPD=number, Y2TEMP=number, Y2DEWPT=number, FYBEAM=nullable text, FYCID=nullable text, FYCPCT=nullable number]}}),

    // 3. Determine max FYBEAM value dynamically across all nested tables
    MaxBeam = List.Max(
        List.Transform(
            #"Grouped Rows"[All_Rows],
            each List.Max(List.Transform(Table.Column(_, "FYBEAM"), each if _ = null then null else Number.From(_)))
        )
    ),
    BeamList = List.Numbers(1, MaxBeam),

    // 4. Build interleaved column definitions: ID_1, PCT_1, ID_2, PCT_2 ... ID_N, PCT_N
    //    For each beam number n, look up the All_Rows row where FYBEAM = n
    ColDefs = List.Combine(
        List.Transform(BeamList, each
            let n = _ in
            {
                {
                    "ID_" & Number.ToText(n),
                    each let t = Table.SelectRows(_[All_Rows], each Number.From([FYBEAM]) = n)
                         in if Table.IsEmpty(t) then null else t[FYCID]{0}
                },
                {
                    "PCT_" & Number.ToText(n),
                    each let t = Table.SelectRows(_[All_Rows], each Number.From([FYBEAM]) = n)
                         in if Table.IsEmpty(t) then null else t[FYCPCT]{0}
                }
            }
        )
    ),

    // 5. Add the beam columns one at a time, then remove the nested table
    WithBeamCols = List.Accumulate(
        ColDefs,
        #"Grouped Rows",
        (state, colDef) => Table.AddColumn(state, colDef{0}, colDef{1})
    ),
    Result = Table.RemoveColumns(WithBeamCols, {"All_Rows"})
in
    Result