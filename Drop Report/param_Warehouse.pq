// Param_Warehouse
// Comma-delimited, single-quoted warehouse codes for SQL IN clause
// Edit the list below to match the warehouses you want to filter on
let
    Warehouses = {"01", "02"},
    Quoted = List.Transform(Warehouses, each "'" & _ & "'"),
    Result = Text.Combine(Quoted, ",")
in
    Result
