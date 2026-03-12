// UnassignedMillOrders
let
    SQL = Group_Filter_CTE & "
        SELECT 
            OPP010.O1ISTY AS Style,
            OPP010.O1ICLR AS Color,
            OPP010.O1ISZE AS Size,
            OPP010.O1IBK AS Back,
            OPP010.O1ORD# as OrdNum,
            OPP010.O1LINE as OrdLine,
            OPP010.O1OQTY as Qty,
            OPP010.O1OQUM as UOM,
            OPP010.O1PJUL+366 as PromDt

        FROM CAMS.DATA.OPP010 OPP010
        WHERE 
             OPP010.O1CNCD = 0
			AND OPP010.O1OCJL = 0
			AND OPP010.O1AQTY = 0
			AND OPP010.O1AJUL = 0
            AND EXISTS (
                SELECT 1
                FROM FilterList f
                WHERE 
                    f.style = OPP010.O1ISTY
                    AND f.color = OPP010.O1ICLR
                    AND f.size = OPP010.O1ISZE
                    AND f.back = OPP010.O1IBK
            )
			AND NOT EXISTS (
				SELECT 1
				FROM CAMS.DATA.PRP010 PRP010
				WHERE
					OPP010.O1ORD# = PRP010.PRORD#
					AND OPP010.O1LINE = prp010.PROLNE
			)
		",
	Source = Sql.Database("TDG-DLT-IBMSQL", "CAMS", [Query=SQL]),
    ChangeType = Table.TransformColumnTypes(Source,{{"PromDt", type date}}),
    #"Merged Queries" = Table.NestedJoin(ChangeType, {"Style", "Color", "Size", "Back"}, Product_Specs, {"Style", "Color", "Size", "Back"}, "Product_Specs", JoinKind.LeftOuter),
    #"Expanded Product_Specs" = Table.ExpandTableColumn(#"Merged Queries", "Product_Specs", {"RollSize"}, {"Product_Specs.RollSize"}),
    #"Added Custom" = Table.AddColumn(#"Expanded Product_Specs", "LF", each if [UOM] = "RL" then [Qty] * [Product_Specs.RollSize] else [Qty]),
    #"Added Custom1" = Table.AddColumn(#"Added Custom", "Src", each "Unassigned")
in
    #"Added Custom1"
