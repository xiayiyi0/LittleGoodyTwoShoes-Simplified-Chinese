@echo off
REM Build LGTS Chinese plugin (no .NET SDK needed; uses in-box Framework csc, C# 5)
setlocal
cd /d "%~dp0"
set CSC=C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe
set GAME=D:\steam\steamapps\common\Little Goody Two Shoes
set MAN=%GAME%\LGTS_Data\Managed
set CORE=%GAME%\BepInEx\core
set FW=C:\Windows\Microsoft.NET\Framework64\v4.0.30319
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
