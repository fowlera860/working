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
