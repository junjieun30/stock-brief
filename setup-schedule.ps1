# 매일 아침 브리핑을 자동 생성하도록 Windows 작업 스케줄러에 등록한다.
#
#   PowerShell 에서:  .\setup-schedule.ps1
#   시간 바꾸기:      .\setup-schedule.ps1 -Time "06:40"
#   등록 해제:        .\setup-schedule.ps1 -Remove
#
# 미국 증시는 한국시간 새벽 5~6시에 마감하므로 기본값은 07:00 입니다.

param(
    [string]$Time = "07:00",
    [string]$TaskName = "StockDailyBrief",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$bat  = Join-Path $here "daily.bat"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "등록 해제 완료: $TaskName"
    return
}

if (-not (Test-Path $bat)) { throw "daily.bat 을 찾을 수 없습니다: $bat" }

$action  = New-ScheduledTaskAction -Execute $bat -WorkingDirectory $here
$trigger = New-ScheduledTaskTrigger -Daily -At $Time

# 노트북이 배터리로 돌아갈 때도 실행되게, 그리고 부팅이 늦어 놓친 실행은 따라잡게 한다
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "해외 주식 데일리 브리핑 자동 생성" -Force | Out-Null

Write-Host "등록 완료: 매일 $Time 에 브리핑을 생성합니다."
Write-Host "지금 한 번 테스트:  Start-ScheduledTask -TaskName $TaskName"
Write-Host "상태 확인:          Get-ScheduledTaskInfo -TaskName $TaskName"
Write-Host ""
Write-Host "리포트 위치: $(Join-Path $here 'report\latest.html')"
