let
    sDate  = Excel.CurrentWorkbook(){[Name="start_Date"]}[Content]{0}[Column1],
    eDate =  Excel.CurrentWorkbook(){[Name="end_Date"]}[Content]{0}[Column1],
    sDateText = DateTime.ToText(DateTime.From(sDate), [Format="yyyy-MM-ddTHH:mm:ss", Culture="en-US"]),
    eDateText = DateTime.ToText(DateTime.From(eDate), [Format="yyyy-MM-ddTHH:mm:ss", Culture="en-US"]),
    Url = "https://dixiegroup.sharepoint.com/sites/Candlewick/_api/web/lists(guid'5970a8de-9025-4ed1-a6db-e604521d9f0e')/items"
        & "?$select=Title,field_2,field_3,field_4,field_5,field_6,field_7,field_8,field_9,Initials,SubReason"
        & "&$filter=field_9 ge datetime'" & sDateText & "' and field_9 le datetime'" & eDateText & "'",
    RawSource = try OData.Feed(Url, null, [ODataVersion=3]) otherwise null,
    EmptyTable = #table(
        type table [Shift=text, Lbs=number, Machine=text, Lot=text, Packages=number, #"Reason Cat"=text, #"Reason Code"=text, User=text, DateTime=datetime, Initials=text, SubReason=text],
        {}
    ),
    Source = if RawSource = null or not Table.HasColumns(RawSource, "Title") then EmptyTable else
        Table.RenameColumns(RawSource,{{"Title", "Shift"}, {"field_2", "Lbs"}, {"field_3", "Machine"}, {"field_4", "Lot"}, {"field_5", "Packages"}, {"field_6", "Reason Cat"}, {"field_7", "Reason Code"}, {"field_8", "User"}, {"field_9", "DateTime"}})
in
    Source