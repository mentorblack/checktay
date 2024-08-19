#!/bin/bash

apt update
apt install -y nginx
apt install -y python3 python3-pip
pip3 install virtualenv

cat <<EOF >/etc/systemd/system/gunicorn.service
[Unit]
Description=Gunicorn
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/root
Environment="PATH=/root/env/bin"
ExecStart=/root/env/bin/gunicorn --workers 1 --bind 0.0.0.0:5000 server:app

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl start gunicorn
systemctl enable gunicorn
cat <<EOF >/etc/nginx/sites-available/default
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF
systemctl restart nginx
cd /root
virtualenv env
source env/bin/activate
pip install -r requirements.txt
