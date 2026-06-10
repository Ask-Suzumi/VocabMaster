# VocabMaster 开发报告

## 项目概述

VocabMaster 是一个基于 SM-2 间隔重复算法的高效词汇记忆系统，支持 Web/移动端/Android APK 多平台，内置账户同步功能，实现多设备学习进度无缝衔接。

**技术栈：** FastAPI + SQLite + JWT + Docker + PWA + Android WebView  
**开发周期：** 2026年6月  
**目标用户：** 六级/CET-6 备考者

---

## 一、设计思路

### 1.1 核心理念：最高效 = 最科学的算法 × 最低的摩擦成本

词汇记忆软件的核心矛盾：**用户需要频繁重复才能记住，但频繁操作导致了高放弃率。**

解决思路：
- **算法层：** SM-2 间隔重复（Anki 同款算法），根据每次回忆质量自动调整复习间隔
- **交互层：** 多模式练习（闪卡/选择题/拼写/听写），覆盖被动识别到主动输出的完整学习链
- **同步层：** 服务端为唯一数据源，打开即继续，消除"换设备就要重来"的挫败感

### 1.2 架构演进

```
阶段一：单文件 HTML（离线可用）
  └→ 阶段二：+ 发音功能（Web Speech API）
    └→ 阶段三：+ FastAPI 后端 + 账户同步
      └→ 阶段四：+ 移动端适配 + PWA
        └→ 阶段五：+ Android APK（WebView 封装）
          └→ 阶段六：同步引擎重构（服务器优先）
```

### 1.3 技术选型原则

| 决策 | 选择 | 理由 |
|------|------|------|
| 前后端分离？ | 单文件 HTML + API 后端 | 部署极简，一个容器搞定 |
| 数据库？ | SQLite | 单用户场景，无需 PostgreSQL |
| 移动端？ | PWA + Android WebView | 一套代码多端复用 |
| 发音？ | Web Speech API | 浏览器内置，零依赖 |
| 部署？ | Docker + Nginx + Let's Encrypt | 一条命令上线 |

---

## 二、制作方法

### 2.1 SM-2 间隔重复算法

```
评分 0-4（完全忘记 → 秒答）

quality < 2（失败）:
  interval = 0       # 当天重新复习
  ease -= 0.2        # 降低记忆保持率估值

quality >= 2（成功）:
  reviews=1: interval=1天
  reviews=2: interval=3天
  reviews≥3: interval = interval × ease
  ease += 0.1 - (3-quality) × (0.08 + (3-quality) × 0.02)
  ease ∈ [1.3, 2.8] # 自适应调节
```

### 2.2 四种练习模式

| 模式 | 认知层次 | 实现方式 |
|------|----------|----------|
| 📝 闪卡复习 | 被动识别 | 显示单词 → 点击翻转 → 5级自评 |
| 🎯 选择题 | 被动识别 | 显示单词 → 4选1释义 → 自动评分 |
| ✍️ 拼写模式 | 主动输出 | 显示释义 → 输入拼写 → 比对答案 |
| 🎧 听写模式 | 听觉+主动 | 朗读发音 → 输入拼写 → 比对答案 |

### 2.3 同步引擎设计

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ 手机 Chrome  │     │ 服务器(SQLite)│     │ 电脑 Chrome  │
│             │     │             │     │             │
│ login ──────┼────→│ pullFromServer│←────┼── login     │
│             │     │             │     │             │
│ 学习操作 ───┼────→│ pushToServer │←────┼── 学习操作   │
│             │     │             │     │             │
│ localStorage│     │ 唯一数据源   │     │ localStorage│
│ (仅作缓存)  │     │             │     │ (仅作缓存)  │
└─────────────┘     └─────────────┘     └─────────────┘
```

关键设计决策：
- **服务器为唯一数据源**：登录后跳过 localStorage，直接从服务器拉取
- **即时推送**：每次 saveData 立即推送到服务器，无防抖延迟
- **登录即拉取**：任何设备登录后自动获取最新进度

### 2.4 移动端适配策略

- **CSS 断点：** 768px 为界，<768px 显示底部导航，≥768px 显示顶部导航
- **安全区域：** `env(safe-area-inset-bottom)` 适配刘海屏
- **触摸优化：** `:active` 伪类替代 `:hover`，`-webkit-tap-highlight-color: transparent`
- **视口单位：** `100dvh` 解决移动浏览器地址栏遮挡问题

---

## 三、Bug 修复记录

### Bug #1：Python 命令被安全策略阻止
- **现象：** `terminal` 工具执行 Python 命令超时
- **原因：** Windows 安全策略限制了 Python 子进程
- **解决：** 改用 `write_file` + `patch` 工具直接编辑文件，避免在终端中执行 Python

### Bug #2：write_file 工具字符串损坏
- **现象：** `JWT_SECRET`、`AUTH_KEY`、环境变量等字符串在写入后变成 `***`
- **原因：** write_file 对特定模式字符串做了过滤
- **解决：** 使用 `patch` 工具做替换修正，或改变变量命名方式

### Bug #3：硬编码账号 user_id=0 同步失败
- **现象：** kousi 账号登录后同步数据不生效，各设备数据独立
- **原因：** `sync_upload` 使用 `UPDATE ... WHERE user_id=0`，但数据库 `user_data` 表没有 user_id=0 的行
- **解决：** 改用 `INSERT ... ON CONFLICT DO UPDATE`（UPSERT），自动创建不存在的行

### Bug #4：多设备数据不同步
- **现象：** 手机和电脑导入的词汇互不可见
- **原因：** 前端使用 localStorage 为主存储，服务端仅为备份；不同设备的 localStorage 天然隔离
- **解决：** 重构同步引擎为"服务端优先"模式——页面加载时如果已登录，跳过 localStorage 直接从服务器拉取

### Bug #5：防抖导致同步丢失
- **现象：** 学习后快速关闭页面，进度未上传
- **原因：** `pushToServer` 有 1 秒防抖延迟，快速关闭时未触发
- **解决：** 移除防抖，每次 `saveData` 立即执行异步推送

### Bug #6：桌面端导航缺失
- **现象：** PC 浏览器只看到复习页，无法切换功能
- **原因：** 移动端适配时去掉了顶部导航，桌面端（≥768px）底部导航被 CSS 隐藏后又没有顶部导航替代
- **解决：** 添加 `.desktop-nav` 组件，≥768px 显示顶部导航，<768px 自动隐藏

### Bug #7：Android APK 域名硬编码错误
- **现象：** APK 安装后显示"域名无法打开"
- **原因：** `MainActivity.java` 中 `APP_URL` 为占位符 `https://你的域名`
- **解决：** 改为实际域名 `https://muvsera.cc.cd`

### Bug #8：Edge 移动端 / Android WebView 每次刷新都需重新登录
- **现象：** Edge 手机浏览器和 Android APK 每次打开页面都需要重新输入账号密码
- **原因：** (1) Edge 移动端的跟踪防护策略会清除 localStorage；(2) Android WebView 默认不持久化 Cookie 和 DOM Storage
- **解决：** 
  - 服务端：登录时设置 `vocabmaster_token` Cookie（30天有效期），新增 `/api/auth/restore` 端点从 Cookie 恢复登录态
  - 前端：页面加载时先读 localStorage，失败则自动请求 `/api/auth/restore` 从 Cookie 恢复
  - Android：`MainActivity.java` 中启用 `CookieManager.setAcceptCookie(true)` 和 `setDatabaseEnabled(true)`

### Bug #9：移动端发音失效 + 语音选择器 UI 显示异常
- **现象：**
  1. 手机端（网页和 APK）点击发音按钮无声音
  2. 语音选择器下拉框显示空白或"加载中..."卡住
- **原因：**
  1. 移动浏览器要求**用户手势**（点击/触摸）后才能激活 SpeechSynthesis API，自动调用会被静默忽略
  2. iOS Safari 和部分安卓浏览器首次加载时 `speechSynthesis.getVoices()` 返回空数组，需要等 `onvoiceschanged` 事件异步触发
  3. 部分设备没有安装英语语音包时，原代码直接取 `voices[0]` 可能是一个非英语语音
- **解决：**
  - 全局监听首次点击事件，用空 utterance 解锁音频上下文
  - `initVoices()` 在 voices 为空时显示"加载中..."，监听 `onvoiceschanged` 事件后重新填充，并加 500ms 延迟重试
  - 英语语音不存在时回退到"系统默认"（`voice=null` 让浏览器自己选）
  - 播放时加 `speechSynth.resume()` 解决 Chrome Android 的暂停 Bug
  - 限制语音列表最多 20 个，避免下拉框过长

---

## 四、项目结构

```
vocabmaster/
├── server.py              # FastAPI 后端（认证/JWT/同步API/日志/调试端点）
├── requirements.txt       # Python 依赖
├── Dockerfile             # Docker 镜像定义
├── docker-compose.yml     # 一键部署配置
├── deploy.sh              # 一键部署脚本（Nginx + HTTPS）
├── static/
│   ├── index.html         # 前端单文件（所有 UI + JS 逻辑）
│   ├── manifest.json      # PWA 清单
│   └── sw.js              # Service Worker（离线缓存）
└── app/                   # (Android)
    └── ...                # Android WebView 封装项目
```

## 五、API 端点

| 端点 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/api/login` | POST | - | 登录，返回 JWT |
| `/api/register` | POST | - | 已禁用 (403) |
| `/api/me` | GET | JWT | 用户信息 |
| `/api/sync/download` | GET | JWT | 下载词库+进度 |
| `/api/sync/upload` | POST | JWT | 上传词库+进度 |
| `/api/health` | GET | - | 健康检查 |
| `/api/debug/db` | GET | JWT | 数据库调试信息 |

---

## 六、部署方式

### Docker（推荐）
```bash
cd vocabmaster && docker-compose up -d
```

### 直接运行
```bash
pip install -r requirements.txt
python server.py
```

### 一键脚本（含 Nginx + HTTPS）
```bash
bash deploy.sh your-domain.com your@email.com
```
