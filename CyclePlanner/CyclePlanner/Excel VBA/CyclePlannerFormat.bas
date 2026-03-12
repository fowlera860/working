Sub FormatCyclePlanner()
    Application.ScreenUpdating = False
    'On Error GoTo ErrHnd
    
    Dim wsCP As Worksheet
    Dim wsParam As Worksheet
    Dim CP As Range
    Dim tblRow As Range
    
    
    Set wsParam = ThisWorkbook.Worksheets("Parameters")
    
    Dim clrSpacer As Variant
    Dim clrTotals As Variant
    Dim clrSpacerTimePhase As Variant
    Dim clrStripe1 As Variant
    Dim clrStripe2 As Variant
    Dim clrStripe1TimePhase As Variant
    Dim clrStripe2TimePhase As Variant
    Dim clrStripe1LowStock As Variant
    Dim clrStripe2LowStock As Variant
    Dim SpacerSize As Integer
    Dim lowStockAmount As Long
    Dim baseColor As Variant
    
    clrSpacer = wsParam.Range("B22").Interior.Color
    clrTotals = wsParam.Range("B24").Interior.Color
    clrStripe1 = wsParam.Range("B20").Interior.Color
    clrStripe2 = wsParam.Range("B21").Interior.Color
    clrSpacerTimePhase = wsParam.Range("C22").Interior.Color
    clrStripe1TimePhase = wsParam.Range("C20").Interior.Color
    clrStripe2TimePhase = wsParam.Range("C21").Interior.Color
    clrStripe1LowStock = wsParam.Range("D20").Interior.Color
    clrStripe2LowStock = wsParam.Range("D21").Interior.Color
    SpacerSize = wsParam.Range("B23").Value
    lowStockAmount = wsParam.Range("B4").Value
    

    Set wsCP = ThisWorkbook.Worksheets("Cycle Planner")
    With wsCP.Range("A7:AZ300")
        .RowHeight = 15
        .Interior.Color = xlNone
        .Font.Bold = False
        .Font.ColorIndex = xlAutomatic
    End With

    Set CP = wsCP.Range("CyclePlannerOutput")
    
    Dim odd As Boolean
    Dim col As Long
    Dim lastCol As Long
    Dim isWeekCol() As Boolean
    
    lastCol = CP.Columns.Count
    ReDim isWeekCol(1 To lastCol)
    
    ' Precompute which columns are "Week " columns
    For col = 1 To lastCol
        isWeekCol(col) = (Left(CP.Cells(1, col).Offset(-1, 0).Value, 5) = "Week ")
    Next col
    
    odd = True
    
    For Each tblRow In CP.rows
        Dim isTotalsRow As Boolean
        Dim isSpacerRow As Boolean

        isTotalsRow = (Left$(CStr(tblRow.Cells(1, 2).Value), 6) = "Total ")
        isSpacerRow = (tblRow.Cells(1, 1).Value = "" And tblRow.Cells(1, 2).Value = "")

        If isSpacerRow Then
            tblRow.RowHeight = SpacerSize
        Else
            tblRow.RowHeight = 15
        End If
        
        'find fill color
        For col = 1 To lastCol
            If isSpacerRow Then
                ' Spacer row
                If isWeekCol(col) Then
                    baseColor = clrSpacerTimePhase
                Else
                    baseColor = clrSpacer
                End If
            ElseIf isTotalsRow Then
                ' Totals row uses dedicated color and normal row spacing.
                baseColor = clrTotals
            Else
                ' Normal row
                If odd Then
                    baseColor = IIf(isWeekCol(col), clrStripe2TimePhase, clrStripe2)
                Else
                    baseColor = IIf(isWeekCol(col), clrStripe1TimePhase, clrStripe1)
                End If
                
                ' Override with low stock colors if value is <= lowStockAmount
                If isWeekCol(col) Then
                    If IsNumeric(tblRow.Cells(1, col).Value) Then
                        If tblRow.Cells(1, col).Value <= lowStockAmount Then
                            If odd Then
                                baseColor = clrStripe2LowStock
                            Else
                                baseColor = clrStripe1LowStock
                            End If
                        End If
                    End If
                End If
            End If
            'assign color
            tblRow.Cells(1, col).Interior.Color = baseColor
        Next col
        
        ' For normal rows only: highlight Recommended (column 22) when above zero.
        If (Not isSpacerRow) And (Not isTotalsRow) Then
            If lastCol >= 22 Then
                If IsNumeric(tblRow.Cells(1, 22).Value) And tblRow.Cells(1, 22).Value > 0 Then
                    tblRow.Cells(1, 22).Font.Color = vbRed
                    tblRow.Cells(1, 22).Font.Bold = True
                Else
                    tblRow.Cells(1, 22).Font.ColorIndex = xlAutomatic
                    tblRow.Cells(1, 22).Font.Bold = False
                End If
            End If

            ' Toggle odd/even only for normal rows
            odd = Not odd
        End If
    Next tblRow
            



    Application.ScreenUpdating = False
    Exit Sub
ErrHnd:
    Application.ScreenUpdating = True
    MsgBox err.Description
End Sub





