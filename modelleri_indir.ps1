# Yapay zeka modellerini models klasörüne indirir (yalnızca eksik olanları)
$ErrorActionPreference = "Stop"
$dir = Join-Path $PSScriptRoot "models"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$list = @(
 @("yunet.onnx","https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"),
 @("face_parsing_resnet34.onnx","https://github.com/yakhyo/face-parsing/releases/download/v0.0.1/resnet34.onnx"),
 @("lama.onnx","https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/inpainting_lama/inpainting_lama_2025jan.onnx"),
 @("efficientsam.onnx","https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/image_segmentation_efficientsam/image_segmentation_efficientsam_ti_2024may.onnx"),
 @("isnet-general-use.onnx","https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx"),
 @("u2net_human_seg.onnx","https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx"),
 @("birefnet_portrait.onnx","https://github.com/danielgatis/rembg/releases/download/v0.0.0/birefnet-portrait-epoch_150.onnx")
)
foreach ($m in $list) {
  $p = Join-Path $dir $m[0]
  if ((Test-Path $p) -and ((Get-Item $p).Length -gt 100000)) { Write-Host "Var: $($m[0])"; continue }
  Write-Host "Indiriliyor: $($m[0]) ..."
  & curl.exe -L --fail --retry 3 -o "$p.part" $m[1]
  if ($LASTEXITCODE -ne 0) { throw "Indirilemedi: $($m[0])" }
  Move-Item -Force "$p.part" $p
}
Write-Host "Modeller tamam."
