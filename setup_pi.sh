#!/usr/bin/env bash

echo Downloading pyBMC...
tmpdir=`mktemp -d`
cd $tmpdir
curl -sL -o pybmc.zip https://github.com/brunokc/pyBMC/archive/main.zip
unzip -q pybmc.zip
mv pyBMC-main pyBMC
cd pyBMC

echo Installing Python dependencies...
sudo apt-get -y install python3-venv

echo Creating Python virtual environment and activating it...
python -m venv venv
source venv/bin/activate

echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

rm -r $tmpdir
