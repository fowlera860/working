let
    Standard = Standard,
    Waste = #"Actual Waste",
    Categories = {"RUN KNOTS THROUGH","TUFTING SET UP","WEIGHT CHECK","DYE HEADER CHECK","BEAM YARN WASTE"},
    WasteSelected = Table.SelectColumns(Waste,{"Y7MCH#","W3TORD","Y7FTSC","Y7STYL","Q2DESC","W3LBS"}),
    WastePivot = Table.Pivot(WasteSelected, Categories, "Q2DESC", "W3LBS", List.Sum),
    RenamedActual = Table.RenameColumns(WastePivot, List.Transform(Categories, each {_, "Actual [" & _ & "]"})),
    StandardRenamedMachine = Table.RenameColumns(Standard, {{"Machine #","Y7MCH#"}}),
    StandardRenamed = Table.RenameColumns(StandardRenamedMachine, List.Transform(Categories, each {_, "Standard [" & _ & "]"})),
    Joined = Table.Join(RenamedActual, {"Y7MCH#"}, StandardRenamed, {"Y7MCH#"}, JoinKind.LeftOuter),
    Reordered = Table.ReorderColumns(Joined,{"Y7MCH#","W3TORD","Y7FTSC","Y7STYL",
        "Standard [RUN KNOTS THROUGH]","Actual [RUN KNOTS THROUGH]",
        "Standard [TUFTING SET UP]","Actual [TUFTING SET UP]",
        "Standard [WEIGHT CHECK]","Actual [WEIGHT CHECK]",
        "Standard [DYE HEADER CHECK]","Actual [DYE HEADER CHECK]",
        "Standard [BEAM YARN WASTE]","Actual [BEAM YARN WASTE]"})
in
    Reordered


data structure:

    Waste = Table(DATE	Y7MCH#	W3WHSE	W3TORD	Y7FTSC	Y7STYL	W3LOT#	W3YNID	W3TYPE	W3YCLR	W3REAS	Q2DESC	W3USER	W3LBS)
    Standard = Table(Machine #	Gauge	Bm/Crl	N/P	RUN KNOTS THROUGH	TUFTING SET UP	WEIGHT CHECK	DYE HEADER CHECK	BEAM YARN WASTE)

    in Waste Q2DESC will always equal one of these (matchs columns in Standard):
        RUN KNOTS THROUGH
    	TUFTING SET UP
        WEIGHT CHECK
        DYE HEADER CHECK
        BEAM YARN WASTE
      