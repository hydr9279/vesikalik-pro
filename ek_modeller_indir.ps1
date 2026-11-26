# Ek model paketi (MIT lisanslı modeller): BiRefNet Matting / HR Matting / Genel ve BEN2 Base.
# Her dosya ayrı denenir; bulunamazsa uyarı verilir, işlem devam eder.
$ErrorActionPreference = "Continue"
$out = Join-Path $PSScriptRoot "ek_modeller"
New-Item -ItemType Directory -Force -Path $out | Out-Null
function Get-Model($name, $url) {
  $p = Join-Path $out $name
  Write-Host "Indiriliyor: $name <- $url"
  & curl.exe -L --fail --retry 3 -o "$p.part" $url
  if ($LASTEXITCODE -eq 0 -and (Get-Item "$p.part").Length -gt 50MB) { Move-Item -Force "$p.part" $p; Write-Host "Tamam: $name" }
  else { Write-Host "UYARI: indirilemedi $name"; Remove-Item -Force "$p.part" -ErrorAction SilentlyContinue }
}
# BiRefNet resmi GitHub surumu: dosya adlari surumden okunur
$rel = Invoke-RestMethod "https://api.github.com/repos/ZhengPeng7/BiRefNet/releases/tags/v1" -Headers @{ "User-Agent" = "hayal-medya" }
$rel.assets | ForEach-Object { Write-Host "  varlik: $($_.name) $([math]::Round($_.size/1MB)) MB" }
$onnx = $rel.assets | Where-Object { $_.name -like "*.onnx" }
$hr   = $onnx | Where-Object { $_.name -match "HR" -and $_.name -match "matting" } | Select-Object -First 1
$mat  = $onnx | Where-Object { $_.name -match "matting" -and $_.name -notmatch "HR" } | Select-Object -First 1
$gen  = $onnx | Where-Object { $_.name -eq "BiRefNet-general-epoch_244.onnx" } | Select-Object -First 1
if ($mat) { Get-Model "birefnet_matting.onnx" $mat.browser_download_url } else { Write-Host "UYARI: matting onnx surumde yok" }
if ($hr)  { Get-Model "birefnet_hr_matting.onnx" $hr.browser_download_url } else { Write-Host "UYARI: HR matting onnx surumde yok" }
if ($gen) { Get-Model "birefnet_general.onnx" $gen.browser_download_url }
Get-Model "ben2_base.onnx" "https://huggingface.co/PramaLLC/BEN2/resolve/main/BEN2_Base.onnx"
Get-ChildItem $out | ForEach-Object { Write-Host "$($_.Name) $([math]::Round($_.Length/1MB)) MB" }
