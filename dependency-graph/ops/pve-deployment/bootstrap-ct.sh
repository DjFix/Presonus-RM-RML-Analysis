#!/bin/bash
# Execute inside CT125, never on PVE host. Public maintenance key argument required.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl gnupg sudo openssh-server nftables jq
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
printf '%s\n' 'deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable' > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y \
  docker-ce=5:29.9.2-1~debian.12~bookworm \
  docker-ce-cli=5:29.9.2-1~debian.12~bookworm \
  containerd.io=2.4.2-3~debian.12~bookworm \
  docker-buildx-plugin=0.38.1-1~debian.12~bookworm \
  docker-compose-plugin=5.6.1-1~debian.12~bookworm
id rs >/dev/null 2>&1 || useradd --create-home --shell /bin/bash rs
install -d -m 0700 -o rs -g rs /home/rs/.ssh
sed 's/^/from="192.168.50.238",no-agent-forwarding,no-X11-forwarding,no-port-forwarding /' /root/vm101-memgraph-pve.pub > /home/rs/.ssh/authorized_keys
chown rs:rs /home/rs/.ssh/authorized_keys
chmod 0600 /home/rs/.ssh/authorized_keys
install -m 0755 -o root -g root /root/memgraphctl /usr/local/sbin/memgraphctl
printf '%s\n' 'rs ALL=(root) NOPASSWD: /usr/local/sbin/memgraphctl' > /etc/sudoers.d/rs-memgraph
chmod 0440 /etc/sudoers.d/rs-memgraph
visudo -cf /etc/sudoers.d/rs-memgraph
mkdir -p /etc/ssh/sshd_config.d
printf '%s\n' 'PasswordAuthentication no' 'KbdInteractiveAuthentication no' 'PermitRootLogin no' 'PubkeyAuthentication yes' > /etc/ssh/sshd_config.d/10-memgraph.conf
sshd -t
systemctl enable --now ssh docker nftables
systemctl restart ssh
mkdir -p /opt/memgraph /srv/memgraph/{data,log,lab,backups}
cat > /etc/nftables.conf <<'NFT'
#!/usr/sbin/nft -f
add table inet uc_lan
flush table inet uc_lan
table inet uc_lan {
 chain ingress_guard {
  type filter hook prerouting priority -150; policy accept;
  iifname "eth0" ct state established,related accept
  iifname "eth0" udp sport 67 udp dport 68 accept
  iifname "eth0" ip saddr 192.168.50.0/24 accept
  iifname "eth0" drop
 }
 chain input {
  type filter hook input priority -5; policy drop;
  iifname "lo" accept
  ct state established,related accept
  udp sport 67 udp dport 68 accept
  ip saddr 192.168.50.0/24 ip protocol icmp accept
  ip saddr 192.168.50.0/24 tcp dport { 22, 3000, 7687, 7444 } accept
  iifname "docker0" accept
  iifname "br-*" accept
 }
}
NFT
mkdir -p /etc/systemd/system/nftables.service.d
cat > /etc/systemd/system/nftables.service.d/uc-owned-table.conf <<'SYSTEMD'
[Service]
ExecStop=
ExecStop=/usr/sbin/nft delete table inet uc_lan
SYSTEMD
systemctl daemon-reload
# Preserve Docker-owned rules when restarting the guest firewall.
systemctl restart nftables
systemctl restart docker
docker version
docker compose version
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
ip -j addr show eth0
cat /run/systemd/netif/leases/* 2>/dev/null || true
