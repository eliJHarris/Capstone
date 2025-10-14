#!/bin/bash
set -e

echo "=== Installing Docker and dependencies ==="
sudo zypper install -y docker docker-compose

echo "=== Enabling and starting Docker service ==="
sudo systemctl enable docker
sudo systemctl start docker

echo "=== Verifying installation ==="
docker --version

echo "=== Docker setup complete! ==="