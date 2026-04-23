param (
    [string]$botScript = "run_bot.py"
)

$aiMemoryFile = "logs/ai_memory.json"
$logFile = "logs/crash_dump.log"
$env:PYTHONPATH = "."
$pythonPath = ".\venv\Scripts\python.exe"

Write-Host "--- Qbit-bot Self-Healing System LIVE ---" -ForegroundColor Green

while ($true) {
    Write-Host "LAUNCHING $botScript at $(Get-Date -Format 'HH:mm:ss')..." -ForegroundColor Cyan
    
    # Run the bot and pipe output
    try {
        & $pythonPath $botScript 2>&1 | Tee-Object -FilePath $logFile
    } catch {
        Write-Host "Process interrupted." -ForegroundColor Gray
    }

    # Only consult Gemini if the bot actually crashed (Exit Code != 0)
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 3221225786) { 
        Write-Host "CRASH DETECTED (Code: $LASTEXITCODE). Consulting Gemini..." -ForegroundColor Red
        
        if (Test-Path $logFile) {
            try {
                $errorDetails = Get-Content $logFile | Select-Object -Last 30
                $prompt = "Analyzer Role: Senior Python Support. Review this crash and suggest a fix: $errorDetails"
                
                $geminiFix = $prompt | gemini
                
                $timestamp = Get-Date -Format "HH:mm"
                # Prepare JSON object
                $newInsight = @{
                    time = $timestamp
                    reason = "SELF-HEALING ANALYSIS: $geminiFix"
                }
                
                # Append and save
                if (Test-Path $aiMemoryFile) {
                    $currentMemory = Get-Content $aiMemoryFile | ConvertFrom-Json
                    if ($currentMemory -isnot [array]) { $currentMemory = @($currentMemory) }
                } else { $currentMemory = @() }
                
                $updatedMemory = @($newInsight) + $currentMemory | Select-Object -First 20
                $updatedMemory | ConvertTo-Json -Depth 5 | Out-File -FilePath $aiMemoryFile -Encoding utf8
                Write-Host "FIX LOGGED TO DASHBOARD." -ForegroundColor Yellow
            } catch {
                Write-Host "Gemini CLI busy or error occurred. Skipping analysis." -ForegroundColor Gray
            }
        }
        
        Write-Host "RE-LAUNCHING IN 10 SECONDS..." -ForegroundColor Cyan
        Start-Sleep -Seconds 10
    } else {
        Write-Host "BOT STOPPED (Normal or User). Restarting in 5s..." -ForegroundColor Gray
        Start-Sleep -Seconds 5
    }
}
