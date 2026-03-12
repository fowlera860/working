// MillOrderProductionAssignment
let
    SQL = Group_Filter_CTE & "
        SELECT 
            PRP010.PRSTYL AS Style,
            PRP010.PRCLR AS Color,
            PRP010.PRSIZE AS Size,
            PRP010.PRBACK AS Back,
            PRP010.PRORD# as OrdNum,
            PRP010.PROLNE as OrdLine,
            PRP010.PRCTL# as ProdOrder,
            PRP010.PRQTY as AsgQty,
            PRP010.PRCJUL+366 as PromDt,
            ISNULL(SUM(FIP010.F1BLTF),0)  as RsvQty,
            CASE 
                WHEN PRP010.PRQTY - ISNULL(SUM(FIP010.F1BLTF),0) < 0 THEN 0
                ELSE PRP010.PRQTY - ISNULL(SUM(FIP010.F1BLTF),0)
            END as PendingProd

        FROM CAMS.DATA.PRP010 PRP010
        LEFT OUTER JOIN CAMS.DATA.FIP010 FIP010
        ON
            FIP010.F1AORD = PRP010.PRORD#
            AND FIP010.F1ALNE = PRP010.PROLNE

        WHERE 
            PRPRTF <> 'Y'
            AND EXISTS (
                SELECT 1
                FROM FilterList f
                WHERE 
                    f.style = PRP010.PRSTYL
                    AND f.color = PRP010.PRCLR
                    AND f.size = PRP010.PRSIZE
                    AND f.back = PRP010.PRBACK
            )
        GROUP BY
            PRP010.PRSTYL,
            PRP010.PRCLR,
            PRP010.PRSIZE,
            PRP010.PRBACK,
            PRP010.PRORD#,
            PRP010.PROLNE,
            PRP010.PRCTL#,
            PRP010.PRQTY,
            PRP010.PRCJUL
		",
	Source = Sql.Database("TDG-DLT-IBMSQL", "CAMS", [Query=SQL]),
    ChangeType = Table.TransformColumnTypes(Source,{{"PromDt", type date}}),
    #"Added Custom" = Table.AddColumn(ChangeType, "Src", each "Production Assignment")
in
    #"Added Custom"
