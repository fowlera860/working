// Inventory
// FIP012 + FIP020T: on-hand inventory converted to sq yds, filtered by backing/size/warehouse
let
    SQL = "
        SELECT
            FMSTYL                                          AS Style,
            FMCLR                                          AS Color,
            FMBACK                                         AS Back,
            FMSIZE                                         AS Size,
            CASE WHEN FMDLOT = '' THEN FMPLAN ELSE FMDLOT END AS Lot,
            SUM(FMIQTY) * F2SCSE * F2SQIN / 144            AS Qty
        FROM data.FIP012, data.FIP020T
        WHERE FMACT = 0
          AND FMBACK IN(" & param_BackingList & ")
          AND FMSIZE IN(" & param_SizeList & ")
          AND FMSTYL = F2STYL
          AND FMCLR  = F2CLR
          AND FMSIZE = F2SIZE
          AND FMWHSE IN(" & param_Warehouse & ")
        GROUP BY FMSTYL, FMCLR, FMBACK, FMSIZE, FMDLOT, FMPLAN, F2SQIN, F2SCSE
    ",
    Source = Sql.Database("TDG-DLT-IBMSQL", "CAMS", [Query = SQL]),
    TextColumnList = List.Select(Table.ColumnNames(Source), each Value.Is(Table.Column(Source, _){0}, type text)),
    CleanSource = Table.TransformColumns(Source, List.Transform(TextColumnList, each {_, Text.Trim}))
in
    CleanSource
