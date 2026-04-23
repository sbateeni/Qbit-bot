# Robust Profit Analysis Script using Gemini
# This script sends the optimizer report to Gemini and saves the insight for the dashboard.

$reportFile = "logs/optimizer_report.json"
$aiMemoryFile = "logs/ai_memory.json"

if (!(Test-Path $reportFile)) {
    Write-Host "Error: $reportFile not found." -ForegroundColor Red
    exit
}

# 1. Read the report
$reportData = Get-Content $reportFile -Raw

# 2. Prepare the prompt (English for the AI, results will be shown in both)
$prompt = @"
Analyzer Role: Trading Expert.
Data: Optimizer Report.
Constraint: Provide TEXT ONLY analysis. Do not call any tools or sub-agents.

Analyze this Trading Optimizer Report:
$reportData

Questions:
1. Which pair is most profitable?
2. Which pair is worst?
3. Suggest RSI Oversold, RSI Overbought, and EMA values for EURUSD to maximize Net Profit.

Format the output as a concise summary for a dashboard. Mention 'Gemini CLI Tool' at the start.
"@

Write-Host "Consulting Gemini CLI..." -ForegroundColor Cyan

# 3. Call Gemini and capture output
# We use -InputObject to avoid pipe encoding issues with strings
$geminiOutput = $prompt | gemini

if ($null -eq $geminiOutput -or $geminiOutput.Trim() -eq "") {
    Write-Host "Error: Gemini returned no output." -ForegroundColor Red
    exit
}

Write-Host "Analysis Received: $geminiOutput" -ForegroundColor Green

# 4. Prepare JSON object for the dashboard
$timestamp = Get-Date -Format "HH:mm"
$newInsight = @{
    time = $timestamp
    reason = "Gemini CLI: $geminiOutput"
}

# 5. Load existing memory or create new
if (Test-Path $aiMemoryFile) {
    $currentMemory = Get-Content $aiMemoryFile | ConvertFrom-Json
    if ($currentMemory -isnot [system.array]) { $currentMemory = @($currentMemory) }
} else {
    $currentMemory = @()
}

# 6. Append new insight and keep only last 20
$updatedMemory = @($newInsight) + $currentMemory
$updatedMemory = $updatedMemory | Select-Object -First 20

# 7. Save back to file
$updatedMemory | ConvertTo-Json -Depth 5 | Out-File -FilePath $aiMemoryFile -Encoding utf8
Write-Host "Insight saved to $aiMemoryFile for Dashboard integration." -ForegroundColor Yellow
