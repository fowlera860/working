let
		SQL = Group_Filter_CTE & "
            SELECT 
                FIP025.FYSTYL Style,
                FIP025.FYCLR Color,
                FIP025.FYSIZE Size,
                FIP025.FYALT# Alt#,
                FIP025.FYBEAM BeamGroup,
                FIP025.FYYSEQ Seq,
                FIP025.FYYNID YarnID,
                FIP025.FYTYPE YarnType,
                FIP025.FYOZSY OzSY,
                FIP025.FY#END NumEnds,
                FIP025.FYYPCT Per,
                FIP025.FYBMYN Beamed
            FROM data.FIP025 FIP025
            WHERE 
                FIP025.FYALT# = 0

                AND EXISTS (
                    SELECT 1
                    FROM FilterList f
                    WHERE 
                        f.style = FIP025.FYSTYL
                        AND (
                            f.color = FIP025.FYCLR
                            OR
                            f.color = ''
                            )
                        AND f.size = FIP025.FYSIZE
                )

		",
		Source = Sql.Database("TDG-DLT-IBMSQL", "CAMS", [Query=SQL])
	in
		Source