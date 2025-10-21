# Fix datetime.utcnow() deprecation warnings

$files = @(
    "src\gaspipe\logging_config.py",
    "src\gaspipe\pipeline.py",
    "tests\test_validate.py"
)

foreach ($file in $files) {
    Write-Host "Fixing $file..." -ForegroundColor Yellow
    
    # Read content
    $content = Get-Content $file -Raw
    
    # Fix imports
    $content = $content -replace 'from datetime import datetime$', 'from datetime import datetime, UTC'
    $content = $content -replace 'from datetime import datetime\r?\n', "from datetime import datetime, UTC`n"
    
    # Fix utcnow() calls
    $content = $content -replace 'datetime\.utcnow\(\)', 'datetime.now(UTC)'
    
    # Special fix for logging_config timestamp with Z suffix
    $content = $content -replace 'datetime\.now\(UTC\)\.isoformat\(\) \+ "Z"', 'datetime.now(UTC).isoformat().replace(''+00:00'', ''Z'')'
    
    # Write back
    Set-Content $file $content -NoNewline
    
    Write-Host "  Done" -ForegroundColor Green
}

Write-Host "`nAll files fixed. Run: pytest tests/ -v" -ForegroundColor Cyan