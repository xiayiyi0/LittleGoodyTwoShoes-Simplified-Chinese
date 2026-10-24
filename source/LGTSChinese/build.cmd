@echo off
REM Build LGTS Chinese plugin (no .NET SDK needed; uses in-box Framework csc, C# 5)
REM
REM Usage:  build.cmd [game-dir]
REM   game-dir  comes from argv[1], else env LGTS_GAME, else DEFAULT_GAME below.
REM     build.cmd "E:\Games\Little Goody Two Shoes"
REM     set LGTS_GAME=E:\Games\Little Goody Two Shoes
REM
REM Output: build\LGTSChinese.dll  (assembly + file version taken from Plugin.VER)
setlocal
cd /d "%~dp0"

set "GAME="
if not "%~1"=="" set "GAME=%~1"
if not defined GAME if defined LGTS_GAME set "GAME=%LGTS_GAME%"
if not defined GAME set "GAME=D:\steam\steamapps\common\Little Goody Two Shoes"

set "CSC=C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
set "FW=C:\Windows\Microsoft.NET\Framework64\v4.0.30319"
set "MAN=%GAME%\LGTS_Data\Managed"
set "CORE=%GAME%\BepInEx\core"

if not exist "%CSC%" (
    echo [ERROR] in-box C# compiler not found: %CSC%
    goto :fail
)
if not exist "%GAME%\LGTS.exe" (
    echo [ERROR] no LGTS.exe under: %GAME%
    echo         Pass the game folder as argument 1, or set LGTS_GAME.
    goto :fail
)
if not exist "%MAN%\UnityEngine.dll" (
    echo [ERROR] not found: %MAN%\UnityEngine.dll
    echo         Expected a LGTS_Data\Managed\ subfolder in the game folder.
    goto :fail
)
if not exist "%CORE%\BepInEx.dll" (
    echo [ERROR] not found: %CORE%\BepInEx.dll
    echo         Install BepInEx 5 into the game folder first.
    goto :fail
)

echo GAME=%GAME%
if not exist build mkdir build
"%CSC%" /nologo /target:library /langversion:5 /optimize+ /out:build\LGTSChinese.dll ^
 /reference:"%CORE%\BepInEx.dll" ^
 /reference:"%CORE%\0Harmony.dll" ^
 /reference:"%MAN%\UnityEngine.dll" ^
 /reference:"%MAN%\UnityEngine.CoreModule.dll" ^
 /reference:"%MAN%\UnityEngine.AssetBundleModule.dll" ^
 /reference:"%MAN%\UnityEngine.TextRenderingModule.dll" ^
 /reference:"%MAN%\UnityEngine.UI.dll" ^
 /reference:"%MAN%\Unity.TextMeshPro.dll" ^
 /reference:"%FW%\System.dll" ^
 /reference:"%FW%\System.Core.dll" ^
 Plugin.cs
echo BUILD_EXIT=%ERRORLEVEL%
endlocal
exit /b 0

:fail
endlocal
exit /b 1
