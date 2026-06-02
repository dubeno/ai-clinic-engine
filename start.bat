@echo off
chcp 65001 >nul
title AI诊所内容引擎

echo ================================================
echo   AI诊所内容引擎 - 一键启动
echo ================================================
echo.

:: 检查 Python
where py >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 安装依赖
echo [1/2] 检查依赖...
py -m pip install -e . --quiet 2>nul
if %errorlevel% neq 0 (
    py -m pip install anthropic openai pydantic fire python-dotenv loguru pdfplumber duckduckgo-search --quiet
)

echo [2/2] 启动服务...
echo.
echo   浏览器将自动打开: http://localhost:8080
echo   按 Ctrl+C 停止服务
echo.

:: 启动并打开浏览器
start http://localhost:8080
py web.py
pause
