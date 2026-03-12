// TuftingOrders
let
    SQL = Group_Filter_CTE & "
        SELECT 
            YAP070.Y7STYL AS Style,
            YAP070.Y7CLR AS Color,
            YAP070.Y7SIZE AS Size,
            YAP070.Y7BACK AS Back,
            YAP070.Y7CTL# as ProdNum,
            YAP070.Y7FTSC as FtOrdered,
            YAP070.Y7FTFT as FtProduced,
			YAP070.Y7OJUL+366 as PromDate


        FROM CAMS.DATA.YAP070 YAP070


        WHERE 
            Y7ACT = 0
            AND EXISTS (
                SELECT 1
                FROM FilterList f
                WHERE 
                    f.style = YAP070.Y7STYL
                    AND f.size = YAP070.Y7SIZE
            )
		",
	Source = Sql.Database("TDG-DLT-IBMSQL", "CAMS", [Query=SQL]),
    ChangeType = Table.TransformColumnTypes(Source,{{"PromDate", type date}})
in
    ChangeType
