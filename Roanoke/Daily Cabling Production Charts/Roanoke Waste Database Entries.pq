let
    BaseUrl = "https://dixiegroup.sharepoint.com/sites/Candlewick/",
    ListId = "5970a8de-9025-4ed1-a6db-e604521d9f0e",
    StartDateText = Date.ToText(StartDate, "yyyy-MM-dd"),
    EndDateText = Date.ToText(EndDate, "yyyy-MM-dd"),
    ODataUrl = BaseUrl & "/_api/web/lists(guid'" & ListId & "')/items?" &
        "$select=Title,field_0,field_2,field_3,field_4,field_5,field_6,field_7,field_8,field_9" &
        "&$filter=field_0 ge datetime'" & StartDateText & "T00:00:00Z' and field_0 le datetime'" & EndDateText & "T23:59:59Z'",
    Source = OData.Feed(ODataUrl, null, [Implementation="2.0"]),
    #"Renamed Columns1" = Table.RenameColumns(Source,{{"Title", "Shift"}, {"field_2", "Lbs"}, {"field_3", "Mch"}, {"field_4", "lot"}, {"field_5", "Pkgs"}, {"field_6", "Reason Cat"}, {"field_7", "Reason  Code"}, {"field_8", "User"}, {"field_9", "DateTime"}, {"field_0", "Date"}}),
    #"Changed Type" = Table.TransformColumnTypes(#"Renamed Columns1",{{"Date", type date}}),
    #"Merged Queries" = Table.NestedJoin(#"Changed Type", {"Mch"}, #"Roanoke Waste Database Machines", {"Mch"}, "Roanoke Waste Database Machines", JoinKind.LeftOuter),
    #"Expanded Roanoke Waste Database Machines" = Table.ExpandTableColumn(#"Merged Queries", "Roanoke Waste Database Machines", {"MchType"}, {"MchType"})
in
    #"Expanded Roanoke Waste Database Machines"