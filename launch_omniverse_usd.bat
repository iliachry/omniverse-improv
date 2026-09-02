@echo off
setlocal
cd /d "%~dp0"

set KIT_EXE=%~dp0kit-app-template\_build\windows-x86_64\release\kit\kit.exe
set APP_KIT=%~dp0kit-app-template\source\apps\omni.improv.editor.kit
set EXTS_PATH=%~dp0exts

set STAGE_FILE=%1
if "%STAGE_FILE%"=="" (
    set STAGE_FILE=usd_generators\output_physics_playground.usda
)

echo =========================================================
echo    Opening USD Stage in Native NVIDIA Omniverse Kit
echo    Target Stage: %STAGE_FILE%
echo =========================================================

"%KIT_EXE%" "%APP_KIT%" --ext-folder "%EXTS_PATH%" "%STAGE_FILE%"
