#!/usr/bin/env bash

set -x

branch=${1:-main}

echo Downloading pyBMC...
tmpdir=`mktemp -d`
curdir=$PWD
cd $tmpdir
curl -sL -o pybmc.zip https://github.com/brunokc/pyBMC/archive/${branch}.zip
unzip -q pybmc.zip
mv pyBMC-main ${curdir}/pyBMC
cd ${curdir}/pyBMC
rm -r $tmpdir

echo Installing Python dependencies...
sudo apt-get -y install python3-venv

echo Creating Python virtual environment and activating it...
python -m venv venv
source venv/bin/activate

echo Installing pyBMC dependencies...
pip install --upgrade pip
pip install -r requirements.txt
