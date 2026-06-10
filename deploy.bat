@echo off
title VocabMaster Deploy

echo Uploading server.py ...
scp "C:\Users\Administrator\Desktop\vocabmaster\server.py" root@muvsera.cc.cd:/home/vocabmaster/

echo Uploading index.html ...
scp "C:\Users\Administrator\Desktop\vocabmaster\static\index.html" root@muvsera.cc.cd:/home/vocabmaster/static/

echo Rebuilding Docker ...
ssh root@muvsera.cc.cd "cd /home/vocabmaster && docker-compose down && docker-compose up -d --build"

echo.
echo Done. Visit https://muvsera.cc.cd
pause
