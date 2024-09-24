#!/usr/bin/env bash
docker compose -f /home/iboaz/code-server/compose.yml build
docker compose -f /home/iboaz/code-server/compose.yml up -d
