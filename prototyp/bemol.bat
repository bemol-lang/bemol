@echo off
rem ======================================================================
rem  BEMOL - kompilacja i uruchomienie programu (Windows)
rem
rem  Uzycie:
rem     bemol program.bmol               kompilacja testowa i uruchomienie
rem     bemol -finalbake program.bmol    finalbake i uruchomienie
rem     bemol --check program.bmol       tylko sprawdzenie kodu
rem
rem  Folder z tym plikiem mozna dodac do zmiennej PATH, wtedy polecenie
rem  "bemol" dziala w kazdym folderze.
rem ======================================================================
setlocal EnableDelayedExpansion
chcp 65001 >nul

set "BEMOLC=%~dp0bemolc.py"
set "SRC="
set "NORUN="
for %%A in (%*) do (
    if /i "%%~xA"==".bmol" set "SRC=%%~fA"
    if /i "%%~A"=="--check" set "NORUN=1"
    if /i "%%~A"=="--emit-c" set "NORUN=1"
)

if not defined SRC (
    echo Uzycie: bemol program.bmol   [-finalbake] [--check]
    exit /b 2
)

rem Python: najpierw launcher "py", potem "python"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo BML-E0995: nie znaleziono Pythona.
    echo Zainstaluj go poleceniem:  winget install Python.Python.3.12
    echo a potem zamknij i otworz terminal na nowo.
    exit /b 1
)

%PY% "%BEMOLC%" %*
if errorlevel 1 exit /b 1
if defined NORUN exit /b 0

set "EXE=%SRC:~0,-5%.exe"
echo.
"%EXE%"
exit /b %errorlevel%
