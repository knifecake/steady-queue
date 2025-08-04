#!/bin/sh

set -e

docker rm -f robust-postgres || true
docker run -d --name robust-postgres -e POSTGRES_PASSWORD=postgres postgres:17.4-alpine