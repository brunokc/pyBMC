#!/usr/bin/env bash

echo Downloading pyBMC...
curl -L -o pybmc.zip https://github.com/brunokc/pyBMC/archive/main.zip
mv pyBMC-main pyBMC
cd pyBMC

echo Creating Python virtual environment...
python -m venv venv
source venv/bin/activate

echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
