#!/usr/bin/env bash
# CS528 HW5 - Compute Engine Debian startup script (runs as root).
set -Eeuo pipefail
exec > >(tee -a /var/log/hw5-startup.log) 2>&1

PROJECT_ID='enduring-trees-508117-p7'
REGION='us-east1'
INSTANCE='cs528-hw5-mysql'
REPO_URL='https://github.com/GeesalaPrashanthi/CS528--Cloud-Computing.git'
SECRET_NAME='hw5-db-password'
APP_DIR='/opt/hw5'
LOCK='/var/log/startup_already_done'

# The guest agent invokes startup scripts on every boot. Install only once.
if [[ -f "$LOCK" ]]; then
  echo 'HW5 startup previously configured; systemd will bring services back on boot.'
  exit 0
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y git curl ca-certificates python3 python3-venv python3-pip

mkdir -p "$APP_DIR"
# The HW5 directory MUST be committed and pushed before provisioning the VM.
git clone --depth 1 "$REPO_URL" /tmp/hw5-source
cp /tmp/hw5-source/hw5/server.py /tmp/hw5-source/hw5/reporter.py /tmp/hw5-source/hw5/requirements.txt "$APP_DIR/"
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --no-cache-dir -r "$APP_DIR/requirements.txt" google-cloud-secret-manager

# Google-published Cloud SQL Auth Proxy v2 for x86_64 Linux.
curl -fL --retry 3 -o /usr/local/bin/cloud-sql-proxy \
  'https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.26.3/cloud-sql-proxy.linux.amd64'
chmod 755 /usr/local/bin/cloud-sql-proxy

# Retrieve the DB password at service start, never store it in metadata or Git.
cat > "$APP_DIR/run-server.py" <<'PY'
import os
from google.cloud import secretmanager
secret = 'projects/enduring-trees-508117-p7/secrets/hw5-db-password/versions/latest'
client = secretmanager.SecretManagerServiceClient()
os.environ['DB_PASSWORD'] = client.access_secret_version(request={'name': secret}).payload.data.decode()
os.environ.update(GOOGLE_CLOUD_PROJECT='enduring-trees-508117-p7',
                  BUCKET='cs528-hw2-pgeesala', PORT='8080',
                  DB_HOST='127.0.0.1', DB_PORT='3307', DB_USER='root',
                  DB_NAME='cs528_hw5', REPORTER_URL='http://127.0.0.1:8081')
os.chdir('/opt/hw5')
os.execv('/opt/hw5/venv/bin/python', ['/opt/hw5/venv/bin/python', '-u', '/opt/hw5/server.py'])
PY
chmod 700 "$APP_DIR/run-server.py"

cat > /etc/systemd/system/hw5-sql-proxy.service <<EOF2
[Unit]
Description=HW5 Cloud SQL Auth Proxy
After=network-online.target
Wants=network-online.target
[Service]
ExecStart=/usr/local/bin/cloud-sql-proxy --address 127.0.0.1 --port 3307 ${PROJECT_ID}:${REGION}:${INSTANCE}
Restart=always
RestartSec=4
[Install]
WantedBy=multi-user.target
EOF2

cat > /etc/systemd/system/hw5-reporter.service <<'EOF2'
[Unit]
Description=HW5 reporter (unchanged HW4 app)
After=network-online.target
Wants=network-online.target
[Service]
WorkingDirectory=/opt/hw5
ExecStart=/opt/hw5/venv/bin/python -u /opt/hw5/reporter.py
Restart=always
RestartSec=4
[Install]
WantedBy=multi-user.target
EOF2

cat > /etc/systemd/system/hw5-server.service <<'EOF2'
[Unit]
Description=HW5 HTTP server
Requires=hw5-sql-proxy.service
After=network-online.target hw5-sql-proxy.service hw5-reporter.service
Wants=network-online.target hw5-reporter.service
[Service]
WorkingDirectory=/opt/hw5
ExecStart=/opt/hw5/venv/bin/python -u /opt/hw5/run-server.py
Restart=always
RestartSec=4
[Install]
WantedBy=multi-user.target
EOF2

systemctl daemon-reload
systemctl enable --now hw5-sql-proxy.service hw5-reporter.service hw5-server.service
# Lock only after installation and service configuration succeed.
touch "$LOCK"
echo 'HW5 installation finished; check systemctl status hw5-server for service health.'
