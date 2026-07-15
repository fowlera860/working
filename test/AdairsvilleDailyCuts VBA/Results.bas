Attribute VB_Name = "Results"
Option Explicit

Sub UpdateDailyCutsResults()

    Dim wsCP As Worksheet, wsR As Worksheet
    Dim tbl As ListObject
    Dim targetDate As Date
    
    Set wsCP = ThisWorkbook.Worksheets("Control Panel")
    Set wsR = ThisWorkbook.Worksheets("Results")
    Set tbl = wsR.ListObjects("DailyCutsResults")
    
    targetDate = wsCP.Range("C3").Value
    
    Dim shift As Integer
    Dim i As Integer
    Dim machineName As String
    Dim baseCol As Integer
    Dim newCount As Integer
    Dim updatedCount As Integer

    newCount = 0
    updatedCount = 0

    Application.ScreenUpdating = False
    
    For shift = 1 To 3
    
        For i = 0 To 2
        
            baseCol = GetMachineBaseCol(shift, i)
            
            ' only save machine name if data exists, blank machine names get skipped
            If wsCP.Cells(24, baseCol).Value > 0 Then
                machineName = wsCP.Cells(23, baseCol).Value
            Else
                machineName = ""
            End If
            
            If machineName <> "" Then
                UpsertRow tbl, wsCP, targetDate, shift, machineName, baseCol, newCount, updatedCount
            End If
            
        Next i
        
    Next shift

    Application.ScreenUpdating = True

    MsgBox "Saved " & newCount & " new records, updated " & updatedCount & " records.", vbInformation

End Sub


Private Function GetMachineBaseCol(shift As Integer, index As Integer) As Integer
    ' Shift 1: C(3), D(4)
    ' Shift 2: H(8), I(9)
    ' Shift 3: M(13), N(14)
    
    Dim startCols As Variant
    startCols = Array(3, 8, 13)
    
    GetMachineBaseCol = startCols(shift - 1) + index
End Function


Private Sub UpsertRow(tbl As ListObject, wsCP As Worksheet, _
                      targetDate As Date, shift As Integer, _
                      machineName As String, baseCol As Integer, _
                      ByRef newCount As Integer, ByRef updatedCount As Integer)

    Dim lr As ListRow
    Dim foundRow As ListRow
    
    Dim timeCol As Integer, overrideCol As Integer
    
    If machineName = "AD1" Then
        timeCol = 3
        overrideCol = 19
    ElseIf machineName = "AD2" Then
        timeCol = 4
        overrideCol = 20
    Else
        timeCol = 5
        overrideCol = 21
    End If
    ' Find existing row
    For Each lr In tbl.ListRows
        If lr.Range(1, 1).Value = targetDate And _
           lr.Range(1, 2).Value = machineName And _
           lr.Range(1, 3).Value = shift Then
           
            Set foundRow = lr
            Exit For
        End If
    Next lr
    
    If foundRow Is Nothing Then
        Set foundRow = tbl.ListRows.Add
        newCount = newCount + 1
    Else
        updatedCount = updatedCount + 1
    End If
    
    With foundRow.Range
        
        .Cells(1, 1).Value = targetDate
        .Cells(1, 2).Value = machineName
        .Cells(1, 3).Value = shift
        
        ' Shift + Machine specific data
        .Cells(1, 4).Value = wsCP.Cells(24, baseCol).Value ' Hours
        .Cells(1, 5).Value = wsCP.Cells(25, baseCol).Value ' Rolls
        .Cells(1, 6).Value = wsCP.Cells(26, baseCol).Value ' Cuts
        .Cells(1, 7).Value = wsCP.Cells(27, baseCol).Value ' Cuts/Roll
        .Cells(1, 8).Value = wsCP.Cells(28, baseCol).Value ' Earned Min
        .Cells(1, 9).Value = wsCP.Cells(29, baseCol).Value ' Avail Min
        .Cells(1, 10).Value = wsCP.Cells(30, baseCol).Value ' Effective %
        
        .Cells(1, 11).Value = wsCP.Cells(32, baseCol).Value ' Cuts/Hr
        .Cells(1, 12).Value = wsCP.Cells(33, baseCol).Value ' Cuts/Hr Max
        
        .Cells(1, 13).Value = wsCP.Cells(35, baseCol).Value ' Single cut
        .Cells(1, 14).Value = wsCP.Cells(36, baseCol).Value ' 2 cuts
        .Cells(1, 15).Value = wsCP.Cells(37, baseCol).Value ' 3-5 cuts
        .Cells(1, 16).Value = wsCP.Cells(38, baseCol).Value ' 6+ cuts
        
        ' ===== Shift Start / End =====
        Dim startRow As Integer, endRow As Integer
        
        Select Case shift
            Case 1
                startRow = 8
                endRow = 9
            Case 2
                startRow = 10
                endRow = 11
            Case 3
                startRow = 6
                endRow = 7
        End Select
        
        .Cells(1, 17).Value = wsCP.Cells(startRow, timeCol).Value
        .Cells(1, 18).Value = wsCP.Cells(endRow, timeCol).Value
        
        
        ' ===== Override Hours =====
        Dim overrideRow As Integer
        Select Case shift
            Case 3: overrideRow = 6
            Case 1: overrideRow = 7
            Case 2: overrideRow = 8
        End Select
        
        .Cells(1, 19).Value = wsCP.Cells(overrideRow, overrideCol).Value
    End With

End Sub

