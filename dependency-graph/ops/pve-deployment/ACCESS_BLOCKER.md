> Historical access failure: resolved after the owner added the existing VM101 public key. CT125 is now deployed and restored; see OPERATIONS.md and current evidence status.json.

# PVE deployment access gate — 2026-10-31

No CT was created. PVE inventory and resource checks could not run because SSH
root authentication failed. No CTID, storage, bridge or free LAN address has been
assumed. Existing services and project endpoint pointers remain unchanged.

Host: `192.168.50.2`, TCP SSH reachable, existing known_hosts matches.
Trusted Ed25519 host fingerprint:
`SHA256:Nmor7sE7HKhg/m86SlaQeT29+wnFdCAyAk2NsgCsUEU`.

VM101 existing RSA public-key fingerprint:
`SHA256:TKbVvAPkgy5j0TJkW5siZobc6S+uJDF4JY1ba7/llZ4`.
Public file: `/home/rs/.ssh/id_rsa.pub`.
Both explicit `IdentitiesOnly=yes` and default BatchMode were rejected with
`Permission denied (publickey,password)`. There is no SSH agent or SSH config.

An existing PVE administrator can authorize that public key for PVE root via the
PVE console or another established admin session. Keep the dedicated Memgraph
maintenance key restricted to the eventual CT; do not authorize it on PVE.
Never copy private keys. Once access exists, rerun the inventory below before
any mutation:

```sh
ssh -i /home/rs/.ssh/id_rsa -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes root@192.168.50.2 'pveversion; hostname; free -b; pvesh get /cluster/resources --output-format json; pvesm status; ip -j addr; cat /etc/network/interfaces; pvesh get /cluster/nextid; ls /var/lib/vz/template/cache'
```

`compose.yaml.in` is an unexecuted configuration template. Required digests and
Lab release must be verified, Lab's persistence path checked against that release,
then CT networking/firewall, image UID/GID, limits, SQL, browser and reboot checks
completed. It is not a deployment proof. Full requirements remain in
`dependency-graph/ops/PVE_MEMGRAPH_TASK.md`.

The additional explicitly authorized login `rs@192.168.50.2` with the same RSA
key, BatchMode and ConnectTimeout=5 was also rejected. `sudo -n pveversion`
could not execute. No further usernames or passwords were attempted.
