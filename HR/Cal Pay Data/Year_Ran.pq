let
    Source = #"EE Data",
    #"FY " = Source{0}[#"FY "]
in
    #"FY "