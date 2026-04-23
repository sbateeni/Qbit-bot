# Robust Code Debugging Script using Gemini
param (
    [Parameter(Mandatory=$true)]
    [string]$File
)

$aiMemoryFile = "logs/ai_memory.json"

if (!(Test-Path $File)) {
    Write-Host "Error: File '$File' not found." -ForegroundColor Red
    exit
}

# 1. Read the code
$codeData = Get-Content $File -Raw

# 2. Prepare the prompt
$prompt = @"
Analyzer Role: Senior Python Developer.
Constraint: Provide TEXT ONLY analysis. Do NOT attempt to run tools or use sub-agents. 

Review this code for logical errors, missing dependencies, or performance issues:
File: $File

Code Buffer:
$codeData

Identify any specific issues and provide a quick fix.
"@

Write-Host "Analyzing '$File' with Gemini CLI Analyst..." -ForegroundColor Cyan

# 3. Call Gemini
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
    reason = "Gemini CLI Debug ($File): $geminiOutput"
}

# 5. Load existing memory
if (Test-Path $aiMemoryFile) {
    $currentMemory = Get-Content $aiMemoryFile | ConvertFrom-Json
    if ($currentMemory -isnot [system.array]) { $currentMemory = @($currentMemory) }
} else {
    $currentMemory = @()
}

# 6. Append and save
$updatedMemory = @($newInsight) + $currentMemory
$updatedMemory = $updatedMemory | Select-Object -First 20
$updatedMemory | ConvertTo-Json -Depth 5 | Out-File -FilePath $aiMemoryFile -Encoding utf8

Write-Host "Debug insight saved to $aiMemoryFile." -ForegroundColor Yellow
