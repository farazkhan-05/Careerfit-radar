param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,

    [string]$Region = "us-central1",
    [string]$ArtifactRepository = "careerfit-radar",
    [string]$BackendService = "careerfit-backend",
    [string]$FrontendService = "careerfit-frontend",
    [string]$RuntimeServiceAccount = "careerfit-runtime",
    [string]$SchedulerJob = "careerfit-scheduled-web-search",
    [string]$SchedulerCron = "0 */6 * * *",
    [string]$SchedulerTimeZone = "Etc/UTC",
    [string]$SearchQuery = "software engineer",
    [string]$SearchLocation = "remote"
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

$imageTag = (Get-Date).ToUniversalTime().ToString("yyyyMMddHHmmss")
$backendImage = "$Region-docker.pkg.dev/$ProjectId/$ArtifactRepository/careerfit-backend:$imageTag"
$frontendImage = "$Region-docker.pkg.dev/$ProjectId/$ArtifactRepository/careerfit-frontend:$imageTag"

Invoke-Gcloud config set project $ProjectId
Invoke-Gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com cloudscheduler.googleapis.com logging.googleapis.com

$runtimeServiceAccountEmail = "$RuntimeServiceAccount@$ProjectId.iam.gserviceaccount.com"
if (-not (Test-Gcloud iam service-accounts describe $runtimeServiceAccountEmail --project $ProjectId)) {
    Invoke-Gcloud iam service-accounts create $RuntimeServiceAccount --display-name "CareerFit Radar runtime" --project $ProjectId
}

for ($attempt = 1; $attempt -le 12; $attempt++) {
    if (Test-Gcloud iam service-accounts describe $runtimeServiceAccountEmail --project $ProjectId) {
        break
    }
    Start-Sleep -Seconds 5
}

if (-not (Test-Gcloud iam service-accounts describe $runtimeServiceAccountEmail --project $ProjectId)) {
    throw "Runtime service account did not become available: $runtimeServiceAccountEmail"
}

Invoke-Gcloud projects add-iam-policy-binding $ProjectId `
    --member "serviceAccount:$runtimeServiceAccountEmail" `
    --role "roles/secretmanager.secretAccessor" `
    --quiet

Invoke-Gcloud projects add-iam-policy-binding $ProjectId `
    --member "serviceAccount:$runtimeServiceAccountEmail" `
    --role "roles/logging.logWriter" `
    --quiet

if (-not (Test-Gcloud artifacts repositories describe $ArtifactRepository --location $Region --project $ProjectId)) {
    Invoke-Gcloud artifacts repositories create $ArtifactRepository --repository-format docker --location $Region --description "CareerFit Radar containers" --project $ProjectId
}

Invoke-Gcloud builds submit . --config deploy/gcp/cloudbuild.yaml --substitutions "_REGION=$Region,_AR_REPOSITORY=$ArtifactRepository,_IMAGE_TAG=$imageTag" --project $ProjectId

$secretEnv = "DATABASE_URL=DATABASE_URL:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest,API_AUTH_TOKEN=API_AUTH_TOKEN:latest,TAVILY_API_KEY=TAVILY_API_KEY:latest"
$commonBackendEnv = "APP_ENV=production,LOG_LEVEL=INFO,GOOGLE_CLOUD_PROJECT=$ProjectId"

Invoke-Gcloud run deploy $BackendService `
    --image $backendImage `
    --region $Region `
    --platform managed `
    --allow-unauthenticated `
    --port 8080 `
    --service-account $runtimeServiceAccountEmail `
    --set-env-vars $commonBackendEnv `
    --set-secrets $secretEnv `
    --project $ProjectId

$backendUrl = (& gcloud.cmd run services describe $BackendService --region $Region --project $ProjectId --format "value(status.url)")
if (-not $backendUrl) {
    throw "Could not resolve backend Cloud Run URL."
}

Invoke-Gcloud run deploy $FrontendService `
    --image $frontendImage `
    --region $Region `
    --platform managed `
    --allow-unauthenticated `
    --port 8080 `
    --service-account $runtimeServiceAccountEmail `
    --set-env-vars "BACKEND_URL=$backendUrl" `
    --set-secrets "API_AUTH_TOKEN=API_AUTH_TOKEN:latest" `
    --project $ProjectId

$frontendUrl = (& gcloud.cmd run services describe $FrontendService --region $Region --project $ProjectId --format "value(status.url)")
if (-not $frontendUrl) {
    throw "Could not resolve frontend Cloud Run URL."
}

Invoke-Gcloud run services update $BackendService `
    --region $Region `
    --update-env-vars "^|^CORS_ORIGINS=$frontendUrl,$backendUrl" `
    --project $ProjectId

$apiToken = ((& gcloud.cmd secrets versions access latest --secret API_AUTH_TOKEN --project $ProjectId) -join "").Trim()
if (-not $apiToken) {
    throw "Could not read API_AUTH_TOKEN from Secret Manager for Scheduler header setup."
}

$schedulerBody = @{
    query = $SearchQuery
    location = $SearchLocation
} | ConvertTo-Json -Compress
$schedulerPayloadPath = Join-Path "tmp" "scheduler-payload.json"
New-Item -ItemType Directory -Force (Split-Path $schedulerPayloadPath) | Out-Null
Set-Content -Path $schedulerPayloadPath -Value $schedulerBody -NoNewline

if (Test-Gcloud scheduler jobs describe $SchedulerJob --location $Region --project $ProjectId) {
    Invoke-Gcloud scheduler jobs update http $SchedulerJob `
        --location $Region `
        --schedule $SchedulerCron `
        --time-zone $SchedulerTimeZone `
        --uri "$backendUrl/sources/import/web-search" `
        --http-method POST `
        --headers "Content-Type=application/json,Authorization=Bearer $apiToken" `
        --message-body-from-file $schedulerPayloadPath `
        --format "value(name,state)" `
        --project $ProjectId
} else {
    Invoke-Gcloud scheduler jobs create http $SchedulerJob `
        --location $Region `
        --schedule $SchedulerCron `
        --time-zone $SchedulerTimeZone `
        --uri "$backendUrl/sources/import/web-search" `
        --http-method POST `
        --headers "Content-Type=application/json,Authorization=Bearer $apiToken" `
        --message-body-from-file $schedulerPayloadPath `
        --format "value(name,state)" `
        --project $ProjectId
}

Write-Host "Backend URL:  $backendUrl"
Write-Host "Frontend URL: $frontendUrl"
Write-Host "Images:"
Write-Host "  $backendImage"
Write-Host "  $frontendImage"
Write-Host "Run health check:"
Write-Host "  curl $backendUrl/health/ready"
