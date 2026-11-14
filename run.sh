#!/bin/bash
# ikuuu 签到运行脚本（供 systemd timer 调用）
cd "$(dirname "$0")"
exec .venv/bin/python checkin.py
