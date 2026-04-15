Sub GenerateCyclePlanner()
    On Error GoTo errHndl
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets("Cycle Planner")
    
    Dim sourceTable As ListObject
    Set sourceTable = ThisWorkbook.Sheets("CyclePlannerPrebuild").ListObjects("CyclePlannerPrebuild")
    'Set sourceTable = ThisWorkbook.Sheets("CyclePlannerPrebuild (2)").ListObjects("CyclePlannerPrebuild__2")
    
    Dim outputTable As ListObject
    Set outputTable = ws.ListObjects("CyclePlannerOutput")
    
    ' clear output table first
    If outputTable.ListRows.Count > 0 Then outputTable.DataBodyRange.Delete
    ' filter source table based on drop-down value
    
    Dim cell As Range
    Dim SelectedGroup As String
    SelectedGroup = ws.Range("C2").Value  ' get group to filter by
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
    totalCols = Array(15, 16, 17, 18, 19, 20, 21, 22, 23, 25, 26, 27)
    '15 O Avg Forecast LF
    '16 P Avg Forecast Lbs
    '17 Q AsgQty LF
    '18 R ReservedQty LF
    '19 S B/O LF
    '20 T Open Tuft LF
    '21 U Inv LF
    '22 V Inv Pos (LF)
    '23 W Inv Pos (Lbs)
    '25 Y Recommended LF
    '26 Z Recommended Rolls
    '27 AA Recommended Lbs
    
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
            totalsRow(1, 29) = arr(idx - 1, 29)
            totalsRow(1, 30) = arr(idx - 1, 30)
            totalsRow(1, 31) = arr(idx - 1, 31)
            totalsRow(1, 32) = arr(idx - 1, 32)
            totalsRow(1, 33) = arr(idx - 1, 33)
            
            For Each totalCol In totalCols
                If CLng(totalCol) <= UBound(arr, 2) Then
                    totalsRow(1, CLng(totalCol)) = runningTotals(CLng(totalCol))
                    runningTotals(CLng(totalCol)) = 0
                End If
            Next totalCol

            'add total row calculations
            
            If totalsRow(1, 16) = 0 Then
                totalsRow(1, 24) = 0
                totalsRow(1, 28) = 0
            Else
                'X Inv Pos (Wks) = W Inv Pos (Lbs) / P Avg Forecast Lbs
                totalsRow(1, 24) = totalsRow(1, 23) / totalsRow(1, 16)
                'AB Inv Pos (Wks) = (  W Inv Pos (Lbs) + AA RecommendedLbs) / P Avg Forecast Lbs
                totalsRow(1, 28) = (totalsRow(1, 23) + totalsRow(1, 27)) / totalsRow(1, 16)
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

        outputList.Add grandTotalsRow
    End If

    ' finalArr already contains filtered rows + totals rows
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

