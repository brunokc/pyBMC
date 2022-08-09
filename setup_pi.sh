#!/usr/bin/env bash
#

set -x

branch=${1:-main}

echo Downloading pyBMC...
tmpdir=`mktemp -d`
basedir=$PWD
cd $tmpdir
curl -sL -o pybmc.zip https://github.com/brunokc/pyBMC/archive/${branch}.zip
unzip -q pybmc.zip
mv pyBMC-${branch} ${basedir}/pyBMC
cd ${basedir}/pyBMC
rm -r $tmpdir

echo Installing pyBMC dependencies...
sudo apt-get -y install python3-venv pigpiod

echo Configuring pigpiod...
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

echo Creating Python virtual environment and activating it...
python -m venv venv
source venv/bin/activate

echo Installing pyBMC Python dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo Installing systemd files...
cp extra/pybmc.service /etc/systemd/system
cp extra/pybmc /etc/default
sudo systemctl daemon-reload
sudo systemctl enable pybmc

echo Starting pyBMC...
sudo systemctl start pybmc

source /etc/default/pybmc
echo Done.
echo App should be running on ${BIND_HOST}:${BIND_POST}
