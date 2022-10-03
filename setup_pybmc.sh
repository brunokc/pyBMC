#!/usr/bin/env bash
#

if [ "$1" = "-x" ]; then
    set -x
fi

branch=${1:-main}
install_path=/var/www/pyBMC
user=pybmc

tmpdir=`mktemp -d`
trap "rm -r $tmpdir" EXIT

echo Downloading latest pyBMC...
cd $tmpdir
curl -sL -o pybmc.zip https://github.com/brunokc/pyBMC/archive/${branch}.zip
unzip -q pybmc.zip

echo Setting up pyBMC user...
# Need to add new user to the video group so that vcgencmd will work
sudo useradd -d ${install_path} -m -r -s /bin/false -c "pyBMC" -G video ${user} 2>/dev/null
sudo mkdir -p `dirname ${install_path}`

echo Installing pyBMC...
sudo mv pyBMC-${branch} ${install_path}
sudo chown -R ${user}.${user} ${install_path}
cd ${install_path}

echo Installing pyBMC dependencies...
sudo apt-get -y install python3-venv pigpiod

echo Configuring pigpiod...
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

sudo -u ${user} bash<<_
echo Creating Python virtual environment and activating it...
python -m venv venv
source venv/bin/activate

echo Installing pyBMC Python dependencies...
pip install --upgrade pip
pip install -r requirements.txt
_

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
