Option Explicit

Public Sub SettingsLoadButton_Click()
	LoadSettingsFromJson
End Sub

Public Sub SettingsSaveButton_Click()
	SaveSettingsToJson
End Sub

Public Sub LoadSettingsFromJson()
	On Error GoTo ErrHandler
	Dim stepName As String

	stepName = "Read JSONPath"
	Dim jsonPath As String
	jsonPath = GetJsonPath()

	stepName = "Check JSON file exists"
	If Len(Dir$(jsonPath, vbNormal)) = 0 Then
		Err.Raise vbObjectError + 2000, "LoadSettingsFromJson", "JSON file not found: " & jsonPath
	End If

	stepName = "Read JSON text"
	Dim jsonText As String
	jsonText = ReadTextFile(jsonPath)

	stepName = "Parse JSON"
	Dim root As Object
	Set root = ParseJsonText(jsonText)

	stepName = "Get Settings worksheet"
	Dim ws As Worksheet
	Set ws = ThisWorkbook.Worksheets("Settings")

	stepName = "Write headers and clear rows"
	ws.Cells(3, "A").Value = "Section"
	ws.Cells(3, "B").Value = "Key"
	ws.Cells(3, "C").Value = "Value"
	ws.Range("A4:C" & ws.Rows.Count).ClearContents

	stepName = "Flatten JSON"
	Dim rows As Collection
	Set rows = New Collection
	FlattenJsonLeaves root, "", rows

	If rows.Count > 0 Then
		stepName = "Write rows to sheet"
		Dim outputArr() As Variant
		ReDim outputArr(1 To rows.Count, 1 To 3)

		Dim i As Long
		For i = 1 To rows.Count
			Dim item As Variant
			item = rows(i)
			outputArr(i, 1) = item(0)
			outputArr(i, 2) = item(1)
			outputArr(i, 3) = item(2)
		Next i

		ws.Range("A4").Resize(rows.Count, 3).Value = outputArr
	End If

	MsgBox "Settings loaded from JSON successfully.", vbInformation
	Exit Sub

ErrHandler:
	MsgBox "Load failed at step: " & stepName & vbCrLf & Err.Description, vbCritical
End Sub

Public Sub SaveSettingsToJson()
	On Error GoTo ErrHandler

	Dim jsonPath As String
	jsonPath = GetJsonPath()

	If Len(Dir$(jsonPath, vbNormal)) = 0 Then
		Err.Raise vbObjectError + 2100, "SaveSettingsToJson", "JSON file not found: " & jsonPath
	End If

	Dim jsonText As String
	jsonText = ReadTextFile(jsonPath)

	Dim root As Object
	Set root = ParseJsonText(jsonText)

	Dim expected As Object
	Set expected = CreateObject("Scripting.Dictionary")
	BuildLeafMap root, "", expected

	Dim ws As Worksheet
	Set ws = ThisWorkbook.Worksheets("Settings")

	Dim lastRow As Long
	lastRow = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row
	If lastRow < 4 Then
		Err.Raise vbObjectError + 2101, "SaveSettingsToJson", "No settings rows found on Settings sheet."
	End If

	Dim provided As Object
	Set provided = CreateObject("Scripting.Dictionary")

	Dim r As Long
	For r = 4 To lastRow
		Dim sectionName As String
		Dim keyName As String
		Dim valueText As String

		sectionName = Trim$(CStr(ws.Cells(r, "A").Value))
		keyName = Trim$(CStr(ws.Cells(r, "B").Value))
		valueText = CStr(ws.Cells(r, "C").Value)

		If Len(sectionName) = 0 And Len(keyName) = 0 Then
			If Len(Trim$(valueText)) > 0 Then
				Err.Raise vbObjectError + 2102, "SaveSettingsToJson", "Row " & r & " has value but no Section/Key."
			End If
			GoTo NextRow
		End If

		If Len(sectionName) = 0 Or Len(keyName) = 0 Then
			Err.Raise vbObjectError + 2103, "SaveSettingsToJson", "Row " & r & " must contain both Section and Key."
		End If

		Dim pathKey As String
		pathKey = sectionName & "." & keyName

		If provided.Exists(pathKey) Then
			Err.Raise vbObjectError + 2104, "SaveSettingsToJson", "Duplicate setting found: " & pathKey
		End If

		provided.Add pathKey, valueText

NextRow:
	Next r

	ValidateSheetStructure expected, provided

	Dim p As Variant
	For Each p In expected.Keys
		Dim meta As Variant
		meta = expected(p)

		Dim originalType As String
		originalType = CStr(meta(0))

		Dim newValue As Variant
		newValue = CoerceValueToType(CStr(provided(p)), originalType, CStr(p))

		SetLeafValue root, CStr(p), newValue
	Next p

	Dim outputText As String
	outputText = StringifyJson(root, 0)

	WriteTextFile jsonPath, outputText

	MsgBox "Settings saved to JSON successfully.", vbInformation
	Exit Sub

ErrHandler:
	MsgBox "Save failed: " & Err.Description, vbCritical
End Sub

Private Sub ValidateSheetStructure(ByVal expected As Object, ByVal provided As Object)
	If expected.Count <> provided.Count Then
		Err.Raise vbObjectError + 2200, "ValidateSheetStructure", _
				  "Sheet structure mismatch. Expected " & expected.Count & " settings but found " & provided.Count & "."
	End If

	Dim k As Variant
	For Each k In expected.Keys
		If Not provided.Exists(k) Then
			Err.Raise vbObjectError + 2201, "ValidateSheetStructure", _
					  "Missing required setting: " & CStr(k)
		End If
	Next k

	For Each k In provided.Keys
		If Not expected.Exists(k) Then
			Err.Raise vbObjectError + 2202, "ValidateSheetStructure", _
					  "Unexpected setting found (keys/structure cannot change): " & CStr(k)
		End If
	Next k
End Sub

Private Function GetJsonPath() As String
	On Error GoTo ErrHandler

	Dim nm As Name
	Set nm = ThisWorkbook.Names("JSONPath")

	Dim pathValue As String
	pathValue = CStr(nm.RefersToRange.Value)
	pathValue = Trim$(pathValue)

	If Len(pathValue) = 0 Then
		Err.Raise vbObjectError + 2300, "GetJsonPath", "Named range JSONPath is blank."
	End If

	GetJsonPath = pathValue
	Exit Function

ErrHandler:
	Err.Raise vbObjectError + 2301, "GetJsonPath", "Could not read named range JSONPath."
End Function

Private Function ReadTextFile(ByVal filePath As String) As String
	Dim ff As Integer
	ff = FreeFile

	Open filePath For Input As #ff
	ReadTextFile = Input$(LOF(ff), #ff)
	Close #ff
End Function

Private Sub WriteTextFile(ByVal filePath As String, ByVal content As String)
	Dim ff As Integer
	ff = FreeFile

	Open filePath For Output As #ff
	Print #ff, content;
	Close #ff
End Sub

Private Sub FlattenJsonLeaves(ByVal node As Variant, ByVal parentPath As String, ByRef rows As Collection)
	If IsObject(node) Then
		If TypeName(node) = "Dictionary" Then
			Dim k As Variant
			For Each k In node.Keys
				Dim childPath As String
				If Len(parentPath) = 0 Then
					childPath = CStr(k)
				Else
					childPath = parentPath & "." & CStr(k)
				End If

				If IsObject(node(k)) Then
					FlattenJsonLeaves node(k), childPath, rows
				Else
					Dim sectionName As String
					Dim keyName As String
					SplitPath childPath, sectionName, keyName
					rows.Add Array(sectionName, keyName, ValueToCellText(node(k)))
				End If
			Next k
		ElseIf TypeName(node) = "Collection" Then
			Err.Raise vbObjectError + 2400, "FlattenJsonLeaves", "JSON arrays are not supported in Settings JSON."
		End If
	Else
		Err.Raise vbObjectError + 2401, "FlattenJsonLeaves", "Root JSON must be an object."
	End If
End Sub

Private Sub BuildLeafMap(ByVal node As Variant, ByVal parentPath As String, ByRef leafMap As Object)
	If IsObject(node) Then
		If TypeName(node) = "Dictionary" Then
			Dim k As Variant
			For Each k In node.Keys
				Dim childPath As String
				If Len(parentPath) = 0 Then
					childPath = CStr(k)
				Else
					childPath = parentPath & "." & CStr(k)
				End If

				If IsObject(node(k)) Then
					BuildLeafMap node(k), childPath, leafMap
				Else
					leafMap.Add childPath, Array(GetValueTypeName(node(k)), node(k))
				End If
			Next k
		ElseIf TypeName(node) = "Collection" Then
			Err.Raise vbObjectError + 2500, "BuildLeafMap", "JSON arrays are not supported in Settings JSON."
		End If
	Else
		Err.Raise vbObjectError + 2501, "BuildLeafMap", "Root JSON must be an object."
	End If
End Sub

Private Sub SetLeafValue(ByRef root As Object, ByVal fullPath As String, ByVal newValue As Variant)
	Dim parts() As String
	parts = Split(fullPath, ".")

	If UBound(parts) < 1 Then
		Err.Raise vbObjectError + 2600, "SetLeafValue", "Invalid path: " & fullPath
	End If

	Dim i As Long
	Dim cur As Object
	Set cur = root

	For i = LBound(parts) To UBound(parts) - 1
		If Not cur.Exists(parts(i)) Then
			Err.Raise vbObjectError + 2601, "SetLeafValue", "Path segment not found: " & parts(i)
		End If
		If Not IsObject(cur(parts(i))) Then
			Err.Raise vbObjectError + 2602, "SetLeafValue", "Path segment is not an object: " & parts(i)
		End If
		Set cur = cur(parts(i))
	Next i

	Dim leafKey As String
	leafKey = parts(UBound(parts))

	If Not cur.Exists(leafKey) Then
		Err.Raise vbObjectError + 2603, "SetLeafValue", "Leaf key not found: " & leafKey
	End If

	cur(leafKey) = newValue
End Sub

Private Function CoerceValueToType(ByVal textValue As String, ByVal expectedType As String, ByVal pathKey As String) As Variant
	Dim trimmed As String
	trimmed = Trim$(textValue)

	Select Case LCase$(expectedType)
		Case "string"
			CoerceValueToType = textValue

		Case "number"
			If Len(trimmed) = 0 Then
				Err.Raise vbObjectError + 2700, "CoerceValueToType", "Numeric value required for " & pathKey
			End If
			If Not IsNumeric(trimmed) Then
				Err.Raise vbObjectError + 2701, "CoerceValueToType", "Invalid number for " & pathKey & ": " & textValue
			End If
			CoerceValueToType = CDbl(trimmed)

		Case "boolean"
			Select Case LCase$(trimmed)
				Case "true", "1", "yes", "y"
					CoerceValueToType = True
				Case "false", "0", "no", "n"
					CoerceValueToType = False
				Case Else
					Err.Raise vbObjectError + 2702, "CoerceValueToType", "Invalid boolean for " & pathKey & ": " & textValue
			End Select

		Case "null"
			If Len(trimmed) > 0 And LCase$(trimmed) <> "null" Then
				Err.Raise vbObjectError + 2703, "CoerceValueToType", "Only NULL is allowed for " & pathKey
			End If
			CoerceValueToType = Null

		Case Else
			Err.Raise vbObjectError + 2704, "CoerceValueToType", "Unsupported JSON value type for " & pathKey & ": " & expectedType
	End Select
End Function

Private Function GetValueTypeName(ByVal v As Variant) As String
	If IsNull(v) Then
		GetValueTypeName = "null"
	ElseIf VarType(v) = vbBoolean Then
		GetValueTypeName = "boolean"
	ElseIf IsNumeric(v) Then
		GetValueTypeName = "number"
	Else
		GetValueTypeName = "string"
	End If
End Function

Private Function ValueToCellText(ByVal v As Variant) As String
	If IsNull(v) Then
		ValueToCellText = "null"
	ElseIf VarType(v) = vbBoolean Then
		If v = True Then
			ValueToCellText = "true"
		Else
			ValueToCellText = "false"
		End If
	Else
		ValueToCellText = CStr(v)
	End If
End Function

Private Sub SplitPath(ByVal fullPath As String, ByRef sectionName As String, ByRef keyName As String)
	Dim pos As Long
	pos = InStrRev(fullPath, ".")

	If pos <= 0 Then
		sectionName = ""
		keyName = fullPath
	Else
		sectionName = Left$(fullPath, pos - 1)
		keyName = Mid$(fullPath, pos + 1)
	End If
End Sub

' =========================
' Minimal JSON parser/writer
' =========================

Private Function ParseJsonText(ByVal jsonText As String) As Object
	Dim p As Long
	p = 1
	SkipWs jsonText, p

	If p > Len(jsonText) Or Mid$(jsonText, p, 1) <> "{" Then
		Err.Raise vbObjectError + 2802, "ParseJsonText", "Root JSON must be an object."
	End If

	Set ParseJsonText = ParseJsonObject(jsonText, p)

	SkipWs jsonText, p
	If p <= Len(jsonText) Then
		Err.Raise vbObjectError + 2800, "ParseJsonText", "Unexpected trailing content in JSON."
	End If
End Function

Private Function ParseJsonValue(ByVal s As String, ByRef p As Long) As Variant
	SkipWs s, p
	If p > Len(s) Then
		Err.Raise vbObjectError + 2810, "ParseJsonValue", "Unexpected end of JSON."
	End If

	Dim ch As String
	ch = Mid$(s, p, 1)

	Select Case ch
		Case "{"
			Set ParseJsonValue = ParseJsonObject(s, p)
		Case "["
			Set ParseJsonValue = ParseJsonArray(s, p)
		Case """"
			ParseJsonValue = ParseJsonString(s, p)
		Case "t", "f"
			ParseJsonValue = ParseJsonBoolean(s, p)
		Case "n"
			ParseJsonNull s, p
			ParseJsonValue = Null
		Case Else
			If ch = "-" Or (ch >= "0" And ch <= "9") Then
				ParseJsonValue = ParseJsonNumber(s, p)
			Else
				Err.Raise vbObjectError + 2811, "ParseJsonValue", "Invalid JSON token at position " & p
			End If
	End Select
End Function

Private Function ParseJsonObject(ByVal s As String, ByRef p As Long) As Object
	Dim dict As Object
	Set dict = CreateObject("Scripting.Dictionary")

	If Mid$(s, p, 1) <> "{" Then
		Err.Raise vbObjectError + 2820, "ParseJsonObject", "Expected '{' at position " & p
	End If
	p = p + 1

	SkipWs s, p
	If p <= Len(s) And Mid$(s, p, 1) = "}" Then
		p = p + 1
		Set ParseJsonObject = dict
		Exit Function
	End If

	Do
		SkipWs s, p
		If Mid$(s, p, 1) <> """" Then
			Err.Raise vbObjectError + 2821, "ParseJsonObject", "Expected string key at position " & p
		End If

		Dim key As String
		key = ParseJsonString(s, p)

		SkipWs s, p
		If Mid$(s, p, 1) <> ":" Then
			Err.Raise vbObjectError + 2822, "ParseJsonObject", "Expected ':' after key at position " & p
		End If
		p = p + 1

		If dict.Exists(key) Then
			Err.Raise vbObjectError + 2823, "ParseJsonObject", "Duplicate key in JSON object: " & key
		End If

		SkipWs s, p
		If p > Len(s) Then
			Err.Raise vbObjectError + 2826, "ParseJsonObject", "Unexpected end after ':' at position " & p
		End If

		Dim valueCh As String
		valueCh = Mid$(s, p, 1)
		Select Case valueCh
			Case "{"
				Dim objVal As Object
				Set objVal = ParseJsonObject(s, p)
				dict.Add key, objVal
			Case "["
				Dim arrVal As Collection
				Set arrVal = ParseJsonArray(s, p)
				dict.Add key, arrVal
			Case """"
				dict.Add key, ParseJsonString(s, p)
			Case "t", "f"
				dict.Add key, ParseJsonBoolean(s, p)
			Case "n"
				ParseJsonNull s, p
				dict.Add key, Null
			Case Else
				If valueCh = "-" Or (valueCh >= "0" And valueCh <= "9") Then
					dict.Add key, ParseJsonNumber(s, p)
				Else
					Err.Raise vbObjectError + 2827, "ParseJsonObject", "Invalid value token at position " & p
				End If
		End Select

		SkipWs s, p
		If p > Len(s) Then
			Err.Raise vbObjectError + 2824, "ParseJsonObject", "Unexpected end in object at position " & p
		End If

		Dim ch As String
		ch = Mid$(s, p, 1)
		If ch = "}" Then
			p = p + 1
			Exit Do
		ElseIf ch = "," Then
			p = p + 1
		Else
			Err.Raise vbObjectError + 2825, "ParseJsonObject", "Expected ',' or '}' at position " & p
		End If
	Loop

	Set ParseJsonObject = dict
End Function

Private Function ParseJsonArray(ByVal s As String, ByRef p As Long) As Collection
	Dim col As New Collection

	If Mid$(s, p, 1) <> "[" Then
		Err.Raise vbObjectError + 2830, "ParseJsonArray", "Expected '[' at position " & p
	End If
	p = p + 1

	SkipWs s, p
	If p <= Len(s) And Mid$(s, p, 1) = "]" Then
		p = p + 1
		Set ParseJsonArray = col
		Exit Function
	End If

	Do
		SkipWs s, p
		If p > Len(s) Then
			Err.Raise vbObjectError + 2833, "ParseJsonArray", "Unexpected end while reading array value."
		End If

		Dim valueCh As String
		valueCh = Mid$(s, p, 1)
		Select Case valueCh
			Case "{"
				Dim objVal As Object
				Set objVal = ParseJsonObject(s, p)
				col.Add objVal
			Case "["
				Dim arrVal As Collection
				Set arrVal = ParseJsonArray(s, p)
				col.Add arrVal
			Case """"
				col.Add ParseJsonString(s, p)
			Case "t", "f"
				col.Add ParseJsonBoolean(s, p)
			Case "n"
				ParseJsonNull s, p
				col.Add Null
			Case Else
				If valueCh = "-" Or (valueCh >= "0" And valueCh <= "9") Then
					col.Add ParseJsonNumber(s, p)
				Else
					Err.Raise vbObjectError + 2834, "ParseJsonArray", "Invalid value token at position " & p
				End If
		End Select

		SkipWs s, p
		If p > Len(s) Then
			Err.Raise vbObjectError + 2831, "ParseJsonArray", "Unexpected end in array at position " & p
		End If

		Dim ch As String
		ch = Mid$(s, p, 1)
		If ch = "]" Then
			p = p + 1
			Exit Do
		ElseIf ch = "," Then
			p = p + 1
		Else
			Err.Raise vbObjectError + 2832, "ParseJsonArray", "Expected ',' or ']' at position " & p
		End If
	Loop

	Set ParseJsonArray = col
End Function

Private Function ParseJsonString(ByVal s As String, ByRef p As Long) As String
	If Mid$(s, p, 1) <> """" Then
		Err.Raise vbObjectError + 2840, "ParseJsonString", "Expected '""' at position " & p
	End If
	p = p + 1

	Dim result As String
	result = ""

	Do While p <= Len(s)
		Dim ch As String
		ch = Mid$(s, p, 1)

		If ch = """" Then
			p = p + 1
			ParseJsonString = result
			Exit Function
		ElseIf ch = "\" Then
			p = p + 1
			If p > Len(s) Then
				Err.Raise vbObjectError + 2841, "ParseJsonString", "Invalid escape at end of string."
			End If

			Dim esc As String
			esc = Mid$(s, p, 1)
			Select Case esc
				Case """": result = result & """"
				Case "\": result = result & "\"
				Case "/": result = result & "/"
				Case "b": result = result & Chr$(8)
				Case "f": result = result & Chr$(12)
				Case "n": result = result & vbLf
				Case "r": result = result & vbCr
				Case "t": result = result & vbTab
				Case "u"
					If p + 4 > Len(s) Then
						Err.Raise vbObjectError + 2842, "ParseJsonString", "Invalid unicode escape."
					End If
					Dim hexCode As String
					hexCode = Mid$(s, p + 1, 4)
					result = result & ChrW$(CLng("&H" & hexCode))
					p = p + 4
				Case Else
					Err.Raise vbObjectError + 2843, "ParseJsonString", "Invalid escape sequence: \" & esc
			End Select
			p = p + 1
		Else
			result = result & ch
			p = p + 1
		End If
	Loop

	Err.Raise vbObjectError + 2844, "ParseJsonString", "Unterminated string literal."
End Function

Private Function ParseJsonNumber(ByVal s As String, ByRef p As Long) As Double
	Dim startPos As Long
	startPos = p

	If Mid$(s, p, 1) = "-" Then p = p + 1

	Do While p <= Len(s) And Mid$(s, p, 1) >= "0" And Mid$(s, p, 1) <= "9"
		p = p + 1
	Loop

	If p <= Len(s) And Mid$(s, p, 1) = "." Then
		p = p + 1
		Do While p <= Len(s) And Mid$(s, p, 1) >= "0" And Mid$(s, p, 1) <= "9"
			p = p + 1
		Loop
	End If

	If p <= Len(s) Then
		Dim e As String
		e = Mid$(s, p, 1)
		If e = "e" Or e = "E" Then
			p = p + 1
			If p <= Len(s) Then
				Dim sign As String
				sign = Mid$(s, p, 1)
				If sign = "+" Or sign = "-" Then p = p + 1
			End If
			Do While p <= Len(s) And Mid$(s, p, 1) >= "0" And Mid$(s, p, 1) <= "9"
				p = p + 1
			Loop
		End If
	End If

	Dim numText As String
	numText = Mid$(s, startPos, p - startPos)
	ParseJsonNumber = CDbl(numText)
End Function

Private Function ParseJsonBoolean(ByVal s As String, ByRef p As Long) As Boolean
	If Mid$(s, p, 4) = "true" Then
		p = p + 4
		ParseJsonBoolean = True
	ElseIf Mid$(s, p, 5) = "false" Then
		p = p + 5
		ParseJsonBoolean = False
	Else
		Err.Raise vbObjectError + 2850, "ParseJsonBoolean", "Invalid boolean at position " & p
	End If
End Function

Private Sub ParseJsonNull(ByVal s As String, ByRef p As Long)
	If Mid$(s, p, 4) <> "null" Then
		Err.Raise vbObjectError + 2860, "ParseJsonNull", "Invalid null at position " & p
	End If
	p = p + 4
End Sub

Private Sub SkipWs(ByVal s As String, ByRef p As Long)
	Do While p <= Len(s)
		Select Case Mid$(s, p, 1)
			Case " ", vbTab, vbCr, vbLf
				p = p + 1
			Case Else
				Exit Do
		End Select
	Loop
End Sub

Private Function StringifyJson(ByVal node As Variant, ByVal indentLevel As Long) As String
	If IsObject(node) Then
		Select Case TypeName(node)
			Case "Dictionary"
				StringifyJson = StringifyObject(node, indentLevel)
			Case "Collection"
				StringifyJson = StringifyArray(node, indentLevel)
			Case Else
				Err.Raise vbObjectError + 2870, "StringifyJson", "Unsupported object type: " & TypeName(node)
		End Select
	Else
		StringifyJson = StringifyPrimitive(node)
	End If
End Function

Private Function StringifyObject(ByVal dict As Object, ByVal indentLevel As Long) As String
	Dim indent As String
	indent = String$(indentLevel * 2, " ")

	Dim childIndent As String
	childIndent = String$((indentLevel + 1) * 2, " ")

	If dict.Count = 0 Then
		StringifyObject = "{}"
		Exit Function
	End If

	Dim parts() As String
	ReDim parts(0 To dict.Count - 1)

	Dim i As Long
	i = 0

	Dim k As Variant
	For Each k In dict.Keys
		parts(i) = childIndent & """" & EscapeJsonString(CStr(k)) & """: " & StringifyJson(dict(k), indentLevel + 1)
		i = i + 1
	Next k

	StringifyObject = "{" & vbCrLf & Join(parts, "," & vbCrLf) & vbCrLf & indent & "}"
End Function

Private Function StringifyArray(ByVal col As Collection, ByVal indentLevel As Long) As String
	Dim indent As String
	indent = String$(indentLevel * 2, " ")

	Dim childIndent As String
	childIndent = String$((indentLevel + 1) * 2, " ")

	If col.Count = 0 Then
		StringifyArray = "[]"
		Exit Function
	End If

	Dim parts() As String
	ReDim parts(0 To col.Count - 1)

	Dim i As Long
	For i = 1 To col.Count
		parts(i - 1) = childIndent & StringifyJson(col(i), indentLevel + 1)
	Next i

	StringifyArray = "[" & vbCrLf & Join(parts, "," & vbCrLf) & vbCrLf & indent & "]"
End Function

Private Function StringifyPrimitive(ByVal v As Variant) As String
	If IsNull(v) Then
		StringifyPrimitive = "null"
	ElseIf VarType(v) = vbBoolean Then
		If v = True Then
			StringifyPrimitive = "true"
		Else
			StringifyPrimitive = "false"
		End If
	ElseIf IsNumeric(v) Then
		StringifyPrimitive = Replace(CStr(v), ",", "")
	Else
		StringifyPrimitive = """" & EscapeJsonString(CStr(v)) & """"
	End If
End Function

Private Function EscapeJsonString(ByVal text As String) As String
	Dim s As String
	s = text
	s = Replace(s, "\", "\\")
	s = Replace(s, """", "\" & """")
	s = Replace(s, vbCrLf, "\n")
	s = Replace(s, vbCr, "\n")
	s = Replace(s, vbLf, "\n")
	s = Replace(s, vbTab, "\t")
	EscapeJsonString = s
End Function
