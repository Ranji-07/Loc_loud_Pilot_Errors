#!/bin/bash
# LocalPilot trial instance bootstrap (cloud-init user data). Ollama listens on 127.0.0.1 only;
# the laptop reaches it through an SSH tunnel. Placeholders are filled in by launch.ps1.
set -euxo pipefail
IDLE_MINUTES=__IDLE_MINUTES__
MODEL="__MODEL__"

mkdir -p /var/lib/localpilot /etc/localpilot
echo "$IDLE_MINUTES" > /etc/localpilot/idle-limit
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y curl jq

# Official installer; runs only on this disposable instance.
curl -fsSL https://ollama.com/install.sh | sh
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/override.conf <<'CONF'
[Service]
Environment="OLLAMA_HOST=127.0.0.1:11434"
Environment="OLLAMA_KEEP_ALIVE=10m"
CONF
systemctl daemon-reload
systemctl enable ollama
systemctl restart ollama

cat > /usr/local/bin/localpilot-idle-check <<'EOS'
#!/bin/bash
# Counts idle minutes (no SSH session, no loaded model) and powers off after the limit.
# Power-off maps to "stop" because launch.ps1 sets instance-initiated-shutdown-behavior=stop.
LIMIT=$(cat /etc/localpilot/idle-limit)
STATE=/var/lib/localpilot/idle-minutes
sessions=$(ss -Htn state established '( sport = :22 )' | wc -l)
loaded=$(curl -s --max-time 3 http://127.0.0.1:11434/api/ps | jq '.models | length' 2>/dev/null || echo 0)
if [ "$sessions" -gt 0 ] || [ "${loaded:-0}" -gt 0 ]; then echo 0 > "$STATE"; exit 0; fi
n=$(( $(cat "$STATE" 2>/dev/null || echo 0) + 5 ))
echo "$n" > "$STATE"
if [ "$n" -ge "$LIMIT" ]; then logger "localpilot: idle ${n}m >= ${LIMIT}m, powering off"; shutdown -h now; fi
EOS
chmod 755 /usr/local/bin/localpilot-idle-check
cat > /etc/systemd/system/localpilot-idle.service <<'UNIT'
[Unit]
Description=LocalPilot idle shutdown check
[Service]
Type=oneshot
ExecStart=/usr/local/bin/localpilot-idle-check
UNIT
cat > /etc/systemd/system/localpilot-idle.timer <<'UNIT'
[Unit]
Description=Run LocalPilot idle check every 5 minutes
[Timer]
OnBootSec=10min
OnUnitActiveSec=5min
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now localpilot-idle.timer

for i in $(seq 1 30); do curl -s http://127.0.0.1:11434/api/version && break; sleep 2; done
if [ -n "$MODEL" ]; then ollama pull "$MODEL" || echo "model pull failed; pull it later with remote.ps1 -Action pull-model"; fi
touch /var/lib/localpilot/ready
