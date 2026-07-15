let
    sDate  = Text.From(Number.From(Excel.CurrentWorkbook(){[Name="start_Date"]}[Content]{0}[Column1])-366),
    eDate =  Text.From(Number.From(Excel.CurrentWorkbook(){[Name="end_Date"]}[Content]{0}[Column1])-366),
    sql = "
      SELECT
          A.Y1XJUL + 366 AS Y1XJUL,
          A.Y1PCDE,
          A.Y1YNID,
          SUM(A.Y1NWGT) AS Y1NWGT,
          P.COSTPERLB,
          P.COSTPERLB * SUM(A.Y1NWGT) AS TOTALCOST,
          P.WASTECOSTPERLB,
          P.WASTECOSTPERLB * SUM(A.Y1NWGT) AS WASTECOST,
          CASE
              WHEN P.COSTPERLB IS NULL OR P.COSTPERLB = 0 THEN 0
              ELSE (P.WASTECOSTPERLB * SUM(A.Y1NWGT)) / P.COSTPERLB
          END AS EARNEDWASTELBS
      FROM CAMSY.YAP100 AS A
      LEFT OUTER JOIN CAMSY.YAP020 AS Y2
          ON A.Y1YNID = Y2.Y2YNID
        AND A.Y1YCLR = Y2.Y2YCLR
      LEFT OUTER JOIN (
          SELECT
              P4PTNO,
              P4WHSE,
              SUM(P4COST) AS COSTPERLB,
              SUM(P4WCST) AS WASTECOSTPERLB
          FROM CAMSY.PCP040
          GROUP BY P4PTNO, P4WHSE
      ) AS P
          ON P.P4PTNO = A.Y1YNID
          AND P.P4WHSE = A.Y1WHSE
      WHERE A.Y1XJUL BETWEEN "  & sDate & " AND " & eDate & "
        AND A.Y1WHSE IN ('R1')
        AND A.Y1XTYP = 'P'
        AND A.Y1PCDE IN ('YHS', '012')
      GROUP BY
          A.Y1XJUL,
          A.Y1PCDE,
          A.Y1YNID,
          P.COSTPERLB,
          P.WASTECOSTPERLB
      ",
		Source = Odbc.Query("DRIVER={Client Access ODBC Driver (32-bit)};SYSTEM=TDG-SA-DTS;DBQ=CAMSY;DFTPKGLIB=QGPL;LANGUAGEID=ENU;PKG=QGPL/DEFAULT(IBM),2,0,1,0,512;QRYSTGLMT=-1;", sql),
    ChangedType = Table.TransformColumnTypes(Source,{{"Y1XJUL", type date},{"WASTECOST", Currency.Type}, {"WASTECOSTPERLB", Currency.Type}, {"TOTALCOST", Currency.Type}, {"COSTPERLB", Currency.Type}}),
    TotalProd = List.Sum(ChangedType[Y1NWGT]),
    TotalWaste = Baled_Waste_Total,
    #"Added Custom" = Table.AddColumn(ChangedType, "EstimatedWaste", each [Y1NWGT]/TotalProd * TotalWaste),
    #"Added Custom1" = Table.AddColumn(#"Added Custom", "ActualWasteCost", each [COSTPERLB]*[EstimatedWaste])

in
    #"Added Custom1"