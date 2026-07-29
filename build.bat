@echo off
chcp 65001 >nul
REM ============================================
REM  Resin MeasureWare 快速构建脚本
REM  输出: dist\ResinMeasureWare.exe
REM ============================================

cd /d "%~dp0"

echo.
echo === 清理旧构建 ===
if exist "build\ResinMeasureWare" rmdir /s /q "build\ResinMeasureWare"
if exist "dist\ResinMeasureWare.exe" del /q "dist\ResinMeasureWare.exe"

echo === 构建 exe ===
.venv\Scripts\pyinstaller ResinMeasureWare.spec

if errorlevel 1 (
    echo.
    echo ❌ 构建失败！
    pause
    exit /b 1
)

echo.
echo ✅ 构建完成！
echo 输出文件: dist\ResinMeasureWare.exe
echo 文件大小:
dir dist\ResinMeasureWare.exe | find "ResinMeasureWare.exe"

echo.
echo === 构建 deploy 发布包 ===
set "DEPLOY_DIR=dist\ResinMeasureWare_Deploy"
if exist "%DEPLOY_DIR%" rmdir /s /q "%DEPLOY_DIR%"
mkdir "%DEPLOY_DIR%"
copy "dist\ResinMeasureWare.exe" "%DEPLOY_DIR%\" >nul
copy "DEPLOYMENT.md" "%DEPLOY_DIR%\" >nul

echo.
echo ✅ 发布包已准备: %DEPLOY_DIR%
echo    包含:
echo      - ResinMeasureWare.exe
echo      - DEPLOYMENT.md （部署说明）
echo.
echo 将整个 %DEPLOY_DIR% 文件夹复制到目标机器即可！
echo.
pause
