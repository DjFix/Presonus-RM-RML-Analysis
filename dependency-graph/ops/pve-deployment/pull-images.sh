#!/bin/bash
# CT125 only; image digests captured from public Docker registry on 2026-10-31.
set -euo pipefail
MAGE=memgraph/memgraph-mage:3.13.0@sha256:cc33431b088c6b9580528d8d5aff92f3b958de1af5d40126f831ab8512eb855a
LAB=memgraph/lab:3.13.2@sha256:c6c205e240ac27b09d75877788650f5ff1d4c640b0a96af27dcc6e06ce25620c
docker pull "$MAGE"
docker pull "$LAB"
docker image inspect "$MAGE" "$LAB"
docker run --rm --entrypoint sh "$MAGE" -c 'id; id memgraph; command -v mgconsole; cat /etc/memgraph/memgraph.conf | head -20'
docker run --rm --entrypoint sh "$LAB" -c 'id; pwd; ls -la; find / -maxdepth 3 -iname "*lab*" 2>/dev/null | head -30'
