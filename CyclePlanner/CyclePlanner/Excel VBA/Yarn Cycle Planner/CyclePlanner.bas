Sub GenerateCyclePlanner()
    On Error GoTo errHndl
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets("Yarn Cycle Planner")
    
    Dim sourceTable As ListObject
    Set sourceTable = ThisWorkbook.Sheets("CyclePlannerPrebuild").ListObjects("CyclePlannerPrebuild")
    'Set sourceTable = ThisWorkbook.Sheets("CyclePlannerPrebuild (2)").ListObjects("CyclePlannerPrebuild__2")
    
    Dim outputTable As ListObject
    Set outputTable = ws.ListObjects("CyclePlannerOutput")

    ' Load Recommend_Week parameter (Power Query scalar loaded as named range)
    Dim recWeek As Long
    recWeek = CLng(ThisWorkbook.Names("Recommend_Week").RefersToRange.Value)

    ' Find yarn_order_recommendations table
    Dim recTable As ListObject
    Dim recWs As Worksheet
    For Each recWs In ThisWorkbook.Worksheets
        Dim recTbl As ListObject
        For Each recTbl In recWs.ListObjects
            If recTbl.Name = "yarn_order_recommendations" Then
                Set recTable = recTbl
                Exit For
            End If
        Next recTbl
        If Not recTable Is Nothing Then Exit For
    Next recWs

    ' clear output table first
    If outputTable.ListRows.Count > 0 Then outputTable.DataBodyRange.Delete
    ' filter source table based on drop-down value
    
    Dim cell As Range
    Dim SelectedGroup As String
    SelectedGroup = ws.Range("D2").Value  ' get group to filter by
    Dim arr() As Variant
    Dim r As Long
    ReDim arr(1 To sourceTable.ListRows.Count, 1 To sourceTable.ListColumns.Count)
    r = 0
    
    Dim i As Long
    For i = 1 To sourceTable.ListRows.Count
        If sourceTable.DataBodyRange.Cells(i, 1).Value = SelectedGroup Then ' adjust column index
            r = r + 1
            Dim j As Long
            For j = 1 To sourceTable.ListColumns.Count
                arr(r, j) = sourceTable.DataBodyRange.Cells(i, j).Value
            Next j
        End If
    Next i
    

    ' Add totals rows per color group
    Dim outputList As Collection
    Set outputList = New Collection

    Dim totalCols As Variant
    totalCols = Array(6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33)
    '7 SKU Count
    '8 FIN Inv
    '9 WIP Inv
    '10 Inv

    
    Dim totalCol As Variant

    Dim runningTotals() As Double
    ReDim runningTotals(1 To UBound(arr, 2))

    Dim grandTotals() As Double
    ReDim grandTotals(1 To UBound(arr, 2))
    
    Dim prevValue As Variant
    prevValue = ""
    
    For idx = 1 To r   ' <-- loop only through actual filtered rows
        Dim currentValue As Variant
        currentValue = arr(idx, 2)  ' adjust column index for colorgroup
        
        ' Add totals row when color group changes.
        If prevValue <> "" And currentValue <> prevValue Then
            Dim totalsRow() As Variant
            ReDim totalsRow(1 To 1, 1 To UBound(arr, 2))
            Dim c As Long
            For c = 1 To UBound(arr, 2)
                totalsRow(1, c) = ""
            Next c
            totalsRow(1, 1) = arr(idx - 1, 1)
            totalsRow(1, 2) = "Total " & prevValue

            
            For Each totalCol In totalCols
                If CLng(totalCol) <= UBound(arr, 2) Then
                    totalsRow(1, CLng(totalCol)) = runningTotals(CLng(totalCol))
                    runningTotals(CLng(totalCol)) = 0
                End If
            Next totalCol

            ' Recommended production lookup for this color group total
            If Not recTable Is Nothing Then
                totalsRow(1, 13) = WorksheetFunction.SumIfs( _
                    recTable.ListColumns("Recommended Order").DataBodyRange, _
                    recTable.ListColumns("PlanningGroup").DataBodyRange, arr(idx - 1, 1), _
                    recTable.ListColumns("ColorGroup").DataBodyRange, prevValue, _
                    recTable.ListColumns("Week").DataBodyRange, recWeek)
            End If

            outputList.Add totalsRow
            
            

            ' Add a true blank spacer row after each totals row (between groups).
            Dim spacerRow() As Variant
            ReDim spacerRow(1 To 1, 1 To UBound(arr, 2))
            For c = 1 To UBound(arr, 2)
                spacerRow(1, c) = ""
            Next c
            outputList.Add spacerRow
        End If
        
        
        Dim dataRow() As Variant
        ReDim dataRow(1 To 1, 1 To UBound(arr, 2))
        For c = 1 To UBound(arr, 2)
            dataRow(1, c) = arr(idx, c)
        Next c
        dataRow(1, 13) = ""  ' Recommended production belongs on totals row only
        outputList.Add dataRow

        For Each totalCol In totalCols
            If CLng(totalCol) <= UBound(arr, 2) Then
                If IsNumeric(arr(idx, CLng(totalCol))) Then
                    runningTotals(CLng(totalCol)) = runningTotals(CLng(totalCol)) + CDbl(arr(idx, CLng(totalCol)))
                    grandTotals(CLng(totalCol)) = grandTotals(CLng(totalCol)) + CDbl(arr(idx, CLng(totalCol)))
                End If
            End If
        Next totalCol
        
        prevValue = currentValue
    Next idx

    If r > 0 Then
        Dim finalTotalsRow() As Variant
        ReDim finalTotalsRow(1 To 1, 1 To UBound(arr, 2))
        For c = 1 To UBound(arr, 2)
            finalTotalsRow(1, c) = ""
        Next c
        finalTotalsRow(1, 2) = "Total " & prevValue

        For Each totalCol In totalCols
            If CLng(totalCol) <= UBound(arr, 2) Then
                finalTotalsRow(1, CLng(totalCol)) = runningTotals(CLng(totalCol))
            End If
        Next totalCol

        ' Recommended production lookup for final color group total
        If Not recTable Is Nothing Then
            finalTotalsRow(1, 13) = WorksheetFunction.SumIfs( _
                recTable.ListColumns("Recommended Order").DataBodyRange, _
                recTable.ListColumns("PlanningGroup").DataBodyRange, arr(r, 1), _
                recTable.ListColumns("ColorGroup").DataBodyRange, prevValue, _
                recTable.ListColumns("Week").DataBodyRange, recWeek)
        End If

        outputList.Add finalTotalsRow

        Dim grandTotalsRow() As Variant
        ReDim grandTotalsRow(1 To 1, 1 To UBound(arr, 2))
        For c = 1 To UBound(arr, 2)
            grandTotalsRow(1, c) = ""
        Next c
        grandTotalsRow(1, 2) = "Grand Total"

        For Each totalCol In totalCols
            If CLng(totalCol) <= UBound(arr, 2) Then
                grandTotalsRow(1, CLng(totalCol)) = grandTotals(CLng(totalCol))
            End If
        Next totalCol

        ' Recommended production lookup for grand total (all color groups in this planning group)
        If Not recTable Is Nothing Then
            grandTotalsRow(1, 13) = WorksheetFunction.SumIfs( _
                recTable.ListColumns("Recommended Order").DataBodyRange, _
                recTable.ListColumns("PlanningGroup").DataBodyRange, SelectedGroup, _
                recTable.ListColumns("Week").DataBodyRange, recWeek)
        End If

        outputList.Add grandTotalsRow
    End If

    ' finalArr already contains the filtered rows + blank rows
    Dim totalRows As Long
    totalRows = outputList.Count
    
    Dim finalArr() As Variant
    ReDim finalArr(1 To totalRows, 1 To UBound(arr, 2))
    
    For i = 1 To totalRows
        For j = 1 To UBound(arr, 2)
            finalArr(i, j) = outputList(i)(1, j)
        Next j
    Next i
    
    ' Write to table
    If totalRows > 0 Then
        outputTable.Resize outputTable.Range.Resize(totalRows + 1, sourceTable.ListColumns.Count)
        outputTable.DataBodyRange.Value = finalArr
    End If
    Exit Sub
errHndl:
    Application.EnableEvents = True
    MsgBox err.Description
End Sub
