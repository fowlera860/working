// Assigned
// OPP010T + FIP020T: open sales order assignments converted to sq yds, filtered by backing/size/warehouse
let
    SQL = "
        SELECT
            O1ISTY                                    AS Style,
            O1ICLR                                    AS Color,
            O1IBK                                     AS Back,
            O1ISZE                                    AS Size,
            SUM(O1OQTY - O1SQTY) * F2SCSE * F2SQIN / 144 AS Qty
        FROM data.OPP010T, data.FIP020T
        WHERE O1IBK   IN(" & param_BackingList & ")
          AND O1ISZE  IN(" & param_SizeList & ")
          AND O1COMP <> 'Y'
          AND O1OCJL  = 0
          AND F2STYL  = O1ISTY
          AND F2CLR   = O1ICLR
          AND F2BACK  = O1IBK
          AND F2SIZE  = O1ISZE
          AND O1OQTY  > O1SQTY
          AND O1WHSE  IN(" & param_Warehouse & ")
        GROUP BY O1ISTY, O1ICLR, O1IBK, O1ISZE, F2SQIN, F2SCSE
    ",
    Source = Sql.Database("TDG-DLT-IBMSQL", "CAMS", [Query = SQL]),
    TextColumnList = List.Select(Table.ColumnNames(Source), each Value.Is(Table.Column(Source, _){0}, type text)),
    CleanSource = Table.TransformColumns(Source, List.Transform(TextColumnList, each {_, Text.Trim}))
in
    CleanSource
