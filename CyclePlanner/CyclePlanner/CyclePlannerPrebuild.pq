let
    Source = Csv.Document(File.Contents("\\tdg-sa-file\Atmore\IE\Cycle Planner\exports\cycle_planner_prebuild.csv"),[Delimiter=",", Columns=71, Encoding=1252, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"PlanningGroup", type text}, {"ColorGroup_x", type text}, {"Style", type text}, {"Color", type text}, {"Size", type text}, {"Back", type text}, {"StyleName", type text}, {"ColorName", type text},
        {"RollSize", Int64.Type}, {"FaceWt", type number}, {"MachineNum", type text}, {"MachineDescription", type text}, {"EPN", Int64.Type},
        {"AsgQty", Int64.Type}, {"ReservedQty", Int64.Type}, {"B/O", type number}, {"OnHand", Int64.Type},
        {"FC W 01", type number}, {"FC W 02", type number}, {"FC W 03", type number}, {"FC W 04", type number}, {"FC W 05", type number}, {"FC W 06", type number},
        {"FC W 07", type number}, {"FC W 08", type number}, {"FC W 09", type number}, {"FC W 10", type number}, {"FC W 11", type number}, {"FC W 12", type number},
        {"PlanGroup", type text}, {"ColorGroup_y", type text},
        {"PD W 01", type number}, {"PD W 02", type number}, {"PD W 03", type number}, {"PD W 04", type number}, {"PD W 05", type number}, {"PD W 06", type number},
        {"PD W 07", type number}, {"PD W 08", type number}, {"PD W 09", type number}, {"PD W 10", type number}, {"PD W 11", type number}, {"PD W 12", type number},
        {"SH W 01", type number}, {"SH W 02", type number}, {"SH W 03", type number}, {"SH W 04", type number}, {"SH W 05", type number}, {"SH W 06", type number},
        {"SH W 07", type number}, {"SH W 08", type number}, {"SH W 09", type number}, {"SH W 10", type number}, {"SH W 11", type number}, {"SH W 12", type number},
        {"Week 01", type number}, {"Week 02", type number}, {"Week 03", type number}, {"Week 04", type number}, {"Week 05", type number}, {"Week 06", type number},
        {"Week 07", type number}, {"Week 08", type number}, {"Week 09", type number}, {"Week 10", type number}, {"Week 11", type number}, {"Week 12", type number},
        {"Avg Forecast", type number}, {"Total Production", type number}
    }),
    #"Renamed Columns" = Table.RenameColumns(#"Changed Type",{{"ColorGroup_x", "ColorGroup"}}),
    #"Reordered Columns" = Table.ReorderColumns(#"Renamed Columns",{
        "PlanningGroup","ColorGroup","Style","StyleName","Color","ColorName","Size","Back","RollSize","FaceWt",
        "MachineNum","MachineDescription","EPN","Avg Forecast","AsgQty","ReservedQty","B/O","Total Production","OnHand",
        "FC W 01","FC W 02","FC W 03","FC W 04","FC W 05","FC W 06","FC W 07","FC W 08","FC W 09","FC W 10","FC W 11","FC W 12",
        "PlanGroup","ColorGroup_y",
        "PD W 01","PD W 02","PD W 03","PD W 04","PD W 05","PD W 06","PD W 07","PD W 08","PD W 09","PD W 10","PD W 11","PD W 12",
        "SH W 01","SH W 02","SH W 03","SH W 04","SH W 05","SH W 06","SH W 07","SH W 08","SH W 09","SH W 10","SH W 11","SH W 12",
        "Week 01","Week 02","Week 03","Week 04","Week 05","Week 06","Week 07","Week 08","Week 09","Week 10","Week 11","Week 12"
    }),
    #"Removed Columns" = Table.RemoveColumns(#"Reordered Columns",{"FC W 01", "FC W 02", "FC W 03", "FC W 04", "FC W 05", "FC W 06", "FC W 07", "FC W 08", "FC W 09", "FC W 10", "FC W 11", "FC W 12", "PlanGroup", "ColorGroup_y", "PD W 01", "PD W 02", "PD W 03", "PD W 04", "PD W 05", "PD W 06", "PD W 07", "PD W 08", "PD W 09", "PD W 10", "PD W 11", "PD W 12", "SH W 01", "SH W 02", "SH W 03", "SH W 04", "SH W 05", "SH W 06", "SH W 07", "SH W 08", "SH W 09", "SH W 10", "SH W 11", "SH W 12", "PD W 13", "SH W 13"}),
    #"Replaced Value" = Table.ReplaceValue(#"Removed Columns",null,0,Replacer.ReplaceValue,{"AsgQty", "ReservedQty", "B/O"}),
    AddedPosition = Table.AddColumn(#"Replaced Value", "Position", each if [Avg Forecast] = 0 then 0 else 
([OnHand]+[Total Production]-[#"B/O"]-[ReservedQty]-[AsgQty])/[Avg Forecast]),
    Grouped = Table.Group(AddedPosition, {"PlanningGroup", "ColorGroup"}, {{"Rows", each _, type table}}),
    AddedRecommendations = Table.AddColumn(
        Grouped,
        "Recs",
        each
            let
                GroupTable = [Rows],
                WithIndex = Table.AddIndexColumn(GroupTable, "RowId", 0, 1, Int64.Type),
                Records = Table.ToRecords(WithIndex),
                RecordsWithRec = List.Transform(Records, each Record.AddField(_, "Recommened", 0)),
                ComputeUpdated = (recs as list) as list =>
                    List.Transform(
                        recs,
                        (r) =>
                            let
                                available = r[OnHand] + r[Total Production] - r[#"B/O"] - r[ReservedQty] - r[AsgQty] + r[Recommened],
                                updated = if r[Avg Forecast] = 0 then 0 else available / r[Avg Forecast]
                            in
                                Record.AddField(Record.RemoveFields(r, {"Updated Position"}, MissingField.Ignore), "Updated Position", updated)
                    ),
                Eligible = (recs as list) as list => List.Select(recs, each _[Avg Forecast] <> 0),
                Init = ComputeUpdated(RecordsWithRec),
                MinPosition =
                    let
                        e = Eligible(Init)
                    in
                        if List.IsEmpty(e) then null else List.Min(List.Transform(e, each _[Position])),
                MaxIterations = 10000,
                FinalRecs =
                    if MinPosition = null or MinPosition >= MinimumWeeks then
                        Init
                    else
                        let
                            InitialEligible = Eligible(Init),
                            InitialMinUpdated = if List.IsEmpty(InitialEligible) then null else List.Min(List.Transform(InitialEligible, each _[Updated Position])),
                            Seed = [Recs = Init, Iter = 0, MinUpdated = InitialMinUpdated],
                            Step = (state as record) as record =>
                                let
                                    e = Eligible(state[Recs]),
                                    minUpdated = List.Min(List.Transform(e, each _[Updated Position])),
                                    minRec = List.First(List.Select(e, each _[Updated Position] = minUpdated)),
                                    bumped =
                                        List.Transform(
                                            state[Recs],
                                            each if _[RowId] = minRec[RowId]
                                            then Record.TransformFields(_, {{"Recommened", (v) => v + _[RollSize]}})
                                            else _
                                        ),
                                    recomputed = ComputeUpdated(bumped),
                                    e2 = Eligible(recomputed),
                                    newMin = if List.IsEmpty(e2) then null else List.Min(List.Transform(e2, each _[Updated Position]))
                                in
                                    [Recs = recomputed, Iter = state[Iter] + 1, MinUpdated = newMin],
                            Generated =
                                List.Generate(
                                    () => Seed,
                                    (state) => state[Iter] < MaxIterations and state[MinUpdated] <> null and state[MinUpdated] <= TargetWeeks,
                                    (state) => Step(state),
                                    (state) => Step(state)
                                ),
                            Result = if List.IsEmpty(Generated) then Seed else List.Last(Generated)
                        in
                            Result[Recs]
            in
                Table.RemoveColumns(Table.FromRecords(FinalRecs), {"RowId"})
    ),
    ExpandedRecommendations = Table.ExpandTableColumn(
        AddedRecommendations,
        "Recs",
        List.RemoveItems(Table.ColumnNames(AddedPosition), {"PlanningGroup", "ColorGroup"}) & {"Recommened", "Updated Position"}
    ),
    AddedRecommendedLbs = Table.AddColumn(
        ExpandedRecommendations,
        "RecommendedLbs",
        each [Recommened] * [FaceWt] / 16
    )
in
    AddedRecommendedLbs