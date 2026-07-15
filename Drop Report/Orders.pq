// Orders
// PPP010: open production orders, filtered by backing/size/warehouse
let
    SQL = "
        SELECT
            PPSTYL  AS Style,
            PPCLR   AS Color,
            PPBACK  AS Back,
            PPSIZE  AS Size,
            PPCTL#  AS Lot,
            SUM(PPOQTY - PPCQTY) AS Qty
        FROM data.PPP010
        WHERE PPCOMP <> 'Y'
          AND PPBACK IN(" & param_BackingList & ")
          AND PPSIZE IN(" & param_SizeList & ")
          AND PPWHSE IN(" & param_Warehouse & ")
        GROUP BY PPSTYL, PPCLR, PPBACK, PPSIZE, PPCTL#
    ",
    Source = Sql.Database("TDG-DLT-IBMSQL", "CAMS", [Query = SQL]),
    TextColumnList = List.Select(Table.ColumnNames(Source), each Value.Is(Table.Column(Source, _){0}, type text)),
    CleanSource = Table.TransformColumns(Source, List.Transform(TextColumnList, each {_, Text.Trim}))
in
    CleanSource
