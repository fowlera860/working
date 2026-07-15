let
    Source =  Excel.CurrentWorkbook(){[Name="Folder_Path"]}[Content]{0}[Column1]
in
    Source