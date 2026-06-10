# 🧠 VocabMaster — 科学词汇记忆系统

基于 SM-2 间隔重复算法的高效词汇记忆应用，支持 Web / 移动端 / Android APK，内置多设备自动同步。

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 📝 闪卡复习 | SM-2 算法，5 级自适应评分，自动调度复习间隔 |
| 🎯 选择题 | 看单词选释义，4 选 1 自动评分 |
| ✍️ 拼写模式 | 看释义拼单词，主动回忆 |
| 🎧 听写模式 | 听发音默写，听觉+拼写双重记忆 |
| 🔊 单词发音 | Web Speech API，支持多语音/语速调节 |
| 📥 导入词库 | 支持 .xlsx / .csv 拖拽导入 |
| ☁️ 自动同步 | 登录后多设备自动同步学习进度 |
| 📱 PWA | 手机浏览器可安装到桌面 |
| 📦 Android APK | WebView 封装的原生应用 |

## 🚀 快速开始

### Docker 部署（推荐）

```bash
git clone https://github.com/Ask-Suzumi/VocabMaster.git
cd VocabMaster
docker-compose up -d
```

访问 `http://localhost:8000`

### 直接运行

```bash
pip install -r requirements.txt
python server.py
```

### 带 HTTPS 的一键部署

```bash
bash deploy.sh your-domain.com your@email.com
```

脚本会自动安装 Nginx、申请 Let's Encrypt 证书、配置反向代理。

## 🔑 登录

注册功能已禁用，单账号模式。

## 📁 项目结构

```
├── server.py              # FastAPI 后端
├── requirements.txt       # Python 依赖
├── Dockerfile             # Docker 镜像
├── docker-compose.yml     # 编排配置
├── deploy.sh              # 一键部署脚本
├── static/
│   ├── index.html         # 前端
│   ├── manifest.json      # PWA 清单
│   └── sw.js              # Service Worker
├── DEVELOPMENT.md         # 开发报告
└── app/                   # Android 项目
```

## 📡 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/login` | POST | 登录 |
| `/api/sync/download` | GET | 下载数据 |
| `/api/sync/upload` | POST | 上传数据 |
| `/api/health` | GET | 健康检查 |

## 🛠 技术栈

- **后端：** Python FastAPI + SQLite + JWT
- **前端：** 原生 HTML/CSS/JS（单文件）
- **算法：** SM-2 间隔重复
- **部署：** Docker + Nginx + Let's Encrypt
- **移动端：** PWA + Android WebView

## 📄 许可

MIT License
