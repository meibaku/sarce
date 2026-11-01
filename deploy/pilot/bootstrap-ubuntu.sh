#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 || $# -ne 1 ]]; then
  echo "usage: sudo bootstrap-ubuntu.sh <operator-ip-or-cidr>" >&2
  exit 2
fi

operator_cidr=$1
if [[ ! $operator_cidr =~ ^[0-9a-fA-F:.]+(/[0-9]{1,3})?$ ]]; then
  echo "operator address must be an explicit IP or CIDR" >&2
  exit 2
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io docker-compose-v2 caddy ufw unattended-upgrades
systemctl enable --now docker caddy unattended-upgrades

install -d -m 0750 -o root -g docker /opt/sarce
install -d -m 0700 -o root -g root /etc/sarce
install -m 0600 -o root -g root /dev/null /etc/sarce/pilot.env
install -m 0600 -o root -g root /dev/null /etc/sarce/caddy.env

ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow from "$operator_cidr" to any port 22 proto tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "Host prepared. Populate /etc/sarce/*.env before copying configs or starting services."
