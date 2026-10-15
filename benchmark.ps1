$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force results | Out-Null
$rows = @()
foreach ($variant in @('naive', 'opt')) {
  $tag = "iris-serve:$variant"
  $dockerfile = "Dockerfile.serve.$variant"
  docker image rm $tag 2>$null | Out-Null
  # Sans cache de construction pour mesurer le build à froid.
  $cold = (Measure-Command { docker build --no-cache -f $dockerfile -t $tag .; if ($LASTEXITCODE -ne 0) { throw 'Build failed' } }).TotalSeconds
  $hot = (Measure-Command { docker build -f $dockerfile -t $tag .; if ($LASTEXITCODE -ne 0) { throw 'Build failed' } }).TotalSeconds
  $bytes = [long](docker image inspect $tag --format '{{.Size}}')
  $rows += [pscustomobject]@{Version=$variant; TailleMo=[math]::Round($bytes / 1MB,2); FroidSecondes=[math]::Round($cold,2); ChaudSecondes=[math]::Round($hot,2)}
}
$rows | Format-Table -AutoSize
$rows | Export-Csv -Path results/benchmark.csv -NoTypeInformation -Encoding utf8
