// Directory
let
    Source = Excel.CurrentWorkbook(){[Name="Directory"]}[Content]{0}[Column1]

in
    Source

// InvRollCutoff
let
    Source = Excel.CurrentWorkbook(){[Name="InvRollCutoff"]}[Content]{0}[Column1]

in
    Source

// Planning_Groups
let
    Path = Directory & "Planning Groups.xlsx",
    Source = Excel.Workbook(File.Contents(Path), null, true),
    Planning_Groups_Table = Source{[Item="Planning_Groups",Kind="Table"]}[Data],
    #"Filtered Rows" = Table.SelectRows(Planning_Groups_Table, each true)
in
    #"Filtered Rows"

// Group_Filter_CTE
let
    Source = Planning_Groups,

    // Convert each row to a string like: ('9223','00310','1200','08','NG-Wool','00310')
    RowStrings = Table.ToRows(Source),
    QuotedRows = List.Transform(RowStrings, each "('" & Text.Combine(List.Transform(_, each Text.From(_)), "','") & "')"),

    // Combine all rows with commas and newlines
    ValuesBlock = Text.Combine(QuotedRows, ",#(lf)"),

    // Build full CTE text
    CTE = 
"WITH FilterList AS (
    SELECT *
    FROM (VALUES
" & ValuesBlock & "
    ) AS v(style, color, size, back, planningGroup, colorGroup)
)"
in
    CTE

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
                FIP020B.F2FCWT FaceWt,
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

// SalesForecast
let
    Source = Excel.Workbook(File.Contents("\\tdg-sa-file\Atmore\IE\Cycle Planner\SalesForecast.xlsx"), null, true),
    SalesForecast_Table = Source{[Item="SalesForecast",Kind="Table"]}[Data],
    RemoveColumns = Table.RemoveColumns(SalesForecast_Table,{"Week 1", "Week 2", "Week 3", "Week 4", "Week 5", "Week 6", "Week 7", "Week 8", "Week 9", "Week 10", "Week 11", "Week 12", "Week 13", 
        "Week 14", "Week 15", "Week 16", "Week 17", "Week 18", "Week 19", "Week 20", "Week 21", "Week 22", "Week 23", "Week 24", "Week 25", "Week 26", "Weekly Total", "Yards/Week", "WeeksToUse", 
        "Adjustment", "AdjustedSales", "Sales/Week", "Color Sales %", "ForecastOrSales"}),
    ChangeTypes = Table.TransformColumnTypes(
        RemoveColumns,
            {
                {"Style", type text}, 
                {"Size", type text}, 
                {"Back", type text}, 
                {"Color", type text}, 
                {"FC W 01", type number}, 
                {"FC W 02", type number}, 
                {"FC W 03", type number}, 
                {"FC W 04", type number}, 
                {"FC W 05", type number}, 
                {"FC W 06", type number}, 
                {"FC W 07", type number}, 
                {"FC W 08", type number}, 
                {"FC W 09", type number}, 
                {"FC W 10", type number}, 
                {"FC W 11", type number}, 
                {"FC W 12", type number}
            }
        ),
    InnerJoinGroups = Table.NestedJoin(ChangeTypes, {"Style", "Color", "Size", "Back"}, Planning_Groups, {"Style", "Color", "Size", "Back"}, "Planning_Groups", JoinKind.Inner),
    ExpandGroups = Table.ExpandTableColumn(InnerJoinGroups, "Planning_Groups", {"PlanGroup", "ColorGroup"}, {"PlanGroup", "ColorGroup"})
in
    ExpandGroups

// CyclePlannerPrebuild
let
    Source = Product_Specs,
    MergedBackorders = Table.NestedJoin(Source, {"Style", "Color", "Size", "Back"}, MillOrderProductionAssignment, {"Style", "Color", "Size", "Back"}, "Backorders", JoinKind.LeftOuter),
    AddedAssigned = Table.AddColumn(MergedBackorders, "AsgQty", each List.Sum([Backorders][PendingProd])),
    AddedReserves = Table.AddColumn(AddedAssigned, "ReservedQty", each List.Sum([Backorders][RsvQty])),
    MergedMillOrders = Table.NestedJoin(AddedReserves, {"Style", "Color", "Size", "Back"}, UnassignedMillOrders, {"Style", "Color", "Size", "Back"}, "UnassignedMillOrders", JoinKind.LeftOuter),
    AddedBOs =
    Table.AddColumn(
        MergedMillOrders,
        "B/O",
        each
            let
                t = Table.AddColumn(
                        [UnassignedMillOrders],
                        "Calc",
                        (r) => if r[UOM] = "RL" then [RollSize] * r[Qty] else r[Qty],
                        type number
                    )
            in
                List.Sum(t[Calc])
    ),
    MergedInventory = Table.NestedJoin(AddedBOs, {"Style", "Color", "Size", "Back"}, Inventory, {"Style", "Color", "Size", "Back"}, "Inventory", JoinKind.LeftOuter),
    AddedOnHand = Table.AddColumn(MergedInventory, "OnHand", each List.Sum([Inventory][Feet])),
    MergedForecast = Table.NestedJoin(AddedOnHand, {"Style", "Color", "Size", "Back"}, SalesForecast, {"Style", "Color", "Size", "Back"}, "SalesForecast", JoinKind.LeftOuter),
    MergedProductions = Table.NestedJoin(MergedForecast, {"Style", "Color", "Size", "Back"}, TimePhaseProductionOrders, {"Style", "Color", "Size", "Back"}, "ProductionOrders", JoinKind.LeftOuter),
    MergedShipments = Table.NestedJoin(MergedProductions, {"Style", "Color", "Size", "Back"}, TimePhaseShipments, {"Style", "Color", "Size", "Back"}, "Shipments", JoinKind.LeftOuter),
    #"Replaced Value" = Table.ReplaceValue(MergedShipments,null,0,Replacer.ReplaceValue,{"OnHand"}),
    AddedTimePhase = Table.AddColumn(#"Replaced Value", "TimePhase", each 
        fnTimePhasedInventory(
            [OnHand],
            [SalesForecast],
            [ProductionOrders],
            [Shipments]
        )
    ),
    ExpandedTimePhase = Table.ExpandRecordColumn(AddedTimePhase, "TimePhase", {"Week 01", "Week 02", "Week 03", "Week 04", "Week 05", "Week 06", "Week 07", "Week 08", "Week 09", "Week 10", "Week 11", "Week 12"})
in
    ExpandedTimePhase

// ProductionOrders
let
    SQL = Group_Filter_CTE & "
        SELECT 
			PPP010.PPSTYL AS Style,
			PPP010.PPCLR AS Color,
			PPP010.PPSIZE AS Size,
			PPP010.PPBACK AS Back,
			PPP010.PPCTL# as ProdNum,
			PPP010.PPOQTY as FtOrdered,
			PPP010.PPJULN+366 as ProdDate, 
			PPP010.PPPRJL+366 as PromDate, 
			PPP010.PPWHSE as WH
		FROM CAMS.DATA.PPP010 PPP010
		WHERE PPCOMP <> 'Y'
		  AND EXISTS (
				SELECT 1
				FROM FilterList f
				WHERE 
					f.style = PPP010.PPSTYL
					AND f.color = PPP010.PPCLR
					AND f.size = PPP010.PPSIZE
					AND f.back = PPP010.PPBACK
			)
		  AND PPP010.PPSEQ# = (
				SELECT MAX(PPSEQ#)
				FROM CAMS.DATA.PPP010 p2
				WHERE p2.PPSTYL = PPP010.PPSTYL
				  AND p2.PPCLR = PPP010.PPCLR
				  AND p2.PPSIZE = PPP010.PPSIZE
				  AND p2.PPBACK = PPP010.PPBACK
			)

		",
	Source = Sql.Database("TDG-DLT-IBMSQL", "CAMS", [Query=SQL]),
    ChangeType = Table.TransformColumnTypes(Source,{{"ProdDate", type date},{"PromDate", type date}}),
    #"Sorted Rows" = Table.Sort(ChangeType,{{"ProdDate", Order.Ascending}}),
	#"Added WeeksOut" = Table.AddColumn(
		#"Sorted Rows",
		"WeeksOut",
		each let
			today = Date.From(DateTime.LocalNow()),
			currentWeekSunday = Date.AddDays(today, -Date.DayOfWeek(today, Day.Sunday)),
			weekDiff = Number.RoundDown(Duration.Days([PromDate] - currentWeekSunday) / 7)
		in
			if weekDiff <= 0 then 1 else weekDiff,
		Int64.Type
	)
in
    #"Added WeeksOut"

// TimePhaseProductionOrders
let
    Source = ProductionOrders,
    #"Removed Columns" = Table.RemoveColumns(Source,{"ProdNum", "ProdDate", "PromDate", "WH"}),

    // Keep only weeks 1-13
    Filtered = Table.SelectRows(#"Removed Columns", each [WeeksOut] >= 1 and [WeeksOut] <= 13),

   
    // Create a list of all weeks 1..13 as text "Week 01".."Week 13"
    AllWeeksText = List.Transform({1..13}, each "PD W " & Text.PadStart(Text.From(_), 2, "0")),

    // Create a table with all weeks and a dummy value
    DummyRowsTemp = Table.FromList({1..13}, Splitter.SplitByNothing(), {"WeeksOut"}),
    DummyRows = Table.AddColumn(DummyRowsTemp, "FtOrdered", each 0, Int64.Type),

    // Combine dummy rows with real data
    Combined = Table.Combine({Filtered, DummyRows}),

    // Format all WeeksOut values once as "Week 01".."Week 13"
    CombinedFormatted = Table.TransformColumns(
        Combined,
        {{"WeeksOut", each "PD W " & Text.PadStart(Text.From(_), 2, "0"), type text}}
    ),

    // Pivot the table
    #"Pivoted Column" = Table.Pivot(
        CombinedFormatted,
        List.Distinct(CombinedFormatted[WeeksOut]),
        "WeeksOut",
        "FtOrdered",
        List.Sum
    ),

    // Replace any nulls with 0
    #"Replaced Nulls" = Table.ReplaceValue(
        #"Pivoted Column",
        null,
        0,
        Replacer.ReplaceValue,
        Table.ColumnNames(#"Pivoted Column")
    ),

    // Reorder columns Week 01..Week 13
    #"Reordered Columns" = Table.ReorderColumns(
        #"Replaced Nulls",
        AllWeeksText
    ),
    #"Filtered Rows" = Table.SelectRows(#"Reordered Columns", each ([Style] <> 0))
in
    #"Filtered Rows"

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

// CombinedOutgoing
let
    Source = Table.Combine({MillOrderRollAssignment, UnassignedMillOrders, MillOrderProductionAssignment}),
    #"Reordered Columns" = Table.ReorderColumns(Source,{"Style", "Color", "Size", "Back", "Src", "OrdNum", "OrdLine", "Qty", "UOM", "PromDt", "Product_Specs.RollSize", "LF", "ProdOrder", "AsgQty", "RsvQty", "PendingProd"}),
	#"Added WeeksOut" = Table.AddColumn(
		#"Reordered Columns",
		"WeeksOut",
		each let
			today = Date.From(DateTime.LocalNow()),
			currentWeekSunday = Date.AddDays(today, -Date.DayOfWeek(today, Day.Sunday)),
			weekDiff = Number.RoundDown(Duration.Days([PromDt] - currentWeekSunday) / 7)
		in
			if weekDiff <= 0 then 1 else weekDiff,
		Int64.Type
	)
in
    #"Added WeeksOut"

// TimePhaseShipments
let
    Source = CombinedOutgoing,
    #"Removed Columns1" = Table.RemoveColumns(Source,{"Src", "OrdNum", "OrdLine", "UOM", "PromDt", "Product_Specs.RollSize", "LF", "ProdOrder", "AsgQty", "RsvQty", "PendingProd"}),
    // Keep only weeks 1-13
    Filtered = Table.SelectRows(#"Removed Columns1", each [WeeksOut] >= 1 and [WeeksOut] <= 13),
    #"Renamed Columns" = Table.RenameColumns(Filtered,{{"Qty", "FtToShip"}}),

   
    // Create a list of all weeks 1..13 as text "Week 01".."Week 13"
    AllWeeksText = List.Transform({1..13}, each "SH W " & Text.PadStart(Text.From(_), 2, "0")),

    // Create a table with all weeks and a dummy value
    DummyRowsTemp = Table.FromList({1..13}, Splitter.SplitByNothing(), {"WeeksOut"}),
    DummyRows = Table.AddColumn(DummyRowsTemp, "FtToShip", each 0, Int64.Type),

    // Combine dummy rows with real data
    Combined = Table.Combine({#"Renamed Columns", DummyRows}),

    // Format all WeeksOut values once as "Week 01".."Week 13"
    CombinedFormatted = Table.TransformColumns(
        Combined,
        {{"WeeksOut", each "SH W " & Text.PadStart(Text.From(_), 2, "0"), type text}}
    ),

    // Pivot the table
    #"Pivoted Column" = Table.Pivot(
        CombinedFormatted,
        List.Distinct(CombinedFormatted[WeeksOut]),
        "WeeksOut",
        "FtToShip",
        List.Sum
    ),

    // Replace any nulls with 0
    #"Replaced Nulls" = Table.ReplaceValue(
        #"Pivoted Column",
        null,
        0,
        Replacer.ReplaceValue,
        Table.ColumnNames(#"Pivoted Column")
    ),

    // Reorder columns Week 01..Week 13
    #"Reordered Columns" = Table.ReorderColumns(
        #"Replaced Nulls",
        AllWeeksText
    ),
    #"Filtered Rows" = Table.SelectRows(#"Reordered Columns", each ([Style] <> 0))
in
    #"Filtered Rows"

// fnTimePhasedInventory
(onHand as number, forecastTable as table, pdTable as table, shTable as table) as record =>
let
    // Weeks 01..12
    weeks = List.Transform({1..12}, each Text.PadStart(Text.From(_), 2, "0")),
    fcColumns = List.Transform(weeks, each "FC W " & _),
    pdColumns = List.Transform(weeks, each "PD W " & _),
    shColumns = List.Transform(weeks, each "SH W " & _),

    // Get first row of forecast and planned delivery tables
    forecastRecord = 
        if forecastTable <> null and Table.RowCount(forecastTable) > 0
        then Table.FirstN(forecastTable, 1){0}
        else null,

    pdRecord = 
        if pdTable <> null and Table.RowCount(pdTable) > 0
        then Table.FirstN(pdTable, 1){0}
        else null,

    shRecord = 
        if pdTable <> null and Table.RowCount(shTable) > 0
        then Table.FirstN(shTable, 1){0}
        else null,

    // Extract numeric values for each week
    fcValues = List.Transform(fcColumns, each 
        let raw = try Record.Field(forecastRecord, _) otherwise null
        in if Value.Is(raw, type number) then raw else 0
    ),
    pdValues = List.Transform(pdColumns, each 
        let raw = try Record.Field(pdRecord, _) otherwise null
        in if Value.Is(raw, type number) then raw else 0
    ),
    shValues = List.Transform(shColumns, each 
        let raw = try Record.Field(shRecord, _) otherwise null
        in if Value.Is(raw, type number) then raw else 0
    ),

    // Cumulative inventory calculation
    cumulative = List.Generate(
        () => [i=0, inv=onHand],
        each [i] < List.Count(fcValues),
        each [
            inv = [inv] - fcValues{[i]} + pdValues{[i]} - + shValues{[i]},
            i = [i] + 1
        ],
        each [inv]
    ),

    // Convert to record
    result = Record.FromList(cumulative, List.Transform(weeks, each "Week " & _))
in
    result