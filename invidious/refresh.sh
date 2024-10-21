#!/usr/bin/env bash

output=$(docker run --rm quay.io/invidious/youtube-trusted-session-generator)

visitor_data=$(echo "$output" | awk -F': ' '/visitor_data/ {print $2}')
po_token=$(echo "$output" | awk -F': ' '/po_token/ {print $2}')

sed -i "s/VISITOR_DATA=.*/VISITOR_DATA=$visitor_data/" /home/iboaz/invidious/.env
sed -i "s/PO_TOKEN=.*/PO_TOKEN=$po_token/" /home/iboaz/invidious/.env

docker compose -f /home/iboaz/invidious/compose.yml up --force-recreate -d 
