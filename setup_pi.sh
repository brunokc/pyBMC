#!/usr/bin/env bash
#

set -x

branch=${1:-main}
install_path=/var/www/pyBMC

echo Downloading latest pyBMC...
tmpdir=`mktemp -d`
basedir=$PWD
cd $tmpdir
curl -sL -o pybmc.zip https://github.com/brunokc/pyBMC/archive/${branch}.zip
unzip -q pybmc.zip
mkdir -p ${install_path}
mv pyBMC-${branch} ${install_path}
cd ${install_path}
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
sudo cp extra/pybmc.service /etc/systemd/system
sudo cp extra/pybmc /etc/default
sudo systemctl daemon-reload
sudo systemctl enable pybmc

echo Starting pyBMC...
sudo systemctl start pybmc

source /etc/default/pybmc
echo Done.
echo PyBMC running on ${BIND_HOST}:${BIND_PORT}
