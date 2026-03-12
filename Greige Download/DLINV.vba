Dim cnn As New ADODB.Connection
  Dim cmd400 As New ADODB.Command
  Dim rs As New ADODB.Recordset
  
  Dim sSql As String
Sub Inventory()
cnn.Open "Provider=IBMDA400;Data Source=TDGPROD;"
Application.ScreenUpdating = False
    ActiveWorkbook.Activate
    ActiveWorkbook.Sheets("DATA").Activate
    ActiveWorkbook.Sheets("DATA").Range("A2:K65536").Select
    Selection.ClearContents
    ActiveWorkbook.Sheets("DATA").Range("Q2:S65536").Select
    Selection.ClearContents
    ActiveWorkbook.Sheets("DATA").Range("X2:Y65536").Select
    Selection.ClearContents
    ActiveWorkbook.Sheets("DATA").Range("AF2:AG65536").Select
    Selection.ClearContents
    
cmd400.ActiveConnection = cnn
Application.StatusBar = "Download in Progress......."
sSql = "SELECT G1STYL, "
sSql = sSql & " ROUND(SUM(((CAST(G1CLTF AS DEC(4,0))*12)+CAST(G1CLTI AS DEC(4,0)))*((CAST(G1CWTF AS DEC(4,0))*12)+CAST(G1CWTI AS DEC(4,0)))/1296),0) as SQYD,"
sSql = sSql & " COUNT(G1ROLL) AS ROLLS"
sSql = sSql & " from cams.GIP010"
sSql = sSql & " WHERE G1ACT<>7 And G1ACT<>9 AND G1ATLF>1 AND G1CLR='' AND G1CLTF>=25 AND G1SCLR<'1' AND G1DDTE<1 " & _
                "AND G1DPRT<>'Y' AND G1DLOT<'1' AND G1LOC<>'LOST' AND G1WHSE<>'37' AND G1QLTY =1 "
sSql = sSql & " Group by G1STYL"
'sSql = sSql & " ORDER BY SKU"
'MsgBox sSql
cmd400.CommandText = sSql
Set rs = cmd400.Execute
    If Not rs.EOF Then
Application.StatusBar = "Running Line Products List..." & counter
                    ActiveWorkbook.Sheets("DATA").Range("A2").CopyFromRecordset rs
                    rs.Close
                    With ActiveWorkbook.Sheets("DATA").Range("A1:C1")
                        .Value = Array("STYLE", "SQYDS", "ROLLS")
                        .Font.Bold = True
                    End With
                    ActiveWorkbook.Sheets("DATA").UsedRange.EntireColumn.AutoFit
                    ActiveWorkbook.Activate
                    ActiveWorkbook.Sheets("DATA").Activate
                    ActiveWorkbook.Sheets("DATA").Range("A1").Activate
    Else
'        MsgBox "There are no 1st Quality Rolls in Atmore.", vbCritical
    End If
    If CBool(rs.State And adStateOpen) Then rs.Close
    Set rs = Nothing


sSql = "SELECT G1STYL, ROUND(SUM(((G1CLTF*12)+G1CLTI)*((G1CWTF*12)+G1CWTI)/1296),0) as SQYD, COUNT(G1ROLL) AS ROLLS"
sSql = sSql & " from cams.GIP010"
sSql = sSql & " WHERE G1ACT<>7 And G1ACT<>9 AND G1ATLF>1 AND G1CLR='' AND G1CLTF>=25 AND G1SCLR<'1' AND G1DDTE<1 " & _
                "AND G1DPRT<>'Y' AND G1DLOT<'1' AND G1LOC<>'LOST' AND G1WHSE<>'37' AND G1WHSE<>'59' AND G1QLTY = 7"
sSql = sSql & " Group by G1STYL"
'sSql = sSql & " ORDER BY SKU"
'MsgBox sSql
cmd400.CommandText = sSql
Set rs = cmd400.Execute
    If Not rs.EOF Then
Application.StatusBar = "Running Line Products List..." & counter
                    ActiveWorkbook.Sheets("DATA").Range("I2").CopyFromRecordset rs
                    rs.Close
                    With ActiveWorkbook.Sheets("DATA").Range("I1:K1")
                        .Value = Array("STYLE", "SQYDS", "ROLLS")
                        .Font.Bold = True
                    End With
                    ActiveWorkbook.Sheets("DATA").UsedRange.EntireColumn.AutoFit
                    ActiveWorkbook.Activate
                    ActiveWorkbook.Sheets("DATA").Activate
                    ActiveWorkbook.Sheets("DATA").Range("A1").Activate
    Else
'        MsgBox "There are no quality 7 rolls.", vbCritical
    End If
    If CBool(rs.State And adStateOpen) Then rs.Close
    Set rs = Nothing

sSql = "SELECT G1STYL, ROUND(SUM(((G1CLTF*12)+G1CLTI)*((G1CWTF*12)+G1CWTI)/1296),0) as SQYD, COUNT(G1ROLL) AS ROLLS"
sSql = sSql & " from cams.GIP010"
sSql = sSql & " WHERE G1ACT<>7 And G1ACT<>9 AND G1ATLF>1 AND G1CLR='' AND G1CLTF>=25 AND G1SCLR<'1' AND G1DDTE<1 " & _
                "AND G1DPRT<>'Y' AND G1DLOT<'1' AND G1LOC<>'LOST' AND G1WHSE<>'37' AND G1WHSE<>'59' AND G1QLTY = 5"
sSql = sSql & " Group by G1STYL"
'sSql = sSql & " ORDER BY SKU"
'MsgBox sSql
cmd400.CommandText = sSql
Set rs = cmd400.Execute
    If Not rs.EOF Then
Application.StatusBar = "Running Line Products List..." & counter
                    ActiveWorkbook.Sheets("DATA").Range("Q2").CopyFromRecordset rs
                    rs.Close
                    With ActiveWorkbook.Sheets("DATA").Range("Q1:S1")
                        .Value = Array("STYLE", "SQYDS", "ROLLS")
                        .Font.Bold = True
                    End With
                    ActiveWorkbook.Sheets("DATA").UsedRange.EntireColumn.AutoFit
                    ActiveWorkbook.Activate
                    ActiveWorkbook.Sheets("DATA").Activate
                    ActiveWorkbook.Sheets("DATA").Range("A1").Activate
    Else
'        MsgBox "There are no quality 5 rolls.", vbCritical
    End If
    If CBool(rs.State And adStateOpen) Then rs.Close
    Set rs = Nothing

sSql = "SELECT G1STYL, ROUND(SUM(((G1CLTF*12)+G1CLTI)*((G1CWTF*12)+G1CWTI)/1296),0) as SQYD"
sSql = sSql & " from cams.GIP010"
sSql = sSql & " WHERE G1ACT<>7 And G1ACT<>9 AND G1ATLF>1 AND G1CLR='' AND G1CLTF>=25 AND G1SCLR<'1' AND G1DDTE<1 " & _
                "AND G1DPRT<>'Y' AND G1DLOT<'1' AND G1LOC<>'LOST' AND G1WHSE<>'37' AND G1WHSE<>'59' AND G1QLTY <>1 AND G1QLTY <>7 AND G1QLTY <>5"
sSql = sSql & " Group by G1STYL"
'sSql = sSql & " ORDER BY SKU"
'MsgBox sSql
cmd400.CommandText = sSql
Set rs = cmd400.Execute
    If Not rs.EOF Then
Application.StatusBar = "Running Line Products List..." & counter
                    ActiveWorkbook.Sheets("DATA").Range("X2").CopyFromRecordset rs
                    rs.Close
                    With ActiveWorkbook.Sheets("DATA").Range("X1:Y1")
                        .Value = Array("Style", "2 Qual Sqyds")
                        .Font.Bold = True
                    End With
                    ActiveWorkbook.Sheets("DATA").UsedRange.EntireColumn.AutoFit
                    ActiveWorkbook.Activate
                    ActiveWorkbook.Sheets("DATA").Activate
                    ActiveWorkbook.Sheets("DATA").Range("A1").Activate
    Else
'        MsgBox "There are no 2nd quality rolls.", vbCritical
    End If
    If CBool(rs.State And adStateOpen) Then rs.Close
    Set rs = Nothing


'cnn.Close
'cnn.Open "Provider=IBMDA400;Data Source=MASLANDAS400;", "PCUSER", "PCUSER"

Application.StatusBar = "Fabrica Download in Progress......."

sSql = "SELECT G1STYL, ROUND(SUM(((G1CLTF*12)+G1CLTI)*((G1CWTF*12)+G1CWTI)/1296),0) as SQYD, COUNT(G1ROLL) AS ROLLS"
sSql = sSql & " from cams.GIP010"
sSql = sSql & " WHERE (G1WHSE='39' OR G1WHSE='59') AND G1ACT<>7 And G1ACT<>9 AND G1ATLF>1 AND G1CLR='' AND G1CLTF>=25 AND G1SCLR<'1' AND G1DDTE<1 " & _
                "AND G1DPRT<>'Y' AND G1DLOT<'1' AND G1LOC<>'LOST' AND G1QLTY <> 7 AND G1QLTY <> 5"
sSql = sSql & " Group by G1STYL"
'sSql = sSql & " ORDER BY SKU"
'MsgBox sSql
cmd400.CommandText = sSql
Set rs = cmd400.Execute
    If Not rs.EOF Then
Application.StatusBar = "Fabrica Inventory..." & counter
                    ActiveWorkbook.Sheets("DATA").Range("E2").CopyFromRecordset rs
                    rs.Close
                    With ActiveWorkbook.Sheets("DATA").Range("E1:G1")
                        .Value = Array("STYLE", "SQYDS", "ROLLS")
                        .Font.Bold = True
                    End With
                    ActiveWorkbook.Sheets("DATA").UsedRange.EntireColumn.AutoFit
                    ActiveWorkbook.Activate
                    ActiveWorkbook.Sheets("DATA").Activate
                    ActiveWorkbook.Sheets("DATA").Range("A1").Activate
    Else
'        MsgBox "Error: No Rolls in WH 37.", vbCritical
    End If
    If CBool(rs.State And adStateOpen) Then rs.Close
    Set rs = Nothing
    
Application.StatusBar = "WIP Download in Progress......."

sSql = "SELECT Y7STYL, (ROUND(SUM(((Y7FTSC-Y7FTFT)*12)*((Y7WTHF*12)+Y7WTHI))/1296,0))"
sSql = sSql & " from cams.YAP070"
sSql = sSql & " WHERE Y7ACT = 0  AND Y7CLR = ''"
sSql = sSql & " Group by Y7STYL"


cmd400.CommandText = sSql
Set rs = cmd400.Execute
    If Not rs.EOF Then
Application.StatusBar = "Fabrica Inventory..." & counter
                    ActiveWorkbook.Sheets("DATA").Range("AF2").CopyFromRecordset rs
                    rs.Close
                    With ActiveWorkbook.Sheets("DATA").Range("AF1:AG1")
                        .Value = Array("STYLE", "SQYDS")
                        .Font.Bold = True
                    End With
                    ActiveWorkbook.Sheets("DATA").UsedRange.EntireColumn.AutoFit
                    ActiveWorkbook.Activate
                    ActiveWorkbook.Sheets("DATA").Activate
                    ActiveWorkbook.Sheets("DATA").Range("A1").Activate
    Else
'        MsgBox "Error: No Rolls in WH 37.", vbCritical
    End If
    If CBool(rs.State And adStateOpen) Then rs.Close
    Set rs = Nothing
    
        
    
    
    
    
    
    
cnn.Close


Application.StatusBar = "Downloads Complete"
Application.StatusBar = ""

End Sub
Sub DownloadSalesGreigeAndInv()

    Dim cnn As New ADODB.Connection
    Dim cmd400 As New ADODB.Command
    Dim rs As New ADODB.Recordset
    Dim sSql As String
    cnn.Open "Provider=IBMDA400;Data Source=TDG-SA-DTS;"
    cmd400.ActiveConnection = cnn
    
    On Error Resume Next
        cmd400.CommandText = "DROP TABLE QTEMP.STYLES"
        cmd400.Execute
        cmd400.CommandText = "DROP VIEW QTEMP.ASTYLES"
        cmd400.Execute
        cmd400.CommandText = "DROP VIEW QTEMP.SQYDS"
        cmd400.Execute
    On Error GoTo 0
    
    
    sSql = "CREATE TABLE QTEMP.STYLES( "
    sSql = sSql & "SROW DEC(4,0),"
    sSql = sSql & "STYLE CHAR(5))"
    cmd400.CommandText = sSql
    cmd400.Execute
    

    
    Dim si As Worksheet, data As Worksheet
    Set si = ThisWorkbook.Worksheets("Inventory")
    Set data = ThisWorkbook.Worksheets("Data")
    Dim i As Long
    i = 5
    Dim sDate As Long, eDate As Long
    eDate = CLng(DateTime.Date) - 366 - 4
    sDate = eDate - 91
    
    
    Do Until si.Range("A" & i).Value = ""
        sSql = "INSERT INTO QTEMP.STYLES(STYLE, SROW) "
        sSql = sSql & " VALUES("
        sSql = sSql & " '" & si.Range("A" & i).Value & "', "
        sSql = sSql & i - 4 & ")"
        cmd400.CommandText = sSql
        cmd400.Execute
        i = i + 1
    Loop
    i = i - 1
    
    sSql = " CREATE VIEW QTEMP.ASTYLES(ASTYLE, OSTYLE, ACLR) AS "
    sSql = sSql & " SELECT STYLE, STYLE, '' FROM QTEMP.STYLES "
    sSql = sSql & " UNION ALL "
    sSql = sSql & " SELECT DISTINCT FXSTYL, STYLE, FXCLR "
    sSql = sSql & " FROM CAMS.FIP028 "
    sSql = sSql & " INNER JOIN QTEMP.STYLES "
    sSql = sSql & " ON FXOSTY = STYLE "
    cmd400.CommandText = sSql
    cmd400.Execute
    

    
    sSql = "CREATE VIEW QTEMP.SYDS AS "
    sSql = sSql & " SELECT  DISTINCT OSTYLE AS SSTYLE, ASTYLE, ACLR, S1ROLL, SUM(S1SQYD) AS YDS,'1' AS RUN "
    sSql = sSql & " FROM QTEMP.ASTYLES "
    sSql = sSql & " LEFT OUTER JOIN CAMS.SAP400 "
    sSql = sSql & " ON ASTYLE = S1ISTY "
    sSql = sSql & " AND ACLR = S1ICLR "
    sSql = sSql & " AND S1IJUL BETWEEN " & sDate & " AND " & eDate
    sSql = sSql & " AND S1LPRC > 0 "
    sSql = sSql & " AND S1WHSE IN ('59','06','BC','03','01','80')"
    sSql = sSql & " AND S1CRIN  = 'I' "
    sSql = sSql & " WHERE NOT EXISTS(SELECT C1INHS FROM CAMS.CIP010 "
    sSql = sSql & " WHERE C1CST# = S1CST1"
    sSql = sSql & " AND C1INHS = 'Y') "
    sSql = sSql & " GROUP BY OSTYLE,ASTYLE,ACLR,S1ROLL "
    sSql = sSql & " UNION ALL "
    sSql = sSql & " SELECT  DISTINCT OSTYLE AS SSTYLE, ASTYLE,ACLR, S1ROLL,SUM(S1SQYD) AS YDS,'2' AS RUN "
    sSql = sSql & " FROM QTEMP.ASTYLES "
    sSql = sSql & " LEFT OUTER JOIN CAMS.SAP400 "
    sSql = sSql & " ON ASTYLE = S1ISTY "
    sSql = sSql & " AND ACLR = '' "
    sSql = sSql & " AND S1IJUL BETWEEN " & sDate & " AND " & eDate
    sSql = sSql & " AND S1LPRC > 0 "
    sSql = sSql & " AND S1WHSE IN ('59','06','BC','03','01','80')"
    sSql = sSql & " AND S1CRIN  = 'I' "
    sSql = sSql & " WHERE NOT EXISTS(SELECT C1INHS FROM CAMS.CIP010 "
    sSql = sSql & " WHERE C1CST# = S1CST1"
    sSql = sSql & " AND C1INHS = 'Y') "
    sSql = sSql & " AND NOT EXISTS(SELECT ACLR FROM QTEMP.ASTYLES AS CHK "
    sSql = sSql & " WHERE CHK.ASTYLE = S1ISTY "
    sSql = sSql & " AND CHK.ACLR = S1ICLR)"
    sSql = sSql & " GROUP BY OSTYLE,ASTYLE,ACLR,S1ROLL "
    cmd400.CommandText = sSql
    cmd400.Execute
    
    'cmd400.CommandText = "SELECT * FROM QTEMP.SYDS"
    'Set rs = cmd400.Execute
    'Sheet4.Range("i:x").ClearContents
    'Sheet4.Range("I2").CopyFromRecordset rs
    
    sSql = "SELECT SSTYLE, SUM(YDS)/13 "
    sSql = sSql & " FROM QTEMP.STYLES"
    sSql = sSql & " LEFT OUTER JOIN QTEMP.SYDS "
    sSql = sSql & " ON STYLE = SSTYLE "
    sSql = sSql & " GROUP BY  SSTYLE "
    cmd400.CommandText = sSql
    Set rs = cmd400.Execute
    
    
    data.Range("U:V").ClearContents
    data.Range("U2").CopyFromRecordset rs
    data.Range("U1:V1").Value = Array("Style", "Weekly Usage")
    
    
    sSql = "SELECT  SUM(G1CLTF + CAST(G1CLTI/12 AS DEC(7,3))) "
    sSql = sSql & " FROM QTEMP.STYLES"
    sSql = sSql & " LEFT OUTER JOIN CAMS.GIL010 "
    sSql = sSql & " ON STYLE = G1STYL "
    'sSql = sSql & " AND G1CLTF > " & si.Range("i2").Value
    sSql = sSql & " AND G1WHSE IN('59')"
    sSql = sSql & " AND G1ACT = 0 "
    sSql = sSql & " AND G1CLR = '' "
    'sSql = sSql & " AND G1LOC NOT LIKE 'M%' "
    sSql = sSql & " GROUP BY SROW, STYLE "
    sSql = sSql & " ORDER BY SROW "
    'cmd400.CommandText = sSql
    'Set rs = cmd400.Execute
    
    'si.Range("C6").CopyFromRecordset rs
    
    
    On Error Resume Next
        cmd400.CommandText = "DROP TABLE QTEMP.STYLES"
        cmd400.Execute
        cmd400.CommandText = "DROP VIEW QTEMP.ASTYLES"
        cmd400.Execute
        cmd400.CommandText = "DROP VIEW QTEMP.SQYDS"
        cmd400.Execute
    On Error GoTo 0
    
    
    Set rs = Nothing
    cnn.Close



End Sub

Sub SalesData()
Dim SalesData As Variant, rngSalesData As Range, SampleStyles As Variant, rngSamples As Range
Dim i As Long, t As Long, WsSheet As Worksheet, Drops As Variant, rngDrops As Range, Styles As Variant
Dim rngStyles As Range, SampleItem As Boolean, DroppedItem As Boolean, SalesItem As Boolean
Dim TocarreSales As Double, TocarreIndole As Double, Vibe As Double, ParkAve As Double
Dim Bandala As Double, Texere As Double, Capari As Double, Cheviot As Double
Dim ArtificialDemand As Variant, rngArtificialDemand As Range, ArtificialThere As Boolean

'Call CopyPads
ArtificialThere = False

ActiveWorkbook.Sheets("DATA").Activate
ActiveWorkbook.Sheets("DATA").Range("U2:V2").Select
ActiveWorkbook.Sheets("DATA").Range(Selection, Selection.End(xlDown)).Select
With Selection
    Set rngSalesData = Selection
End With
SalesData = rngSalesData.Value
ActiveWorkbook.Sheets("DATA").Range("A1").Activate

ActiveWorkbook.Sheets("Tables").Activate
ActiveWorkbook.Sheets("Tables").Range("A3:B3").Select
ActiveWorkbook.Sheets("Tables").Range(Selection, Selection.End(xlDown)).Select
With Selection
    Set rngSamples = Selection
End With
SampleStyles = rngSamples.Value

ActiveWorkbook.Sheets("Tables").Activate
ActiveWorkbook.Sheets("Tables").Range("D3:E3").Select
ActiveWorkbook.Sheets("Tables").Range(Selection, Selection.End(xlDown)).Select
With Selection
    Set rngDrops = Selection
End With
Drops = rngDrops.Value

ActiveWorkbook.Sheets("Tables").Range("N3").Activate
If ActiveCell.Value <> "" Then
    ArtificialThere = True
    If ActiveCell.Offset(1, 0).Value = "" Then
        ActiveWorkbook.Sheets("Tables").Range("N3:O3").Select
    Else
        ActiveWorkbook.Sheets("Tables").Range("N3:O3").Select
        ActiveWorkbook.Sheets("Tables").Range(Selection, Selection.End(xlDown)).Select
    End If
    With Selection
        Set rngArtificialDemand = Selection
    End With
    ArtificialDemand = rngArtificialDemand.Value
End If
ActiveWorkbook.Sheets("Tables").Range("A1").Activate



ActiveWorkbook.Sheets("INVENTORY").Activate
Set WsSheet = ActiveSheet
WsSheet.Range("A5:G5").Select
WsSheet.Range(Selection, Selection.End(xlDown)).Select
With Selection
    Set rngStyles = Selection
End With
Styles = rngStyles.Value
TocarreSales = 0

If ArtificialThere = True Then
    For i = LBound(ArtificialDemand) To UBound(ArtificialDemand)
        If CStr(ArtificialDemand(i, 1)) = "9527" Then
            i = i
        End If
        For t = LBound(SalesData) To UBound(SalesData)
            If SalesData(t, 1) = "9527" Then
                t = t
            End If
            If CStr(SalesData(t, 1)) = CStr(ArtificialDemand(i, 1)) Then
                SalesData(t, 2) = ArtificialDemand(i, 2)
                Exit For
            End If
        Next t
    Next i
End If


For i = LBound(SalesData) To UBound(SalesData)
    If SalesData(i, 1) = "9390" Then
        TocarreSales = SalesData(i, 2)
    End If
    If SalesData(i, 1) = "9411" Then
        TocarreIndole = SalesData(i, 2)
    End If
    If SalesData(i, 1) = "9352" Then
        Bandala = SalesData(i, 2)
    End If
    If SalesData(i, 1) = "7214" Then
        Texere = SalesData(i, 2)
    End If
    If SalesData(i, 1) = "7236" Then
        Capari = SalesData(i, 2)
    End If
    If SalesData(i, 1) = "7237" Then
        Cheviot = SalesData(i, 2)
    End If
    If SalesData(i, 1) = "7221" Then
        Vibe = SalesData(i, 2)
    End If
    If SalesData(i, 1) = "9385" Then
        ParkAve = SalesData(i, 2)
    End If
Next i

For i = LBound(SalesData) To UBound(SalesData)
    If SalesData(i, 1) = "9390" Then
        SalesData(i, 2) = TocarreSales + TocarreIndole
    End If
    If SalesData(i, 1) = "9352" Then
        SalesData(i, 2) = Bandala + Texere
    End If
    If SalesData(i, 1) = "7236" Then
        SalesData(i, 2) = Capari + Cheviot
    End If
    If SalesData(i, 1) = "7221" Then
        SalesData(i, 2) = Vibe + ParkAve
    End If
    
Next i

For i = LBound(Styles) To UBound(Styles)
    SampleItem = False
    DroppedItem = False
    SalesItem = False
    If Styles(i, 1) = "9527" Then
        i = i
    End If
    For t = LBound(SampleStyles) To UBound(SampleStyles)
        If Styles(i, 1) = SampleStyles(t, 1) Then
            SampleItem = True
            Styles(i, 7) = "Samples"
            Exit For
        End If
    Next t
    
    If SampleItem = False Then
        For t = LBound(Drops) To UBound(Drops)
            If Styles(i, 1) = Drops(t, 1) Then
                DroppedItem = True
                Styles(i, 7) = "Drop Listed"
                Exit For
            End If
        Next t
    End If
    
    If SampleItem = False And DroppedItem = False Then
        For t = LBound(SalesData) To UBound(SalesData)
            If Styles(i, 1) = "G5236" Then
                If t = 294 Then
                    i = i
                End If
            End If
            
            If CStr(Styles(i, 1)) = CStr(SalesData(t, 1)) Then
                SalesItem = True
                Styles(i, 7) = SalesData(t, 2)
                Exit For
            Else
                If Len(Styles(i, 1)) >= 4 Then
                    Styles(i, 7) = 0
                End If
            End If
        Next t
    End If

Next i
WsSheet.Range("A5:G" & (i + 3)).Value = Styles
End Sub





