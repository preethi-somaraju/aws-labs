@echo off
REM Opens the Chrome that lab screenshot automation attaches to.
REM
REM Separate profile and port from any other automation Chrome on this machine,
REM so this window is signed in as Preethi and nothing else is.
REM
REM Sign in to the AWS console here the first time only. Leave it open while
REM screenshots are taken.

set "CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"

if not exist "%CHROME%" (
  echo Could not find chrome.exe. Edit this file and set CHROME.
  pause
  exit /b 1
)

start "" "%CHROME%" ^
  --remote-debugging-port=9223 ^
  --user-data-dir="%USERPROFILE%\chrome-preethi-labs" ^
  "https://d-9a675ab5df.awsapps.com/start"

echo Capture Chrome starting on port 9223.
echo First run only: sign in to the AWS console in that window.
