param(
  [string]$ProjectRef = "pksjwrajpyobkzxlqmrz",
  [string]$AppUrl = "https://project-flow-delta.vercel.app/",
  [string]$CliPath = "$env:USERPROFILE\.local\supabase-cli\v2.108.0\supabase.exe",
  [switch]$SkipSecrets
)

$ErrorActionPreference = "Stop"

function Read-SecretPlain {
  param(
    [Parameter(Mandatory = $true)][string]$Prompt,
    [switch]$AllowEmpty
  )

  while ($true) {
    $secure = Read-Host $Prompt -AsSecureString
    if ($secure.Length -eq 0 -and $AllowEmpty) {
      return ""
    }

    if ($secure.Length -gt 0) {
      $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
      try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
      }
      finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
      }
    }

    Write-Host "Value is required." -ForegroundColor Yellow
  }
}

function Invoke-Supabase {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
  & $script:Supabase @Args
  if ($LASTEXITCODE -ne 0) {
    throw "Supabase command failed: supabase $($Args -join ' ')"
  }
}

if (-not (Test-Path -LiteralPath $CliPath)) {
  $pathCommand = Get-Command supabase -ErrorAction SilentlyContinue
  if (-not $pathCommand) {
    throw "Supabase CLI was not found. Expected $CliPath or a supabase command on PATH."
  }

  $CliPath = $pathCommand.Source
}

$script:Supabase = $CliPath
$SupabaseUrl = "https://$ProjectRef.supabase.co"

Write-Host "Using Supabase CLI: $CliPath"
Write-Host "Project ref: $ProjectRef"

if (-not $env:SUPABASE_ACCESS_TOKEN) {
  Write-Host ""
  Write-Host "Create a Supabase access token at:" -ForegroundColor Cyan
  Write-Host "https://supabase.com/dashboard/account/tokens"
  $env:SUPABASE_ACCESS_TOKEN = Read-SecretPlain "Paste Supabase access token"
}

Write-Host ""
Write-Host "Linking project..."
$dbPassword = Read-SecretPlain "Project database password"
Invoke-Supabase link --project-ref $ProjectRef --password $dbPassword

Write-Host ""
Write-Host "Pushing database migrations..."
Invoke-Supabase db push --linked --password $dbPassword

Write-Host ""
Write-Host "Deploying Edge Functions..."
$functions = @("me", "workspace", "creem-checkout", "creem-license", "creem-webhook")
foreach ($functionName in $functions) {
  if ($functionName -eq "creem-webhook") {
    Invoke-Supabase functions deploy $functionName --project-ref $ProjectRef --no-verify-jwt
  }
  else {
    Invoke-Supabase functions deploy $functionName --project-ref $ProjectRef
  }
}

if (-not $SkipSecrets) {
  Write-Host ""
  Write-Host "Setting Edge Function secrets..."
  $serviceRoleKey = Read-SecretPlain "Supabase service role key"
  $creemApiKey = Read-SecretPlain "Creem API key"
  $creemWebhookSecret = Read-SecretPlain "Creem webhook secret"
  $creemProductId = Read-SecretPlain "Creem lifetime product id"
  $creemEnvironment = Read-Host "Creem environment? live/test"
  if ($creemEnvironment -notin @("live", "test")) {
    throw "Creem environment must be live or test."
  }
  $creemTestMode = if ($creemEnvironment -eq "test") { "true" } else { "false" }

  $secretFile = Join-Path $env:TEMP ("project-flow-supabase-secrets-" + [guid]::NewGuid().ToString("N") + ".env")
  try {
    @(
      "SUPABASE_URL=$SupabaseUrl",
      "SUPABASE_SERVICE_ROLE_KEY=$serviceRoleKey",
      "APP_URL=$AppUrl",
      "CREEM_API_KEY=$creemApiKey",
      "CREEM_WEBHOOK_SECRET=$creemWebhookSecret",
      "CREEM_LIFETIME_PRODUCT_ID=$creemProductId",
      "CREEM_TEST_MODE=$creemTestMode"
    ) | Set-Content -LiteralPath $secretFile -Encoding UTF8

    Invoke-Supabase secrets set --project-ref $ProjectRef --env-file $secretFile
  }
  finally {
    if (Test-Path -LiteralPath $secretFile) {
      Remove-Item -LiteralPath $secretFile -Force
    }
  }
}

Write-Host ""
Write-Host "Done. Webhook URL:" -ForegroundColor Green
Write-Host "$SupabaseUrl/functions/v1/creem-webhook"
