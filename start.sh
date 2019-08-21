#!/bin/bash
docker-compose pull
docker-compose build
docker-compose push
docker-compose up -d

screen -dmS aperisolve docker-compose logs -f

