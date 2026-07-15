// param_SizeList
// Unique Size codes from Position Report, formatted for SQL IN clause
let
    Sizes = List.Distinct(List.Transform(Table.Column(#"Position Report", "Size"), each Text.Trim(_))),
    Quoted = List.Transform(Sizes, each "'" & _ & "'"),
    Result = Text.Combine(Quoted, ",")
in
    Result
