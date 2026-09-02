@echo off
setlocal
cd /d "%~dp0"

echo =========================================================
echo    Launching Native NVIDIA Omniverse Kit Studio (RTX)
echo =========================================================

set KIT_EXE=%~dp0kit-app-template\_build\windows-x86_64\release\kit\kit.exe
set APP_KIT=%~dp0kit-app-template\source\apps\omni.improv.editor.kit
set EXTS_PATH=%~dp0exts

if not exist "%KIT_EXE%" (
    echo [!] Kit executable not found at: %KIT_EXE%
    echo [*] Bootstrapping NVIDIA Kit SDK via kit-app-template...
    if not exist "%~dp0kit-app-template" (
        git clone https://github.com/NVIDIA-Omniverse/kit-app-template.git "%~dp0kit-app-template"
    )
    if not exist "%~dp0kit-app-template\source\apps" (
        mkdir "%~dp0kit-app-template\source\apps"
    )
    copy /y "%~dp0apps\omni.improv.editor.kit" "%~dp0kit-app-template\source\apps\omni.improv.editor.kit"
    cd /d "%~dp0kit-app-template"
    call .\repo.bat build
    cd /d "%~dp0"
)

if not exist "%APP_KIT%" (
    if not exist "%~dp0kit-app-template\source\apps" (
        mkdir "%~dp0kit-app-template\source\apps"
    )
    copy /y "%~dp0apps\omni.improv.editor.kit" "%APP_KIT%"
)

echo [*] Starting Omniverse Kit with RTX viewport and omni.improv.starter extension...
"%KIT_EXE%" "%APP_KIT%" --ext-folder "%EXTS_PATH%" %*
