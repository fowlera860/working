// MillOrderRollAssignment
let
    SQL = Group_Filter_CTE & "
        SELECT 
            FIP010.F1STYL AS Style,
            FIP010.F1CLR AS Color,
            FIP010.F1SIZE AS Size,
            FIP010.F1BACK AS Back,
            FIP010.F1AORD as OrdNum,
            FIP010.F1ALNE as OrdLine,
            FIP010.F1BLTF as Qty,
            OPP010.O1PJUL+366 as PromDt

        FROM CAMS.DATA.FIP010 FIP010

        LEFT OUTER JOIN CAMS.DATA.OPP010 OPP010
            ON
                OPP010.O1ORD# = FIP010.F1AORD
                AND OPP010.O1LINE = FIP010.F1ALNE
        WHERE 
             FIP010.F1ACT < 7
            AND FIP010.F1AORD <> 0
            AND EXISTS (
                SELECT 1
                FROM FilterList f
                WHERE 
                    f.style = FIP010.F1STYL
                    AND f.color = FIP010.F1CLR
                    AND f.size = FIP010.F1SIZE
                    AND f.back = FIP010.F1BACK
            )

		",
	Source = Sql.Database("TDG-DLT-IBMSQL", "CAMS", [Query=SQL]),
    #"Added Custom" = Table.AddColumn(Source, "Src", each "Roll Reserve"),
    #"Changed Type" = Table.TransformColumnTypes(#"Added Custom",{{"PromDt", type date}})
in
    #"Changed Type"
