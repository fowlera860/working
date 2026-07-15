Attribute VB_Name = "Module1"


Sub download(sDate As Long, eDate As Long, wh As String, pro As String, waste As String)
    
    Dim CP As Worksheet
    Set CP = ThisWorkbook.Worksheets("Control Panel")
    Dim data As Worksheet
    Set data = ThisWorkbook.Worksheets("Data")
    
    Dim AD1S1S As Double, AD1S1E As Double, AD1S2S As Double, AD1S2E As Double, AD1S3S As Double, AD1S3E As Double
    Dim AD2S1S As Double, AD2S1E As Double, AD2S2S As Double, AD2S2E As Double, AD2S3S As Double, AD2S3E As Double
    Dim AR3S1S As Double, AR3S1E As Double, AR3S2S As Double, AR3S2E As Double, AR3S3S As Double, AR3S3E As Double
    Dim T As Double
    Dim d As Long, d2 As Long
    If CP.Range("G8").Value > 0 Then
        AD1S1S = CP.Range("C8").Value - (1 / 24) + sDate + 366
        AD1S1E = CP.Range("C9").Value - (1 / 24) + sDate + 366
    End If
    If CP.Range("G10").Value > 0 Then
        AD1S2S = CP.Range("C10").Value - (1 / 24) + sDate + 366
        AD1S2E = CP.Range("C11").Value - (1 / 24) + sDate + 366
    End If
    If CP.Range("G6").Value > 0 Then
        AD1S3S = CP.Range("C6").Value - (1 / 24) + sDate + 366
        AD1S3E = CP.Range("C7").Value - (1 / 24) + sDate + 366
    End If
    If CP.Range("H8").Value > 0 Then
        AD2S1S = CP.Range("D8").Value - (1 / 24) + sDate + 366
        AD2S1E = CP.Range("D9").Value - (1 / 24) + sDate + 366
    End If
    If CP.Range("H10").Value > 0 Then
        AD2S2S = CP.Range("D10").Value - (1 / 24) + sDate + 366
        AD2S2E = CP.Range("D11").Value - (1 / 24) + sDate + 366
    End If
    If CP.Range("H6").Value > 0 Then
        AD2S3S = CP.Range("D6").Value - (1 / 24) + sDate + 366
        AD2S3E = CP.Range("D7").Value - (1 / 24) + sDate + 366
    End If
    If CP.Range("H8").Value > 0 Then
        AR3S1S = CP.Range("E8").Value - (1 / 24) + sDate + 366
        AR3S1E = CP.Range("E9").Value - (1 / 24) + sDate + 366
    End If
    If CP.Range("H10").Value > 0 Then
        AR3S2S = CP.Range("E10").Value - (1 / 24) + sDate + 366
        AR3S2E = CP.Range("E11").Value - (1 / 24) + sDate + 366
    End If
    If CP.Range("H6").Value > 0 Then
        AR3S3S = CP.Range("E6").Value - (1 / 24) + sDate + 366
        AR3S3E = CP.Range("E7").Value - (1 / 24) + sDate + 366
    End If
    If AD1S3S > 0.5 + sDate + 366 And AD1S3S <> 0 Then AD1S3S = AD1S3S - 1
    If AD2S3S > 0.5 + sDate + 366 And AD2S3S <> 0 Then AD2S3S = AD2S3S - 1
    If AR3S3S > 0.5 + sDate + 366 And AR3S3S <> 0 Then AR3S3S = AR3S3S - 1
    If AD1S2E < 0.5 + sDate + 366 And AD1S2E <> 0 Then AD1S2E = AD1S2E + 1
    If AD2S2E < 0.5 + sDate + 366 And AD2S2E <> 0 Then AD2S2E = AD2S2E + 1
    If AR3S2E < 0.5 + sDate + 366 And AR3S2E <> 0 Then AR3S2E = AR3S2E + 1
    If AD1S2E < 0.5 + sDate + 366 And AD1S2E <> 0 Then AD1S2E = AD1S2E + 1
    If AD2S2E < 0.5 + sDate + 366 And AD2S2E <> 0 Then AD2S2E = AD2S2E + 1
    If AR3S2E < 0.5 + sDate + 366 And AR3S2E <> 0 Then AR3S2E = AR3S2E + 1
    
    Dim cnn As New ADODB.Connection
    Dim cmd400 As New ADODB.Command
    Dim rs As New ADODB.Recordset
    Dim sSQL As String
    
    
    eDate = sDate + 1
    

    
    
    cnn.Open "Provider=IBMDA400;Data Source=TDG-SA-DTS;"
    cmd400.ActiveConnection = cnn
    
    On Error Resume Next
    cmd400.CommandText = "DROP VIEW QTEMP.PROCESSES"
    cmd400.Execute
    On Error GoTo 0
    
    
    sSQL = sSQL & "CREATE VIEW QTEMP.PROCESSES(ROLL, MACHINE, CODE, DATE, TIME, SHIFT, OP, FEET, INCHS, WCODE, WDESC, PARENT, LOC, PTYPE) AS "
    sSQL = sSQL & " SELECT WEROLL, WEMCH#, WECODE, WEJUL+366 AS DATE,"
    sSQL = sSQL & " CAST(FLOOR(WETIME/10000) AS DECIMAL) /24  + CAST(FLOOR(WETIME/100)-FLOOR(WETIME/10000)*100 AS DECIMAL) /60/24 + CAST(WETIME - FLOOR(WETIME/100)*100 AS DECIMAL) /60/60/24 AS TIME,"
    sSQL = sSQL & " 1, "
    sSQL = sSQL & "  WEUSER, "
    sSQL = sSQL & " CAST(WELTHF AS DECIMAL) + (CAST(WELTHI AS DECIMAL)/12), "
    sSQL = sSQL & " '', '', '', WEPROL, WELOC, F2PTYP "
    sSQL = sSQL & " FROM CAMS.WPP050 "
    sSQL = sSQL & " LEFT OUTER JOIN CAMS.FIP020B "
    sSQL = sSQL & " ON F2STYL = WESTYL "
    sSQL = sSQL & " AND F2CLR = WECLR "
    sSQL = sSQL & " AND F2BACK = WEBACK "
    sSQL = sSQL & " AND F2SIZE = WESIZE "
    sSQL = sSQL & " WHERE WEJUL BETWEEN " & sDate & " AND " & eDate
    sSQL = sSQL & " AND WEWHSE = '" & wh & "'"
    sSQL = sSQL & " AND WECODE IN(" & pro & ") "
    sSQL = sSQL & " AND WEMCH# IN('AD1','AD2','AD3','AR3')"

    sSQL = sSQL & " UNION ALL"

    sSQL = sSQL & " SELECT WEROLL, WEMCH#, WECODE, WEJUL+366 AS DATE,"
    sSQL = sSQL & " CAST(FLOOR(WETIME/10000) AS DECIMAL) /24  + CAST(FLOOR(WETIME/100)-FLOOR(WETIME/10000)*100 AS DECIMAL) /60/24 + CAST(WETIME - FLOOR(WETIME/100)*100 AS DECIMAL) /60/60/24 AS TIME,"
    sSQL = sSQL & " 1, WEUSER, "
    sSQL = sSQL & " CAST(WELTHF AS DECIMAL) + (CAST(WELTHI AS DECIMAL)/12), "
    sSQL = sSQL & " '', '', '', WEPROL, WELOC, F2PTYP "
    sSQL = sSQL & " FROM CAMS.WPP050 "
    sSQL = sSQL & " LEFT OUTER JOIN CAMS.FIP020B "
    sSQL = sSQL & " ON F2STYL = WESTYL "
    sSQL = sSQL & " AND F2CLR = WECLR "
    sSQL = sSQL & " AND F2BACK = WEBACK "
    sSQL = sSQL & " AND F2SIZE = WESIZE "
    sSQL = sSQL & " WHERE WEJUL = " & sDate - 1
    
    sSQL = sSQL & " AND WEWHSE = '" & wh & "'"
    sSQL = sSQL & " AND WECODE IN(" & pro & ") "
    sSQL = sSQL & " AND WEMCH# IN('AD1','AD2','AD3','AR3')"
    sSQL = sSQL & " AND (CAST(FLOOR(WETIME/10000) AS DECIMAL)) >= CAST(22 AS DECIMAL) "
    
'    sSQL = sSQL & " UNION ALL "
'
'    sSQL = sSQL & " SELECT W2ROLL, '', 'WASTE', W2AJUL+366 AS DATE, "
'    sSQL = sSQL & " CAST(FLOOR(W2TIME/10000) AS DECIMAL) /24  + CAST(FLOOR(W2TIME/100)-FLOOR(W2TIME/10000)*100 AS DECIMAL) /60/24 + CAST(W2TIME - FLOOR(W2TIME/100)*100 AS DECIMAL) /60/60/24 AS TIME,"
'    sSQL = sSQL & " 1, "
'    sSQL = sSQL & "  W2USER,  W2BLTF, W2BLTI, W2WCDE, Q2DESC, '', '', F2PTYP "
'    sSQL = sSQL & " FROM CAMS.WIP020 "
'    sSQL = sSQL & " INNER JOIN CAMS.FIP010 "
'    sSQL = sSQL & " ON F1ROLL = W2ROLL "
'    sSQL = sSQL & " INNER JOIN CAMS.QLP020 "
'    sSQL = sSQL & " ON Q2REAS = W2WCDE"
'    sSQL = sSQL & " LEFT OUTER JOIN CAMS.FIP020B "
'    sSQL = sSQL & " ON F2STYL = W2STYL "
'    sSQL = sSQL & " AND F2CLR = W2CLR "
'    sSQL = sSQL & " AND F2BACK = W2BACK "
'    sSQL = sSQL & " AND F2SIZE = W2SIZE "
'    sSQL = sSQL & " WHERE W2AJUL BETWEEN " & sDate & " AND " & eDate
'    sSQL = sSQL & " AND W2WCDE IN('991','994')"
'    sSQL = sSQL & " AND W2WHSE = '" & wh & "'"
'
'    sSQL = sSQL & " UNION ALL "
'
'    sSQL = sSQL & " SELECT W2ROLL, '', 'WASTE', W2AJUL+366 AS DATE, "
'    sSQL = sSQL & " CAST(FLOOR(W2TIME/10000) AS DECIMAL) /24  + CAST(FLOOR(W2TIME/100)-FLOOR(W2TIME/10000)*100 AS DECIMAL) /60/24 + CAST(W2TIME - FLOOR(W2TIME/100)*100 AS DECIMAL) /60/60/24 AS TIME,"
'    sSQL = sSQL & " 1, W2USER,  W2BLTF, W2BLTI, W2WCDE, Q2DESC, '', '', F2PTYP "
'    sSQL = sSQL & " FROM CAMS.WIP020 "
'    sSQL = sSQL & " INNER JOIN CAMS.FIP010 "
'    sSQL = sSQL & " ON F1ROLL = W2ROLL "
'    sSQL = sSQL & " INNER JOIN CAMS.QLP020 "
'    sSQL = sSQL & " ON Q2REAS = W2WCDE"
'    sSQL = sSQL & " LEFT OUTER JOIN CAMS.FIP020B "
'    sSQL = sSQL & " ON F2STYL = W2STYL "
'    sSQL = sSQL & " AND F2CLR = W2CLR "
'    sSQL = sSQL & " AND F2BACK = W2BACK "
'    sSQL = sSQL & " AND F2SIZE = W2SIZE "
'    sSQL = sSQL & " WHERE W2AJUL BETWEEN " & sDate - 1 & " AND " & sDate - 1
'    sSQL = sSQL & " AND W2WCDE IN('991','994')"
'    sSQL = sSQL & " AND W2WHSE = '" & wh & "'"
'    sSQL = sSQL & " AND (CAST(FLOOR(W2TIME/10000) AS DECIMAL)) >= CAST(22 AS DECIMAL) "
    cmd400.CommandText = sSQL
    cmd400.Execute
    
    
    sSQL = "SELECT ROLL, MACHINE, CODE, DATE, TIME, SHIFT, OP, FEET, INCHS, WCODE, WDESC, PARENT, LOC, PTYPE "
    sSQL = sSQL & " FROM QTEMP.PROCESSES "
    sSQL = sSQL & " ORDER BY DATE, TIME"
    cmd400.CommandText = sSQL
    Set rs = cmd400.Execute
    
    
    data.Cells.ClearContents
    data.Cells.ClearContents
    data.Range("A2").CopyFromRecordset rs
    data.Range("A1:U1").Value = Array("Roll", "Machine", "Process", "Date", "Time", "Shift", "User", "Feet", _
                                        "X", "X", "X", "Parent Roll", "Location", "PType", _
                                        "FirstCut", "SubseqCut", "GiveAway", "ShortRoll", "LastCut", _
                                        "Balance", "Gave Away")
    
    On Error Resume Next
    cmd400.CommandText = "DROP VIEW QTEMP.PROCESSES"
    cmd400.Execute
    On Error GoTo 0
    
    
    
    Set rs = Nothing
    cnn.Close
    

    d = 2
    Do Until data.Range("A" & d).Value = ""
        If data.Range("C" & d).Value = "WASTE" Then
            d2 = d - 1
            Do Until data.Range("G" & d2).Value = data.Range("G" & d).Value Or d2 = 1
                d2 = d2 - 1
            Loop
            If d2 <> 1 Then
                data.Range("B" & d).Value = "W" & data.Range("B" & d2).Value
            End If
            

        End If
        If data.Range("F" & d).Value <> 0 Then
            'If data.Range("A" & d).Value = "0074534452" Then Stop
            T = CDbl(data.Range("E" & d).Value) + CDbl(data.Range("D" & d).Value)
            If data.Range("B" & d).Value = "AD1" Or data.Range("B" & d).Value = "WAD1" Then
                If T >= AD1S1S And T < AD1S1E Then
                    data.Range("F" & d).Value = 1
                ElseIf T >= AD1S2S And T < AD1S2E Then
                    data.Range("F" & d).Value = 2
                ElseIf T >= AD1S3S And T < AD1S3E Then
                    data.Range("F" & d).Value = 3
                Else
                    data.Range("F" & d).Value = "OUT OF RANGE"
                End If
            ElseIf data.Range("B" & d).Value = "AD2" Or data.Range("B" & d).Value = "WAD2" Then
                If T >= AD2S1S And T < AD2S1E Then
                    data.Range("F" & d).Value = 1
                ElseIf T >= AD2S2S And T < AD2S2E Then
                    data.Range("F" & d).Value = 2
                ElseIf T >= AD2S3S And T < AD2S3E Then
                    data.Range("F" & d).Value = 3
                Else
                    data.Range("F" & d).Value = "OUT OF RANGE"
                End If
            End If
        End If

        d = d + 1
    Loop
    d = d - 1
    data.Range("A2:U" & d).Sort key1:=data.Range("B2:B" & d), order1:=xlAscending
End Sub


Sub Parse(sDate As Long)
    
    Dim i As Long, x As Long, g As Long, x2 As Long
    Dim cRoll As String
    Dim cMch As String
    Dim data As Worksheet
    Dim smallRoll As Long
    Dim giveAway As Long
    Set data = ThisWorkbook.Worksheets("Data")
    sDate = sDate + 366
    smallRoll = 30
    giveAway = 5
    i = 2
    cMch = ""
    cRoll = ""
    Dim c As Integer
    c = 1
    Do Until data.Range("A" & i).Value = ""
        cMch = data.Range("B" & i).Value
        Do Until data.Range("B" & i).Value <> cMch Or data.Range("f" & i).Value = 0   'CLng(data.Range("D" & i).Value) > sDate Or
            If data.Range("C" & i).Value = "CUT" And data.Range("F" & i).Value <> "OUT OF RANGE" Then
                x = i
                If cRoll = data.Range("L" & i).Value Then
                    data.Range("S" & x).Value = 1
                    data.Range("P" & x).Value = 1          'subsequent Cut
                    data.Range("Q" & x2 & ":V" & x2).Value = ""   'delete Q-V from previous cut if this cut is subsequent
                    x2 = x                                  ' save last cut row
                Else
                    data.Range("S" & x).Value = 1
                    data.Range("O" & x).Value = 1
                    cRoll = data.Range("L" & i).Value   'first cut
                    x2 = x                                          ' save last cut row
                End If
                i = i + 1
                If data.Range("A" & i).Value = cRoll Then
                    If data.Range("H" & i).Value <= giveAway Then
                        data.Range("Q" & x).Value = 1               'should be giveaway
                    ElseIf data.Range("H" & i).Value <= smallRoll Then
                        data.Range("R" & x).Value = 1               'Short Roll should be remeasure
                    End If
                    g = i
                End If
                Do Until data.Range("A" & i + 1).Value <> cRoll Or data.Range("B" & i + 1).Value <> cMch ' find last CBL
                    i = i + 1
                    If data.Range("H" & i).Value > 0 Then g = i
                Loop

                If data.Range("H" & i).Value = 0 Then
                    data.Range("U" & x).Value = data.Range("H" & g).Value 'gave away
                ElseIf data.Range("M" & i).Value = "CUTTBL" Then
                    data.Range("T" & x).Value = data.Range("H" & i).Value 'Remeasured
                Else
                    data.Range("V" & x).Value = data.Range("H" & i).Value   'ejected
                End If
                
            ElseIf data.Range("C" & i).Value = "WASTE" And data.Range("F" & i).Value <> "OUT OF RANGE" And data.Range("B" & i).Value <> "" Then
                data.Range("P" & i).Value = 1          'subsequent Cut alwasy for waste cut
                data.Range("B" & i).Value = Strings.Right(data.Range("B" & i).Value, Strings.Len(data.Range("B" & i).Value) - 1)
                i = i + 1
            Else
                i = i + 1
            End If
            
        Loop
        
        
        i = i + 1
    Loop

    
End Sub

Sub createReport()
    Dim data As Worksheet, report As Worksheet, Specs As Worksheet
    Set data = ThisWorkbook.Worksheets("Data")
    Set report = ThisWorkbook.Worksheets("Report")
    Set Specs = ThisWorkbook.Worksheets("Specs")
    Dim firstCutMin As Double, subCutMin As Double, EjectMin As Double, MeasureMin As Double, Speed As Double
    Dim d As Long, r As Long, c As Long
    If report.AutoFilterMode Then report.Cells.AutoFilter
    report.Cells.ClearContents
    report.Cells.ClearContents
    
    
    r = 2
    d = 2
    c = 1
    Dim cnt As Integer
    report.Range("A1:V1").Value = data.Range("A1:V1").Value
    report.Range("V1:AA1").Value = Array("X", "1stCutMin", "SubCutMin", "EjectMin", "MeasureMin", "Cuts/Roll")
    Do Until data.Range("A" & d).Value = ""

        If data.Range("O" & d).Value + data.Range("P" & d).Value > 0 Then
            report.Range("A" & r & ":V" & r).Value = data.Range("A" & d & ":V" & d).Value
'            Select Case report.Range("E" & r).Value
'                Case Is < 0.25
'                    report.Range("F" & r).Value = 3
'                Case Is < 0.583333333333333
'                    report.Range("F" & r).Value = 1
'                Case Is < 0.958333333333333
'                    report.Range("F" & r).Value = 2
'                Case Else
'                    report.Range("F" & r).Value = 3
'            End Select
            If report.Range("B" & r).Value <> Specs.Range("A" & c).Value Then
                c = 2
                Do Until report.Range("B" & r).Value = Specs.Range("A" & c).Value Or Specs.Range("A" & c).Value = ""
                    c = c + 1
                Loop
                firstCutMin = Specs.Range("B" & c).Value
                subCutMin = Specs.Range("C" & c).Value
                EjectMin = Specs.Range("D" & c).Value
                MeasureMin = Specs.Range("E" & c).Value
                Speed = Specs.Range("F" & c).Value
            End If
            If Specs.Range("A" & c).Value <> "" Then
                If report.Range("O" & r).Value = 1 Then
                    report.Range("W" & r).Value = firstCutMin + ((report.Range("H" & r).Value + report.Range("U" & r).Value) / Speed)
                End If
                If report.Range("P" & r).Value = 1 Then
                    report.Range("X" & r).Value = subCutMin + ((report.Range("H" & r).Value + report.Range("U" & r).Value) / Speed)
                End If
                If report.Range("S" & r).Value = 1 Then
                    If report.Range("R" & r).Value = 1 Then
                        report.Range("Y" & r).Value = EjectMin
                    Else
                        report.Range("Z" & r).Value = MeasureMin + (report.Range("H" & r).Value / Speed)
                    End If
                End If
            End If
            r = r + 1
        End If




        d = d + 1
    Loop
    r = 2
    cnt = 1
    Do Until report.Range("L" & r).Value = ""
        If report.Range("L" & r + 1).Value <> report.Range("L" & r).Value Then
            report.Range("AA" & r).Value = cnt
            cnt = 1
        Else
            cnt = cnt + 1
        End If
        r = r + 1
    Loop
End Sub

Sub CreateSummary()
    Dim summary As Worksheet, report As Worksheet, CP As Worksheet
    Set summary = ThisWorkbook.Worksheets("Summary")
    Set report = ThisWorkbook.Worksheets("Report")
    Set CP = ThisWorkbook.Worksheets("Control Panel")
    Dim CurUser As String, curTime As Double
    If summary.AutoFilterMode Then summary.Cells.AutoFilter
    summary.Cells.ClearContents
    summary.Range("A1:R1").Value = Array("Date", "Machine", "Shift", "User", "Hours", "CutFeet", "NumCuts", _
                                        "NumRolls", "SubCuts", "GiveAwayCnt", "ShortRollCnt", "GiveAwayFt", "EjectFt", _
                                        "MeasuredFt", "FirstCutMin", "SubCutMin", "EjectMin", "MeasureMin")
    Dim s As Long, r As Long, c As Integer
    r = 2
    Do Until report.Range("A" & r).Value = ""
        s = 2
        Do Until (summary.Range("A" & s).Value = CP.Range("C3").Value And _
                  summary.Range("B" & s).Value = report.Range("B" & r).Value And _
                  summary.Range("C" & s).Value = report.Range("F" & r).Value And _
                  summary.Range("D" & s).Value = report.Range("G" & r).Value) Or _
                  summary.Range("A" & s).Value = ""
            s = s + 1
        Loop
        If summary.Range("A" & s).Value = "" Then
            summary.Range("A" & s).Value = CP.Range("C3").Value
            summary.Range("B" & s).Value = report.Range("B" & r).Value
            summary.Range("C" & s).Value = report.Range("F" & r).Value
            summary.Range("D" & s).Value = report.Range("G" & r).Value
            'Summary.Range("E" & s).Value = report.Range("E" & r).Value
            summary.Range("F" & s).Value = report.Range("H" & r).Value
            summary.Range("G" & s).Value = 1
            summary.Range("H" & s).Value = report.Range("O" & r).Value
            summary.Range("I" & s).Value = report.Range("P" & r).Value
            summary.Range("J" & s).Value = report.Range("Q" & r).Value
            summary.Range("K" & s).Value = report.Range("R" & r).Value
            summary.Range("L" & s).Value = report.Range("U" & r).Value
            If report.Range("R" & r).Value = 1 Then
                summary.Range("M" & s).Value = report.Range("T" & r).Value
            Else
                summary.Range("N" & s).Value = report.Range("T" & r).Value
            End If
            summary.Range("O" & s).Value = report.Range("W" & r).Value
            summary.Range("P" & s).Value = report.Range("X" & r).Value
            summary.Range("Q" & s).Value = report.Range("Y" & r).Value
            summary.Range("R" & s).Value = report.Range("Z" & r).Value
            
        Else
'            If report.Range("E" & r).Value < Summary.Range("E" & s).Value Then
'                Summary.Range("E" & s).Value = report.Range("E" & r).Value
'            End If
'            If report.Range("E" & r).Value > Summary.Range("F" & s).Value Then
'                Summary.Range("F" & s).Value = report.Range("E" & r).Value
'            End If
            summary.Range("F" & s).Value = summary.Range("F" & s).Value + report.Range("H" & r).Value
            summary.Range("G" & s).Value = summary.Range("G" & s).Value + 1
            summary.Range("H" & s).Value = summary.Range("H" & s).Value + report.Range("O" & r).Value
            summary.Range("I" & s).Value = summary.Range("I" & s).Value + report.Range("P" & r).Value
            summary.Range("J" & s).Value = summary.Range("J" & s).Value + report.Range("Q" & r).Value
            summary.Range("K" & s).Value = summary.Range("K" & s).Value + report.Range("R" & r).Value
            summary.Range("L" & s).Value = summary.Range("L" & s).Value + report.Range("U" & r).Value
            If report.Range("R" & r).Value = 1 Then
                summary.Range("M" & s).Value = summary.Range("M" & s).Value + report.Range("T" & r).Value
            Else
                summary.Range("N" & s).Value = summary.Range("N" & s).Value + report.Range("T" & r).Value
            End If
            summary.Range("O" & s).Value = summary.Range("O" & s).Value + report.Range("W" & r).Value
            summary.Range("P" & s).Value = summary.Range("P" & s).Value + report.Range("X" & r).Value
            summary.Range("Q" & s).Value = summary.Range("Q" & s).Value + report.Range("Y" & r).Value
            summary.Range("R" & s).Value = summary.Range("R" & s).Value + report.Range("Z" & r).Value
            
        End If
        If report.Range("C" & r).Value = "CUT" Then
            If CurUser = summary.Range("D" & s).Value Then
                summary.Range("E" & s).Value = summary.Range("E" & s).Value + (report.Range("E" & r).Value - curTime) * 24
                curTime = report.Range("E" & r).Value
            Else
                CurUser = summary.Range("D" & s).Value
                curTime = report.Range("E" & r).Value
            End If
        End If
        r = r + 1
    Loop
    s = 2
    Do Until summary.Range("A" & s).Value = ""
        For c = 5 To 18
            If summary.Cells(s, c) = "" Then summary.Cells(s, c) = 0
        Next c
        s = s + 1
    Loop
End Sub

Sub UploadData()
Dim cnn As New ADODB.Connection
    Dim cmd400 As New ADODB.Command
    Dim rs As New ADODB.Recordset
    Dim sSQL As String
    
    Dim summary As Worksheet
    Set summary = ThisWorkbook.Worksheets("Summary")
    Dim i As Long
    i = 2
    If summary.Range("A" & i).Value <> "" Then
        cnn.Open "Provider=SQLOLEDB.1;Data Source=tdg-atm-webdev\sqlexpress;Initial Catalog=Planning;Uid=intranet_user;Pwd=Dixie123;Connection Timeout=120"
        cmd400.ActiveConnection = cnn
        
        sSQL = "DELETE FROM DBO.ADRDAILYCUTS WHERE DATE = " & CLng(summary.Range("A" & i).Value)
        
        Do Until summary.Range("A" & i).Value = ""
        
        
            sSQL = "INSERT INTO DBO.ADRDAILYCUTS(DATE,MACHINE,SHIFT,PROFILE,HOURS,CUTFEET,"
            sSQL = sSQL & " NUMCUTS,NUMROLLS,SUBCUTS,GIVEAWAYCNT,SHORTROLLCNT, "
            sSQL = sSQL & " GIVEAWAYFT,EJECTFT,MEASUREDFT,"
            sSQL = sSQL & " FIRSTCUTMIN,SUBCUTMIN,EJECTMIN,MEASUREMIN)"
            sSQL = sSQL & " VALUES( "
            sSQL = sSQL & "'" & summary.Range("A" & i).Value & "', "
            sSQL = sSQL & "'" & summary.Range("B" & i).Value & "', "
            sSQL = sSQL & "'" & summary.Range("C" & i).Value & "', "
            sSQL = sSQL & "'" & summary.Range("D" & i).Value & "', "
            sSQL = sSQL & summary.Range("E" & i).Value & ", "
            sSQL = sSQL & summary.Range("F" & i).Value & ", "
            sSQL = sSQL & summary.Range("G" & i).Value & ", "
            sSQL = sSQL & summary.Range("H" & i).Value & ", "
            sSQL = sSQL & summary.Range("I" & i).Value & ", "
            sSQL = sSQL & summary.Range("J" & i).Value & ", "
            sSQL = sSQL & summary.Range("K" & i).Value & ", "
            sSQL = sSQL & summary.Range("L" & i).Value & ", "
            sSQL = sSQL & summary.Range("M" & i).Value & ", "
            sSQL = sSQL & summary.Range("N" & i).Value & ", "
            sSQL = sSQL & summary.Range("O" & i).Value & ", "
            sSQL = sSQL & summary.Range("P" & i).Value & ", "
            sSQL = sSQL & summary.Range("Q" & i).Value & ", "
            sSQL = sSQL & summary.Range("R" & i).Value & ") "
            cmd400.CommandText = sSQL
            cmd400.Execute
            
            i = i + 1
        Loop
        Set rs = Nothing
        cnn.Close
    End If
End Sub


