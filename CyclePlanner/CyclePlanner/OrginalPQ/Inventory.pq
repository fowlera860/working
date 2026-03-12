// Inventory
let
		SQL = Group_Filter_CTE & "
            SELECT 
                FIP010.F1STYL Style,
                FIP010.F1CLR Color,
                FIP010.F1SIZE Size,
                FIP010.F1BACK Back,
                FIP010.F1ROLL RollNumber,
                FIP010.F1ALTF  Feet,
                FIP010.F1DLOT DyeLot,
                FIP010.F1WHSE WH,
                FIP010.F1LOC Loc
            FROM data.FIP010 FIP010
            WHERE 
                F1ACT = 0
                AND F1QLTY = 1
                AND FIP010.F1ALTF > 0
                AND FIP010.F1SFLG = ''
                AND FIP010.F1ALTF > " & Number.ToText(InvRollCutoff) & "
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
		Source = Sql.Database("TDG-DLT-IBMSQL", "CAMS", [Query=SQL])
	in
		Source
