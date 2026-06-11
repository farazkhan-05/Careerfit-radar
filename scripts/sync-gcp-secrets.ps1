param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,

    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"

function Invoke-Gcloud {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    & gcloud.cmd @Args
    if ($LASTEXITCODE -ne 0) {
        throw "gcloud command failed: gcloud $($Args -join ' ')"
    }
}

function Test-Gcloud {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    $command = "gcloud.cmd $($Args -join ' ') >nul 2>nul"
    & cmd.exe /c $command
    return $LASTEXITCODE -eq 0
}

function Read-DotEnv {
    param([string]$Path)

    if (-not (Test-Path -Path $Path)) {
        throw "Environment file not found: $Path"
    }

    $values = @{}
    foreach ($line in Get-Content -Path $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }
        $parts = $line -split "=", 2
        if ($parts.Count -ne 2) {
            continue
        }
        $key = $parts[0].Trim()
        $value = $parts[1].Trim()
        if ($key) {
            $values[$key] = $value
        }
    }
    return $values
}

function Set-SecretVersion {
    param(
        [string]$Name,
        [string]$Value,
        [string]$ProjectId
    )

    if (-not $Value) {
        throw "Required secret value is missing: $Name"
    }

    $tempFile = New-TemporaryFile
    try {
        Set-Content -Path $tempFile -Value $Value -NoNewline
        if (-not (Test-Gcloud secrets describe $Name --project $ProjectId)) {
            Invoke-Gcloud secrets create $Name --replication-policy automatic --data-file $tempFile --project $ProjectId
        } else {
            Invoke-Gcloud secrets versions add $Name --data-file $tempFile --project $ProjectId
        }
    } finally {
        Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue
    }
}

$envValues = Read-DotEnv -Path $EnvFile
$requiredSecrets = @(
    "DATABASE_URL",
    "GEMINI_API_KEY",
    "API_AUTH_TOKEN",
    "TAVILY_API_KEY"
)

Invoke-Gcloud config set project $ProjectId
Invoke-Gcloud services enable secretmanager.googleapis.com --project $ProjectId

foreach ($secretName in $requiredSecrets) {
    Set-SecretVersion -Name $secretName -Value $envValues[$secretName] -ProjectId $ProjectId
}

Write-Host "Secret Manager is up to date for project $ProjectId."
