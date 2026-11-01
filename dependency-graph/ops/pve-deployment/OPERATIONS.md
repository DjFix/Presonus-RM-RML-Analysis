# Memgraph CT125

PVE: `pve-rs`, `192.168.50.2`, Proxmox 9.2.21. New unprivileged CT125,
Debian12, hostname `memgraph-uc`, MAC `BC:24:11:05:8C:06`, bridge `vmbr0`.
Current DHCP address `192.168.50.190/24`, router/DNS `.1`, lease86400seconds.
This is not yet an authoritative static reservation. Reserve that MAC/address
on the router before relying on a permanent endpoint. Do not guess router credentials.

Lab: http://192.168.50.190:3000/ ; Bolt: bolt://192.168.50.190:7687 .
LAN `192.168.50.0/24` may reach22/3000/7687/7444; other inbound traffic is
blocked by CT-owned nftables table `inet uc_lan` before Docker DNAT. No PVE
host/global firewall changes or WAN forwarding. Docker and dependencies exist
only inside CT125. No database password, matching current trusted-LAN clients.

```sh
ssh -i /home/rs/.ssh/id_ed25519_memgraph_pve -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes rs@192.168.50.190 'sudo -n /usr/local/sbin/memgraphctl status'
```

CT Ed25519 host fingerprint:
`SHA256:miLe0+dK45DWl0wKaGtgI+hueIStTtA2b+++RBaFR0c`.
Its public key was retrieved via trusted PVE `pct exec` before known_hosts addition.
Maintenance key stays VM101; rs key source is restricted to192.168.50.238.
Password/root SSH disabled. rs has no Docker group or unrestricted sudo.
Only root-owned `memgraphctl` accepts fixed single actions:
`status`, `logs`, `start`, `stop`, `restart`, `health`, `snapshot`.
Arbitrary root commands and extra wrapper arguments are denied.

Compose: `/opt/memgraph/compose.yaml`, root-owned, pinned MAGE3.13.0 and Lab3.13.2
by registry digest. Reproducible local copies/scripts are in this directory.
Systemd `memgraph-compose` enables boot startup; Docker restart policy is
unless-stopped. Docker29.9.2, Compose5.6.1; exact image metadata is in evidence.
Lab QuickConnect uses the internal Docker name `memgraph`, not a VM101 hostname.

LXC20GiB RAM,4CPUs,swap ceiling2GiB. PVE currently has no swap backing; this
ceiling does not create physical swap. Docker Memgraph18GiB; effective Memgraph
16GiB and unlimited license memory verified by SHOW STORAGE INFO; Lab1GiB.
Transactional storage retained. Root32GiB/data64GiB on local-zfs, data at
`/srv/memgraph/data` (UID101:GID103), logs `/srv/memgraph/log` (same owner).
Docker logs rotate3x20MiB per service. Persistent Memgraph logs reside on64GiB
mount; retain snapshot/WAL and review future log retention without deleting evidence.

Debian nftables service normally flushes all rules on stop. The installed
systemd drop-in limits this to the owned uc_lan table, preserving Docker chains.
The maintained bootstrap includes this correction; the exact earlier executed
bootstrap and runtime fixes are archived separately in evidence.

Initial consistency snapshot/config backup, outside CT data volume:
`temp/recovery-work/pve-memgraph-01/initial-empty-backup.tar.gz` on VM101.
SHA is in evidence `initial-backup.sha256`. It captures empty initial data,
not the source graph. Data migration must follow MIGRATION.md and Root's
archive hash/path instructions. Old VM101 containers/volumes are retained.
Root owns project endpoint switching and replay of the existing sealed delta.

Restored cold archive SHA256:
`1aff112c942ac3052fe1c9c0799f309a7c778b166a44efdaab95aaef9dd6b934`
(782550611bytes), staged under `/home/rs/memgraph-migration/`.
Original empty data preserved as `/srv/memgraph/data-empty-before-migration-20261031T164528Z`.
Verified after full-data reboot:551198Artifact,204204NativeArtifact, all41edge
type counts unchanged; ContextGeneration remains refreshing, NativeGeneration
ready. Artifact(id)/NativeArtifact(id) indexes observed; original index capture
was unavailable, so independent index comparison is not claimed.

Chromium validation executed RETURN1 and displayed the actual restored
Book::isValidPos native graph. Connection title `UC dependency graph` is saved
in the validation browser's local storage. Lab Quick Connect works for a fresh
LAN browser; users can save the same name with New connection > Memgraph
instance > Save connection. Lab connection storage is browser-local.
No demo data was imported. Enterprise-only query sharing is unavailable;
ordinary query execution and graph rendering work without a license.

All restored counts/markers above are the baseline after reboot and BEFORE
Root resumes publication only after the identity migration has been reviewed.
The previous client-side 7200-second timeout request did not override the
server's 600-second limit; both attempts rolled back. Raising that limit is not
an accepted publication strategy. Resumable bounded commits are a separate next
step. Retained progress logs describe attempted, uncommitted operations.
Do not resume the legacy sealed delta using v2 identity producers. Preserve it
and its exact hashes for the explicit migration/supersession journal.
Later apply may legitimately change them. Final
publication proof belongs to Root and is separate from infrastructure acceptance.
Router DNS currently resolves `memgraph-uc` to192.168.50.190 (TTL0);
`memgraph-uc.local` is refused by the router. Use the explicit LAN endpoint.
