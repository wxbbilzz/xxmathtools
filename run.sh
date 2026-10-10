#!/usr/bin/env bash
# 一键启动「小学数学工具」
# 自动使用项目内 venv 的 Python，无需手动激活
cd "$(dirname "$0")"
exec ./venv/bin/python xxmathrools/小学数学工具.py
