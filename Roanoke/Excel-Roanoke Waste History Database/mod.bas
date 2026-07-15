Sub AddRecord()
    ThisWorkbook.RefreshAll
    Do While Application.CalculationState <> xlDone
        DoEvents ' Yield to Excel so it can finish calculations
    Loop
        
    Dim data As Worksheet, database As Worksheet
    Set data = ThisWorkbook.Worksheets("Settings")
    Set database = ThisWorkbook.Worksheets("Database")
    
    Dim r As Long, c As Integer, d As Integer
    r = 2

    
    'find matching date, or next empty record
    Do Until database.Range("A" & r).Value = data.Range("B3").Value Or database.Range("A" & r).Value = ""
        r = r + 1
    Loop
    
    'fill static fields
    
    database.Range("A" & r).Value = data.Range("B3").Value
    database.Range("B" & r).Value = data.Range("F2").Value
    database.Range("C" & r).Value = data.Range("F3").Value
    database.Range("D" & r).Value = data.Range("F4").Value
    database.Range("E" & r).Value = data.Range("F5").Value
    database.Range("F" & r).Value = data.Range("F6").Value
    database.Range("G" & r).Value = data.Range("F7").Value
    database.Range("H" & r).Value = data.Range("F8").Value
    
    'fill dynamic fields
    d = 2
    Do Until data.Range("I" & d).Value = ""
        c = 9
        Do Until database.Cells(1, c).Value = data.Range("I" & d).Value Or database.Cells(1, c).Value = ""
            c = c + 1
        Loop
        If database.Cells(1, c).Value = "" Then
            database.Cells(1, c).Value = data.Range("I" & d).Value
        End If
        database.Cells(r, c).Value = data.Range("L" & d).Value2
        d = d + 1
    Loop
    
End Sub

Sub RunBackReports()
    Dim data As Worksheet
    Set data = ThisWorkbook.Worksheets("Settings")
    Dim startdate As Date, WeekEndingDate As Date
    startdate = #1/7/2023#
    'increment start date to saturday to make sure we start on a saturday as weekending value for report
    WeekEndingDate = startdate
    Do Until Weekday(startdate) = 7
        WeekEndingDate = DateAdd("d", 1, WeekEndingDate)
    Loop
    Do Until WeekEndingDate > Now()
        Range("B2").Value = WeekEndingDate - 6
        Range("B3").Value = WeekEndingDate

            
        Call AddRecord
        WeekEndingDate = WeekEndingDate + 7
    Loop
    
End Sub
