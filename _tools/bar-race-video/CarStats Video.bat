@echo off
rem Opens the CarStats.ie video maker window
where pythonw >nul 2>nul && (start "" pythonw "%~dp0launcher.pyw" & exit /b)
start "" pyw "%~dp0launcher.pyw"
