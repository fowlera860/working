Sub GenerateCyclePlanner()
    On Error GoTo errHndl
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets("Yarn Cycle Planner")

    Dim sourceTable As ListObject
    Set sourceTable = ThisWorkbook.Sheets("CyclePlannerPrebuild").ListObjects("CyclePlannerPrebuild")
    'Set sourceTable = ThisWorkbook.Sheets("CyclePlannerPrebuild (2)").ListObjects("CyclePlannerPrebuild__2")

    Dim outputTable As ListObject
    Set outputTable = ws.ListObjects("CyclePlannerOutput")

    ' Find CyclePlannerPrebuildGroup table (Python group-level aggregates)
    Dim groupTable As ListObject
    Dim groupWs As Worksheet
    For Each groupWs In ThisWorkbook.Worksheets
        Dim groupTbl As ListObject
        For Each groupTbl In groupWs.ListObjects
            If groupTbl.Name = "CyclePlannerPrebuildGroup" Then
                Set groupTable = groupTbl
                Exit For
            End If
        Next groupTbl
        If Not groupTable Is Nothing Then Exit For
    Next groupWs

    ' Clear output table first
    If outputTable.ListRows.Count > 0 Then outputTable.DataBodyRange.Delete

    Dim SelectedGroup As String
    SelectedGroup = ws.Range("D2").Value  ' get group to filter by

    Dim arr() As Variant
    Dim r As Long
    ReDim arr(1 To sourceTable.ListRows.Count, 1 To sourceTable.ListColumns.Count)
    r = 0

    Dim i As Long
    Dim j As Long
    For i = 1 To sourceTable.ListRows.Count
        If sourceTable.DataBodyRange.Cells(i, 1).Value = SelectedGroup Then
            r = r + 1
            For j = 1 To sourceTable.ListColumns.Count
                arr(r, j) = sourceTable.DataBodyRange.Cells(i, j).Value
            Next j
        End If
    Next i

    ' Build output rows: data rows from SKU source, totals from CyclePlannerPrebuildGroup
    Dim outputList As Collection
    Set outputList = New Collection

    Dim prevValue As Variant
    Dim currentValue As Variant
    Dim c As Long
    Dim idx As Long
    prevValue = ""

    For idx = 1 To r
        currentValue = arr(idx, 2)  ' ColorGroup column

        ' When color group changes, insert a totals row then a blank spacer
        If prevValue <> "" And currentValue <> prevValue Then
            Dim totalsRow() As Variant
            ReDim totalsRow(1 To 1, 1 To UBound(arr, 2))
            For c = 1 To UBound(arr, 2)
                totalsRow(1, c) = ""
            Next c
            totalsRow(1, 1) = arr(idx - 1, 1)
            totalsRow(1, 2) = "Total " & prevValue

            ' Look up all metric and rec-week values from the group table
            If Not groupTable Is Nothing Then
                Call FillTotalsFromGroupTable(totalsRow, groupTable, sourceTable, _
                    arr(idx - 1, 1), prevValue)
            End If

            outputList.Add totalsRow

            ' Blank spacer row between color groups
            Dim spacerRow() As Variant
            ReDim spacerRow(1 To 1, 1 To UBound(arr, 2))
            For c = 1 To UBound(arr, 2)
                spacerRow(1, c) = ""
            Next c
            outputList.Add spacerRow
        End If

        ' Write the individual SKU data row as-is
        Dim dataRow() As Variant
        ReDim dataRow(1 To 1, 1 To UBound(arr, 2))
        For c = 1 To UBound(arr, 2)
            dataRow(1, c) = arr(idx, c)
        Next c
        outputList.Add dataRow

        prevValue = currentValue
    Next idx

    If r > 0 Then
        ' Final color group totals row
        Dim finalTotalsRow() As Variant
        ReDim finalTotalsRow(1 To 1, 1 To UBound(arr, 2))
        For c = 1 To UBound(arr, 2)
            finalTotalsRow(1, c) = ""
        Next c
        finalTotalsRow(1, 1) = arr(r, 1)
        finalTotalsRow(1, 2) = "Total " & prevValue

        If Not groupTable Is Nothing Then
            Call FillTotalsFromGroupTable(finalTotalsRow, groupTable, sourceTable, _
                arr(r, 1), prevValue)
        End If

        outputList.Add finalTotalsRow

        ' Grand total row: sums all color groups for the selected planning group
        Dim grandTotalsRow() As Variant
        ReDim grandTotalsRow(1 To 1, 1 To UBound(arr, 2))
        For c = 1 To UBound(arr, 2)
            grandTotalsRow(1, c) = ""
        Next c
        grandTotalsRow(1, 2) = "Grand Total"

        If Not groupTable Is Nothing Then
            Call FillGrandTotalFromGroupTable(grandTotalsRow, groupTable, sourceTable, SelectedGroup)
        End If

        outputList.Add grandTotalsRow
    End If

    ' Write collected rows to output table
    Dim totalRows As Long
    totalRows = outputList.Count

    Dim finalArr() As Variant
    ReDim finalArr(1 To totalRows, 1 To UBound(arr, 2))

    For i = 1 To totalRows
        For j = 1 To UBound(arr, 2)
            finalArr(i, j) = outputList(i)(1, j)
        Next j
    Next i

    If totalRows > 0 Then
        outputTable.Resize outputTable.Range.Resize(totalRows + 1, sourceTable.ListColumns.Count)
        outputTable.DataBodyRange.Value = finalArr
    End If
    Exit Sub
errHndl:
    Application.EnableEvents = True
    MsgBox Err.Description
End Sub

' Fills a totals row by looking up PlanningGroup + ColorGroup in CyclePlannerPrebuildGroup.
' Each column in the group table is matched by name to the source table's column index.
Private Sub FillTotalsFromGroupTable(ByRef rowArr() As Variant, _
                                     ByVal grpTbl As ListObject, _
                                     ByVal srcTbl As ListObject, _
                                     ByVal planningGroup As String, _
                                     ByVal colorGroup As String)
    Dim grpCol As ListColumn
    Dim outColIdx As Long
    For Each grpCol In grpTbl.ListColumns
        If grpCol.Name <> "PlanningGroup" And grpCol.Name <> "ColorGroup" Then
            outColIdx = GetColIdx(srcTbl, grpCol.Name)
            If outColIdx > 0 And outColIdx <= UBound(rowArr, 2) Then
                rowArr(1, outColIdx) = WorksheetFunction.SumIfs( _
                    grpCol.DataBodyRange, _
                    grpTbl.ListColumns("PlanningGroup").DataBodyRange, planningGroup, _
                    grpTbl.ListColumns("ColorGroup").DataBodyRange, colorGroup)
            End If
        End If
    Next grpCol
End Sub

' Fills the grand total row by summing all ColorGroups for the planning group
' in CyclePlannerPrebuildGroup. Column matching is by name.
Private Sub FillGrandTotalFromGroupTable(ByRef rowArr() As Variant, _
                                         ByVal grpTbl As ListObject, _
                                         ByVal srcTbl As ListObject, _
                                         ByVal planningGroup As String)
    Dim grpCol As ListColumn
    Dim outColIdx As Long
    For Each grpCol In grpTbl.ListColumns
        If grpCol.Name <> "PlanningGroup" And grpCol.Name <> "ColorGroup" Then
            outColIdx = GetColIdx(srcTbl, grpCol.Name)
            If outColIdx > 0 And outColIdx <= UBound(rowArr, 2) Then
                rowArr(1, outColIdx) = WorksheetFunction.SumIfs( _
                    grpCol.DataBodyRange, _
                    grpTbl.ListColumns("PlanningGroup").DataBodyRange, planningGroup)
            End If
        End If
    Next grpCol
End Sub

' Returns the 1-based column index of colName in tbl, or 0 if not found.
Private Function GetColIdx(tbl As ListObject, colName As String) As Long
    On Error Resume Next
    GetColIdx = tbl.ListColumns(colName).Index
    On Error GoTo 0
End Function


