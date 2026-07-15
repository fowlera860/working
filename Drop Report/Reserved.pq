// Reserved
// MTP040 + FIP020T: reserved inventory converted to sq yds, filtered by backing/size/warehouse
let
    SQL = "
        SELECT
            M4STYL                                  AS Style,
            M4CLR                                   AS Color,
            M4BACK                                  AS Back,
            M4SIZE                                  AS Size,
            SUM(M4RSQT) * F2SCSE * F2SQIN / 144     AS Reserved
        FROM data.MTP040, data.FIP020T
        WHERE M4BACK IN(" & param_BackingList & ")
          AND M4SIZE IN(" & param_SizeList & ")
          AND F2STYL  = M4STYL
          AND F2CLR   = M4CLR
          AND F2BACK  = M4BACK
          AND F2SIZE  = M4SIZE
          AND M4WHSE  IN(" & param_Warehouse & ")
        GROUP BY M4STYL, M4CLR, M4BACK, M4SIZE, F2SQIN, F2SCSE
    ",
    Source = Sql.Database("TDG-DLT-IBMSQL", "CAMS", [Query = SQL]),
    TextColumnList = List.Select(Table.ColumnNames(Source), each Value.Is(Table.Column(Source, _){0}, type text)),
    CleanSource = Table.TransformColumns(Source, List.Transform(TextColumnList, each {_, Text.Trim}))
in
    CleanSource
