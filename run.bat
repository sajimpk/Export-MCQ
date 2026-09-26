@echo off
chcp 65001 > nul
title Asopori MCQ Question & Answer Extractor
echo ===================================================
echo   MCQ Question & Answer Extractor
echo ===================================================
echo.
python mcq_scraper.py %*
pause
