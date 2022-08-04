#!/usr/bin/env bash

echo Downloading pyBMC...
tmpdir=`mktemp -d`
cd $tmpdir
curl -sL -o pybmc.zip https://github.com/brunokc/pyBMC/archive/main.zip
unzip -q pybmc.zip
mv pyBMC-main pyBMC
cd pyBMC

echo Creating Python virtual environment...
sudo apt-get -y install python3-venv
python -m venv venv
source venv/bin/activate

echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

rm -r $tmpdir
