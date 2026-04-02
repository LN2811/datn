@echo off
pushd "%~dp0"
docker compose up db %*
popd
