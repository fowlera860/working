// Product_Specs
let
		SQL = Group_Filter_CTE & "
            Select DISTINCT
                f.planningGroup PlanningGroup,
                f.colorGroup ColorGroup,
                FIP020.F2STYL Style,
                FIP020.F2CLR Color,
                FIP020.F2SIZE Size,
                FIP020.F2BACK Back,
                FIP020.F2SDSC StyleName,
                FIP020.F2CDSC ColorName,
                FIP020B.F2SLTH RollSize,
                FIP715.F7WGHTC FaceWt,
                FIP715.F7CMCH MachineNum,
                GIP030.G3DESC MachineDescription,
                FIP715.F7EPN EPN
            From data.FIP020 FIP020
            inner join FilterList f
                on FIP020.F2STYL = f.style
                and FIP020.F2CLR = f.color
                and FIP020.F2SIZE = f.size
                and FIP020.F2BACK = f.back
            inner join data.FIP020B FIP020B
                on FIP020.F2STYL = FIP020B.F2STYL
                and FIP020.F2CLR = FIP020B.F2CLR
                and FIP020.F2SIZE = FIP020B.F2SIZE
                and FIP020.F2BACK = FIP020B.F2BACK
            left outer join data.FIP712 FIP712
                on FIP020.F2STYL = FIP712.F7STYL
                and FIP020.F2SIZE = FIP712.F7SIZE
                and FIP712.F7MASTER = 'Y'
                and FIP712.F7APPVD = 'Y'
                and FIP712.F7PCODE = 'TFT'
            left outer join data.FIP715 FIP715
                on FIP020.F2STYL = FIP715.F7STYL
                and FIP020.F2SIZE = FIP715.F7SIZE
                and FIP712.F7SPEC# = FIP715.F7SPEC#
                and	FIP712.F7SPEC = FIP715.F7SPEC
            left outer join data.GIP030 GIP030
                on GIP030.G3MACH = FIP715.F7CMCH
		",
		Source = Sql.Database("TDG-DLT-IBMSQL", "CAMS", [Query=SQL]),
    #"Sorted Rows" = Table.Sort(Source,{{"PlanningGroup", Order.Ascending}, {"ColorGroup", Order.Ascending}, {"Style", Order.Ascending}, {"Color", Order.Ascending}}),
    #"Reordered Columns" = Table.ReorderColumns(#"Sorted Rows",{"PlanningGroup", "ColorGroup", "Style", "StyleName", "Color", "ColorName", "Size", "Back", "RollSize", "FaceWt", "MachineNum", "MachineDescription", "EPN"})
	in
		#"Reordered Columns"
