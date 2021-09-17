#!/bin/bash

supervisord >/var/log/supervisor/out.log 2>/var/log/supervisor/err.log &

exec python3 /opt/src/app/app.py
