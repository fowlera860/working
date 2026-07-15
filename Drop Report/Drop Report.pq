let
    // Summarize Inventory (multiple lot rows) → On Hand
    InvGrouped = Table.Group(Inventory, {"Style", "Color", "Back", "Size"}, {{"On Hand", each List.Sum([Qty]), type number}}),

    // Assigned already one row per key — rename Qty → Assigned
    AssignedRenamed = Table.RenameColumns(Assigned, {{"Qty", "Assigned"}}),

    // Summarize Orders (multiple lot rows) → Orders
    OrdersGrouped = Table.Group(Orders, {"Style", "Color", "Back", "Size"}, {{"Orders", each List.Sum([Qty]), type number}}),

    // Left-join each source onto the position list
    JoinInv      = Table.NestedJoin(#"Position Report", {"Style","Color","Back","Size"}, InvGrouped,       {"Style","Color","Back","Size"}, "InvData", JoinKind.LeftOuter),
    ExpandInv    = Table.ExpandTableColumn(JoinInv,      "InvData",  {"On Hand"}),
    JoinAssigned = Table.NestedJoin(ExpandInv,           {"Style","Color","Back","Size"}, AssignedRenamed, {"Style","Color","Back","Size"}, "AssData", JoinKind.LeftOuter),
    ExpandAss    = Table.ExpandTableColumn(JoinAssigned, "AssData",  {"Assigned"}),
    JoinReserved = Table.NestedJoin(ExpandAss,           {"Style","Color","Back","Size"}, Reserved,        {"Style","Color","Back","Size"}, "ResData", JoinKind.LeftOuter),
    ExpandRes    = Table.ExpandTableColumn(JoinReserved, "ResData",  {"Reserved"}),
    JoinOrders   = Table.NestedJoin(ExpandRes,           {"Style","Color","Back","Size"}, OrdersGrouped,   {"Style","Color","Back","Size"}, "OrdData", JoinKind.LeftOuter),
    ExpandOrd    = Table.ExpandTableColumn(JoinOrders,   "OrdData",  {"Orders"}),

    // Treat missing matches as 0
    ReplaceNulls = Table.ReplaceValue(ExpandOrd, null, 0, Replacer.ReplaceValue, {"On Hand", "Assigned", "Reserved", "Orders"}),

    // Available = On Hand - Assigned - Reserved + Orders
    AddAvailable = Table.AddColumn(ReplaceNulls, "Available", each [On Hand] - [Assigned] - [Reserved] + [Orders], type number)
in
    AddAvailable
