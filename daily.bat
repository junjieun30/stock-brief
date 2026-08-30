@echo off
REM 매일 자동 실행용 배치. Windows 작업 스케줄러가 이 파일을 호출한다.
REM 파이썬 경로가 다르면 아래 PY 값을 바꾸세요.

set PY=C:\Users\junji\anaconda3\python.exe
set HERE=%~dp0

cd /d "%HERE%"
"%PY%" run.py >> "%HERE%report\run.log" 2>&1
exit /b %ERRORLEVEL%
