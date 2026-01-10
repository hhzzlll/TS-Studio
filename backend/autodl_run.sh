#!/bin/bash
# AutoDL 启动脚本
# 使用方法: bash autodl_run.sh

# 1. 进入脚本所在目录 (backend/)
cd "$(dirname "$0")"

echo "=== 正在检查并安装依赖 ==="
# 注意: AutoDL 镜像通常已包含 torch, pandas, numpy 等
# 我们只需要安装 Django 相关依赖
pip install -r requirements.txt

echo "=== 执行数据库迁移 ==="
python manage.py makemigrations
python manage.py migrate

echo "=== 启动 Django 服务 (端口 8000) ==="
# 允许外部访问
python manage.py runserver 0.0.0.0:8000
