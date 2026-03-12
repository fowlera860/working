let
    Source = Detail,
    #"Grouped Rows" = Table.Group(Source, {"Y7MCH#", "NP"}, {{"Orders", each Table.RowCount(_), Int64.Type}, {"Feet", each List.Sum([Y7FTSC]), type number}, {"Run Knots Standard", each List.Sum([#"Standard [RUN KNOTS THROUGH]"]), type nullable number}, {"Run Knots Actual", each List.Sum([#"Actual [RUN KNOTS THROUGH]"]), type nullable number}, {"Tufting Set Up Standard", each List.Sum([#"Standard [TUFTING SET UP]"]), type nullable number}, {"Tufting Set Up Actual", each List.Sum([#"Actual [TUFTING SET UP]"]), type nullable number}, {"Weight Check Standard", each List.Sum([#"Standard [WEIGHT CHECK]"]), type nullable number}, {"Weight Check Actual", each List.Sum([#"Actual [WEIGHT CHECK]"]), type nullable number}, {"Dye Header Standard", each List.Sum([#"Standard [DYE HEADER CHECK]"]), type nullable number}, {"Dye Header Actual", each List.Sum([#"Actual [DYE HEADER CHECK]"]), type nullable number}, {"Beam Waste Standard", each List.Sum([#"Standard [BEAM YARN WASTE]"]), type nullable number}, {"Beam Waste Actual", each List.Sum([#"Actual [BEAM YARN WASTE]"]), type nullable number}}),
    null2zero = Table.ReplaceValue(#"Grouped Rows",null,0,Replacer.ReplaceValue,{"Run Knots Standard", "Run Knots Actual", "Tufting Set Up Standard", "Tufting Set Up Actual", "Weight Check Standard", "Weight Check Actual", "Dye Header Standard", "Dye Header Actual", "Beam Waste Standard", "Beam Waste Actual"}),
    columnSpecs = {
        {"Run Knots Variance", each [Run Knots Standard]-[Run Knots Actual], type number},
        {"Tufting Set Up Variance", each [Tufting Set Up Standard]-[Tufting Set Up Actual], type number},
        {"Weight Check Variance", each [Weight Check Standard]-[Weight Check Actual], type number},
        {"Dye Header Variance", each [Dye Header Standard]-[Dye Header Actual], type number},
        {"Beam Waste Variance", each [Beam Waste Standard]-[Beam Waste Actual], type number},
        {"Total Standard", each [Run Knots Standard]+[Tufting Set Up Standard]+[Weight Check Standard]+[Dye Header Standard]+[Beam Waste Standard], type number},
        {"Total Actual", each [Run Knots Actual]+[Tufting Set Up Actual]+[Weight Check Actual]+[Dye Header Actual]+[Beam Waste Actual], type number},
        {"Total Variance", each [Total Standard]-[Total Actual], type number}
    },
    withVarianceAndTotals = List.Accumulate(columnSpecs, null2zero, (state, spec) => Table.AddColumn(state, spec{0}, spec{1}, spec{2})),
    ReorderedColumns = Table.ReorderColumns(withVarianceAndTotals,{"Y7MCH#", "NP", "Orders", "Feet", "Run Knots Standard", "Run Knots Actual", "Run Knots Variance", "Tufting Set Up Standard", "Tufting Set Up Actual", "Tufting Set Up Variance", "Weight Check Standard", "Weight Check Actual", "Weight Check Variance", "Dye Header Standard", "Dye Header Actual", "Dye Header Variance", "Beam Waste Standard", "Beam Waste Actual", "Beam Waste Variance", "Total Standard", "Total Actual", "Total Variance"})
in
    ReorderedColumns