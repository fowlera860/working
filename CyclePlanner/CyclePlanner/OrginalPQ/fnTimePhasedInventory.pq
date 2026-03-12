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
