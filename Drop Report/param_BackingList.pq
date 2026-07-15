// param_BackingList
// Unique Back codes from Position Report, formatted for SQL IN clause
let
    Backings = List.Distinct(List.Transform(Table.Column(#"Position Report", "Back"), each Text.Trim(_))),
    Quoted = List.Transform(Backings, each "'" & _ & "'"),
    Result = Text.Combine(Quoted, ",")
in
    Result
