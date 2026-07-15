Attribute VB_Name = "Sheet1"
Attribute VB_Base = "0{00020820-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
Attribute VB_Control = "CommandButton2, 2, 0, MSForms, CommandButton"
Attribute VB_Control = "CommandButton1, 1, 1, MSForms, CommandButton"
Private Sub CommandButton1_Click()
    Application.Calculation = xlCalculationManual
    Dim sDate As Long
    Dim eDate As Long
'    Dim wh As String
'    Dim pro As String, p As Long
'    Dim waste As String
'    waste = ThisWorkbook.Worksheets("Control Panel").Range("C6").Value
    sDate = ThisWorkbook.Worksheets("Control Panel").Range("C3").Value - 366
    eDate = WorksheetFunction.WorkDay(ThisWorkbook.Worksheets("Control Panel").Range("C3").Value, 1) - 366
'    wh = ThisWorkbook.Worksheets("Control Panel").Range("C5").Value
'    pro = "'" & ThisWorkbook.Worksheets("Control Panel").Range("E3").Value & "'"
'    waste = "'" & ThisWorkbook.Worksheets("Control Panel").Range("G3").Value & "'"
'    p = 4
'    Do Until ThisWorkbook.Worksheets("Control Panel").Range("E" & p).Value = ""
'        pro = pro & ", '" & ThisWorkbook.Worksheets("Control Panel").Range("E" & p).Value & "'"
'        p = p + 1
'    Loop
'    p = 4
'    Do Until ThisWorkbook.Worksheets("Control Panel").Range("G" & p).Value = ""
'        waste = waste & ", '" & ThisWorkbook.Worksheets("Control Panel").Range("G" & p).Value & "'"
'        p = p + 1
'    Loop
    Call download(sDate, eDate, "80", "'CUT', 'CBL'", "''")
    Call Parse(sDate)
    Call createReport
    Call CreateSummary
    'Call UploadData
    Application.Calculation = xlCalculationAutomatic
End Sub

Private Sub CommandButton2_Click()
    Call UpdateDailyCutsResults
    ThisWorkbook.Save
End Sub
