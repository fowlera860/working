let
	    SQL = "
	        SELECT DISTINCT 
				F2STYL as Style, 
				MIN(F2SDSC) as StyleName,
				MIN(FIP715.F7CMCH) as Mch,
				MIN(G3DESC) as MchName,
				MIN(G3WHSE) as PLANT
			FROM CAMS.FIP020
			LEFT OUTER JOIN CAMS.FIP712 as FIP712
				ON F2STYL = FIP712.F7STYL
				AND FIP712.F7ACT = 'Y'
				AND FIP712.F7APPVD = 'Y'
				AND FIP712.F7PCODE = 'TFT'
			LEFT OUTER JOIN CAMS.FIP715 as FIP715
				ON FIP715.F7STYL = F2STYL
				AND FIP715.F7CLR = ''
				AND FIP715.F7SPEC# = FIP712.F7SPEC#
			LEFT OUTER JOIN CAMS.GIP030
				ON RTRIM(G3MACH) = RTRIM(FIP715.F7CMCH)
            WHERE F2CLR = ''
            AND F2STYL IN ( " & Q_StyleFilter & ")
			
			GROUP BY F2STYL, G3WHSE
	    ",
	    Source = Odbc.Query("DRIVER={Client Access ODBC Driver (32-bit)};SYSTEM=TDG-SA-DTS;DBQ=CAMS;DFTPKGLIB=QGPL;LANGUAGEID=ENU;PKG=QGPL/DEFAULT(IBM),2,0,1,0,512;QRYSTGLMT=-1;", SQL),
	    // Force F2STYL to text and trim all text columns
	    TypedSource = Table.TransformColumnTypes(Source, {{"STYLE", type text}}),
	    TextColumnList = List.Select(Table.ColumnNames(TypedSource), each Value.Is(Table.Column(TypedSource, _){0}, type text)),
	    CleanSource = Table.TransformColumns(TypedSource, List.Transform(TextColumnList, each {_, Text.Trim})),
    #"Filtered Rows" = Table.SelectRows(CleanSource, each true)
	
	in
	    #"Filtered Rows"