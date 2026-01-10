# 利用 AutoDL 加速预测计算指南

由于您本机没有 CUDA，预测速度较慢，利用 AutoDL 的 GPU 服务器运行后端预测服务是一个很好的解决方案。

本方案采用 **本地前端 + 远程后端** 的模式，并通过 **SSH 隧道** 连接，这样您**不需要修改任何代码**，使用体验和本地开发完全一致。

## 第一步：准备 AutoDL 实例

1. 租用一个 AutoDL 实例（推荐 PyTorch 镜像，例如 Miniforge3-PyTorch2.x）。
2. 开机后，在控制台找到 **登录指令** 和 **密码**。
   * 登录指令格式如：`ssh -p 12345 root@region-1.autodl.com`

## 第二步：配置 VS Code 远程连接 (推荐)

如果您还没有配置 VS Code 连接 AutoDL，请按以下步骤操作（如果已配置可跳过）：

1. 安装 VS Code 插件：**Remote - SSH**。
2. 点击左下角绿色图标 -> "Connect to Host..." -> "Configure SSH Hosts..."。
3. 输入 AutoDL 的 Host 信息：
   ```config
   Host autodl
       HostName region-1.autodl.com  <-- 替换为您的 HostName
       User root
       Port 12345                    <-- 替换为您的端口
   ```
4. 连接到该 Host，输入密码。

> **提示**：如果不想配置 SSH config，也可以直接打开终端使用 scp 命令传输文件，但 VS Code 拖拽上传更方便。

## 第三步：上传后端代码

1. 在连接上 AutoDL 的 VS Code 窗口中，打开 `/root/` 目录。
2. 建议创建一个文件夹，例如 `/root/project/`。
3. 将您本地的 `backend` 文件夹**完整地**拖入 AutoDL 的 `/root/project/` 中。
   * 注意：确保 `algorithm` 文件夹也在里面，模型权重文件如果很大，也需要上传。

## 第四步：在 AutoDL 上启动后端

1. 在 AutoDL 的 VS Code 终端中（或 SSH 终端中），进入 backend 目录：
   ```bash
   cd /root/project/backend
   ```
2. 我为您准备了一个启动脚本，直接运行即可自动安装依赖并启动：
   ```bash
   bash autodl_run.sh
   ```
   * 脚本会自动安装 `django` 等依赖，并启动服务监听 8000 端口。
   * 看到 `Starting development server at http://0.0.0.0:8000/` 即表示成功。

## 第五步：建立端口映射 (关键)

为了让您本地的前端（在 localhost）能访问到 AutoDL 上的后端，我们需要把服务器的 8000 端口“拉”到本地。

### 方法 A：使用 VS Code (最简单)
在连接到 AutoDL 的 VS Code 窗口中：
1. 打开底部的 **PORTS (端口)** 面板（如果没有，点击菜单 View -> Open View -> Ports）。
2. 点击 **Add Port**。
3. 输入 `8000` 并回车。
4. 此时，VS Code 会自动将远程的 8000 端口转发到您本地的 `localhost:8000`。

### 方法 B：使用 SSH 命令行
在您**本地电脑**的终端运行：
```bash
# 格式: ssh -L 本地端口:localhost:远程端口 root@IP -p ssh端口
ssh -CNg -L 8000:localhost:8000 root@region-1.autodl.com -p 12345
```
输入密码后，终端会挂起（没有输出是正常的），请保持窗口不要关闭。

## 第六步：运行本地前端

1. 回到您**本地**的 VS Code 窗口。
2. 像往常一样启动前端：
   ```bash
   cd frontend
   npm run dev
   ```
3. 打开浏览器访问前端页面。点击预测时，请求会发往 `localhost:8000`，然后通过 SSH 隧道自动转发到 AutoDL 服务器处理，利用 GPU 进行加速，结果再传回本地。

## 总结
- **后端**：在 AutoDL 上运行。
- **前端**：在本地运行。
- **连接**：通过 SSH 隧道 (Port Forwarding) 桥接。
