#!/bin/bash

#
# Simple bash script for Docker install on Ubuntu / Debian 
# Run it with sudo
#

# Check for root user
[[ $(id -u) -ne 0 ]] && echo "[Error] Run script as root!" && exit 1

## Clean-up any old installation
apt-get -qq remove docker docker-engine docker.io containerd runc

## Update the apt package index and install packages to allow apt to use a repository over HTTPS:
apt-get -qq update
apt-get -qq install -y ca-certificates curl gnupg lsb-release

## Add Docker’s official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

## Set up repository
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

## Install docker-engine, containerd and docker-compose
apt-get -qq update
apt-get -qq install -y docker-ce docker-ce-cli containerd.io docker-compose

## Set default docker container log max size and count 
tee -a /etc/docker/daemon.json > /dev/null <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  }
}
EOF

## Restart to get daemon.json configs
systemctl restart docker

## Add user to docker group
usermod -a -G docker ${SUDO_USER:-$(whoami)}
