Param(
    [Parameter(Mandatory=$true)] [string] $Video,
    [Parameter(Mandatory=$true)] [string] $Subtitle,
    [string] $Source = "Channel",
    [string] $Date = "2024-03-15",
    [string] $Title = "Interview",
    [string] $Url = "https://example.com/clip"
)
.\.venv\Scripts\Activate.ps1
python -m backend.ingest --db backend\db.sqlite3 --video "$Video" --subtitle "$Subtitle" --source "$Source" --date "$Date" --title "$Title" --url "$Url"