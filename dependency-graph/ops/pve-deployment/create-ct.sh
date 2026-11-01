#!/bin/bash
# Run on the authorized PVE node after current inventory approval.
set -euo pipefail
CTID=125
TEMPLATE=debian-12-standard_12.12-1_amd64.tar.zst
if pct config "$CTID" >/dev/null 2>&1; then
  echo "CTID already exists: inspect rather than recreate" >&2; exit 1
fi
pveam download local "$TEMPLATE"
pct create "$CTID" "local:vztmpl/$TEMPLATE" \
  --hostname memgraph-uc --unprivileged 1 --cores 4 --memory 20480 --swap 2048 \
  --rootfs local-zfs:32 --mp0 local-zfs:64,mp=/srv/memgraph,backup=1 \
  --features nesting=1,keyctl=1 --onboot 1 --ostype debian \
  --net0 name=eth0,bridge=vmbr0,hwaddr=BC:24:11:05:8C:06,ip=dhcp,type=veth --nameserver 192.168.50.1 \
  --description 'UC derived graph; Memgraph16GiB Docker18GiB CT20GiB; DHCP installation staging pending authoritative static reservation'
pct start "$CTID"
pct config "$CTID"
