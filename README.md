# TS-Studio

## 1. 后端 (Backend)

确保已安装 Python 3.10+ 和必要的依赖。

```bash
cd backend

# 安装依赖
pip install -r requirements.txt
pip install einops tensorboardX wandb

# 启动服务
python manage.py runserver
```

服务默认运行在: `http://127.0.0.1:8000`

## 2. 前端 (Frontend)

确保已安装 Node.js.

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问地址通常为: `http://localhost:5173`
