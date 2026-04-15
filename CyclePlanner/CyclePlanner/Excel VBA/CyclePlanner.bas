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

    ' --- Column Reference (CyclePlannerPrebuild table) ---
    ' Col  1: PlanningGroup
    ' Col  2: ColorGroup
    ' Col  3: Style
    ' Col  4: StyleName
    ' Col  5: Color
    ' Col  6: ColorName
    ' Col  7: Size
    ' Col  8: Back
    ' Col  9: RollSize
    ' Col 10: FaceWt
    ' Col 11: Lbs / Roll
    ' Col 12: MachineNum
    ' Col 13: MachineDescription
    ' Col 14: EPN
    ' Col 15: Avg Forecast LF          <-- summed in totals
    ' Col 16: Avg Forecast Lbs         <-- summed in totals; used as divisor for Wks calcs
    ' Col 17: AsgQty LF                <-- summed in totals
    ' Col 18: ReservedQty LF           <-- summed in totals
    ' Col 19: Max BO Order LF
    ' Col 20: B/O LF                   <-- summed in totals
    ' Col 21: Open Tuft LF             <-- summed in totals
    ' Col 22: Max Roll LF
    ' Col 23: Inv LF                   <-- summed in totals
    ' Col 24: Inv Pos (LF)             <-- summed in totals
    ' Col 25: Inv Pos (Lbs)            <-- summed in totals
    ' Col 26: Inv Pos (Wks)            <-- CALCULATED in total rows: col25 / col16
    ' Col 27: Recommended LF           <-- summed in totals
    ' Col 28: Recommended Rolls        <-- summed in totals
    ' Col 29: RecommendedLbs           <-- summed in totals
    ' Col 30: Updated Position         <-- CALCULATED in total rows: (col25 + col29) / col16
    ' Col 31: ColorGroup.target_weeks          <-- copied from last row of group
    ' Col 32: ColorGroup.tufting_production_size <-- copied from last row of group
    ' Col 33: ColorGroup.Run Size (Lbs)         <-- copied from last row of group
    ' Col 34: ColorGroup.Run Size               <-- copied from last row of group
    ' Col 35: ColorGroup.Color Inv Pos (Wks)    <-- copied from last row of group
    ' Col 36-55: Week 01 - Week 20

    Dim cell As Range
    Dim SelectedGroup As String
    SelectedGroup = ws.Range("C2").Value  ' planning group to filter by (from drop-down)
    Dim arr() As Variant
    Dim r As Long
    ReDim arr(1 To sourceTable.ListRows.Count, 1 To sourceTable.ListColumns.Count)
    r = 0
    
    ' Copy rows matching SelectedGroup into arr()
    Dim i As Long
    For i = 1 To sourceTable.ListRows.Count
        If sourceTable.DataBodyRange.Cells(i, 1).Value = SelectedGroup Then ' col 1 = PlanningGroup
            r = r + 1
            Dim j As Long
            For j = 1 To sourceTable.ListColumns.Count
                arr(r, j) = sourceTable.DataBodyRange.Cells(i, j).Value
            Next j
        End If
    Next i
    
    ' Build output: data rows interleaved with group totals rows and spacers
    Dim outputList As Collection
    Set outputList = New Collection

    ' Columns to SUM in totals rows.
    ' Col 26 (Inv Pos Wks) and Col 30 (Updated Position) are CALCULATED, not summed.
    Dim totalCols As Variant
    totalCols = Array(15, 16, 17, 18, 20, 21, 23, 24, 25, 27, 28, 29)
    ' Col 15: Avg Forecast LF
    ' Col 16: Avg Forecast Lbs
    ' Col 17: AsgQty LF
    ' Col 18: ReservedQty LF
    ' Col 20: B/O LF
    ' Col 21: Open Tuft LF
    ' Col 23: Inv LF
    ' Col 24: Inv Pos (LF)
    ' Col 25: Inv Pos (Lbs)
    ' Col 27: Recommended LF
    ' Col 28: Recommended Rolls
    ' Col 29: RecommendedLbs

    Dim totalCol As Variant

    Dim runningTotals() As Double   ' resets each ColorGroup
    ReDim runningTotals(1 To UBound(arr, 2))

    Dim grandTotals() As Double     ' accumulates across all ColorGroups
    ReDim grandTotals(1 To UBound(arr, 2))
    
    Dim prevValue As Variant
    prevValue = ""
    
    For idx = 1 To r   ' loop only through actual filtered rows
        Dim currentValue As Variant
        currentValue = arr(idx, 2)  ' col 2 = ColorGroup
        
        ' When ColorGroup changes, emit a totals row for the completed group
        If prevValue <> "" And currentValue <> prevValue Then
            Dim totalsRow() As Variant
            ReDim totalsRow(1 To 1, 1 To UBound(arr, 2))
            Dim c As Long
            For c = 1 To UBound(arr, 2)
                totalsRow(1, c) = ""
            Next c
            totalsRow(1, 1) = arr(idx - 1, 1)           ' col  1: PlanningGroup
            totalsRow(1, 2) = "Total " & prevValue       ' col  2: ColorGroup label
            ' Copy ColorGroup metadata from the last row of this group
            totalsRow(1, 31) = arr(idx - 1, 31)          ' col 31: ColorGroup.target_weeks
            totalsRow(1, 32) = arr(idx - 1, 32)          ' col 32: ColorGroup.tufting_production_size
            totalsRow(1, 33) = arr(idx - 1, 33)          ' col 33: ColorGroup.Run Size (Lbs)
            totalsRow(1, 34) = arr(idx - 1, 34)          ' col 34: ColorGroup.Run Size
            totalsRow(1, 35) = arr(idx - 1, 35)          ' col 35: ColorGroup.Color Inv Pos (Wks)
            
            ' Fill summed columns, then reset runningTotals for the next group
            For Each totalCol In totalCols
                If CLng(totalCol) <= UBound(arr, 2) Then
                    totalsRow(1, CLng(totalCol)) = runningTotals(CLng(totalCol))
                    runningTotals(CLng(totalCol)) = 0
                End If
            Next totalCol

            ' Calculate derived Wks columns for the totals row
            If totalsRow(1, 16) = 0 Then
                totalsRow(1, 26) = 0    ' col 26: Inv Pos (Wks) = Inv Pos Lbs / Avg Forecast Lbs
                totalsRow(1, 30) = 0    ' col 30: Updated Position = (Inv Pos Lbs + RecommendedLbs) / Avg Forecast Lbs
            Else
                totalsRow(1, 26) = totalsRow(1, 25) / totalsRow(1, 16)
                totalsRow(1, 30) = (totalsRow(1, 25) + totalsRow(1, 29)) / totalsRow(1, 16)
            End If
            outputList.Add totalsRow

            ' Add a blank spacer row between groups
            Dim spacerRow() As Variant
            ReDim spacerRow(1 To 1, 1 To UBound(arr, 2))
            For c = 1 To UBound(arr, 2)
                spacerRow(1, c) = ""
            Next c
            outputList.Add spacerRow
        End If
        
        ' Add the data row as-is
        Dim dataRow() As Variant
        ReDim dataRow(1 To 1, 1 To UBound(arr, 2))
        For c = 1 To UBound(arr, 2)
            dataRow(1, c) = arr(idx, c)
        Next c
        outputList.Add dataRow

        ' Accumulate running totals (per group) and grand totals (all groups)
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
        ' --- Final group totals row (last ColorGroup, emitted after the loop) ---
        Dim finalTotalsRow() As Variant
        ReDim finalTotalsRow(1 To 1, 1 To UBound(arr, 2))
        For c = 1 To UBound(arr, 2)
            finalTotalsRow(1, c) = ""
        Next c
        finalTotalsRow(1, 1) = arr(r, 1)              ' col  1: PlanningGroup
        finalTotalsRow(1, 2) = "Total " & prevValue   ' col  2: ColorGroup label
        ' Copy ColorGroup metadata from the last data row
        finalTotalsRow(1, 31) = arr(r, 31)             ' col 31: ColorGroup.target_weeks
        finalTotalsRow(1, 32) = arr(r, 32)             ' col 32: ColorGroup.tufting_production_size
        finalTotalsRow(1, 33) = arr(r, 33)             ' col 33: ColorGroup.Run Size (Lbs)
        finalTotalsRow(1, 34) = arr(r, 34)             ' col 34: ColorGroup.Run Size
        finalTotalsRow(1, 35) = arr(r, 35)             ' col 35: ColorGroup.Color Inv Pos (Wks)

        ' Fill summed columns from runningTotals
        For Each totalCol In totalCols
            If CLng(totalCol) <= UBound(arr, 2) Then
                finalTotalsRow(1, CLng(totalCol)) = runningTotals(CLng(totalCol))
            End If
        Next totalCol

        ' Calculate derived Wks columns
        If finalTotalsRow(1, 16) = 0 Then
            finalTotalsRow(1, 26) = 0    ' col 26: Inv Pos (Wks)
            finalTotalsRow(1, 30) = 0    ' col 30: Updated Position
        Else
            finalTotalsRow(1, 26) = finalTotalsRow(1, 25) / finalTotalsRow(1, 16)
            finalTotalsRow(1, 30) = (finalTotalsRow(1, 25) + finalTotalsRow(1, 29)) / finalTotalsRow(1, 16)
        End If

        outputList.Add finalTotalsRow

        ' --- Grand totals row ---
        Dim grandTotalsRow() As Variant
        ReDim grandTotalsRow(1 To 1, 1 To UBound(arr, 2))
        For c = 1 To UBound(arr, 2)
            grandTotalsRow(1, c) = ""
        Next c
        grandTotalsRow(1, 2) = "Grand Total"

        ' Fill summed columns from grandTotals
        For Each totalCol In totalCols
            If CLng(totalCol) <= UBound(arr, 2) Then
                grandTotalsRow(1, CLng(totalCol)) = grandTotals(CLng(totalCol))
            End If
        Next totalCol

        ' Calculate derived Wks columns for grand total
        If grandTotalsRow(1, 16) = 0 Then
            grandTotalsRow(1, 26) = 0    ' col 26: Inv Pos (Wks)
            grandTotalsRow(1, 30) = 0    ' col 30: Updated Position
        Else
            grandTotalsRow(1, 26) = grandTotalsRow(1, 25) / grandTotalsRow(1, 16)
            grandTotalsRow(1, 30) = (grandTotalsRow(1, 25) + grandTotalsRow(1, 29)) / grandTotalsRow(1, 16)
        End If

        outputList.Add grandTotalsRow
    End If

    ' Flatten outputList into a 2D array for a single bulk write
    Dim totalRows As Long
    totalRows = outputList.Count
    
    Dim finalArr() As Variant
    ReDim finalArr(1 To totalRows, 1 To UBound(arr, 2))
    
    For i = 1 To totalRows
        For j = 1 To UBound(arr, 2)
            finalArr(i, j) = outputList(i)(1, j)
        Next j
    Next i
    
    ' Write to output table
    If totalRows > 0 Then
        outputTable.Resize outputTable.Range.Resize(totalRows + 1, sourceTable.ListColumns.Count)
        outputTable.DataBodyRange.Value = finalArr
    End If
    Exit Sub
errHndl:
    Application.EnableEvents = True
    MsgBox err.Description
End Sub

