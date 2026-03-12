// Directory
let
    Source = Excel.CurrentWorkbook(){[Name="Directory"]}[Content]{0}[Column1]

in
    Source
