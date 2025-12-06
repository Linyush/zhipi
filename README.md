# 智批 - AI 作业批改系统

基于 FastAPI + OCR + DeepSeek AI 的智能作业批改系统，支持手机扫码上传作业图片，自动进行 OCR 识别和 AI 批改。

**智能批改，轻松高效**

## 功能特点

- 📱 **手机扫码上传**：生成二维码，手机扫码即可上传作业图片
- 🔍 **OCR 文字识别**：支持腾讯云、百度、阿里云等多种 OCR 服务
- 🤖 **AI 智能批改**：使用 DeepSeek AI 进行作业批改
- 📊 **批改计划管理**：支持创建多个批改计划，每个计划可自定义批改要求
- 💾 **本地数据存储**：所有数据本地存储，安全可靠
- 🌐 **跨平台支持**：支持 macOS、Linux 系统

## 系统要求

- Python 3.8 或更高版本
- 稳定的网络连接（用于 OCR 和 AI API 调用）

## 快速开始（一键启动）

### macOS/Linux 系统

1. **运行启动脚本**
   ```bash
   cd /path/to/demo
   ./scripts/start.sh
   ```

2. **首次运行时**
   - 脚本自动探测 `python`/`python3`（要求 ≥ 3.8）
   - 自动创建虚拟环境并安装依赖包
   - 若缺少 `.env`，在无 `.env.example` 时会生成最小模板并提示编辑

3. **填写配置**
   - 编辑 `.env` 文件，填入你的 API 密钥（见下方"获取 API 密钥"部分）
   - 保存后重新运行 `./scripts/start.sh`

4. **服务启动**
   - 服务会自动在后台运行
   - 浏览器会自动打开系统首页
   - 日志保存在 `logs/server.log`

5. **停止服务**
   ```bash
   ./scripts/stop.sh
   ```

6. **调试模式（可选）**

   如果需要在前台运行并查看实时日志：
   ```bash
   ./scripts/start.sh --debug
   ```

   调试模式特点：
   - 前台运行，日志直接输出到终端
   - 按 `Ctrl+C` 即可停止服务
   - 方便查看详细的运行日志和错误信息
   - 适合开发和问题排查

## 配置说明

### 获取 API 密钥

#### DeepSeek API
1. 访问 [DeepSeek 开放平台](https://platform.deepseek.com/)
2. 注册并登录
3. 在控制台创建 API Key

#### 腾讯云 OCR
1. 访问 [腾讯云控制台](https://console.cloud.tencent.com/)
2. 开通文字识别（OCR）服务
3. 在访问管理 > API 密钥管理获取 SecretId 和 SecretKey

#### 百度 OCR（可选）
1. 访问 [百度 AI 开放平台](https://ai.baidu.com/)
2. 创建文字识别应用
3. 获取 API Key 和 Secret Key

### 配置文件示例（.env）

```env
# DeepSeek API 配置
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# OCR 配置（选择一个提供商）
OCR_PROVIDER=tencent  # 可选: tencent, baidu, ali

# 腾讯云 OCR 配置（如果使用 tencent）
TENCENT_SECRET_ID=your_secret_id_here
TENCENT_SECRET_KEY=your_secret_key_here
TENCENT_REGION=ap-guangzhou

# 服务器配置
SERVER_PORT=8000
DATA_DIR=./data
```

## 使用系统

启动成功后，系统会自动打开浏览器：

1. 点击"新建"创建批改计划
2. 填写计划名称、描述和批改要求
3. 鼠标悬停在"扫码录入"上查看二维码
4. 用手机扫码上传作业图片
5. 系统自动进行 OCR 识别和 AI 批改

## 手动启动（高级用户）

如果需要手动控制启动过程：

#### macOS/Linux 系统
```bash
cd /path/to/demo
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## 项目结构

```
demo/
├── main.py                 # 主程序入口
├── ocr_adapters.py        # OCR 适配器（支持多种 OCR 服务）
├── requirements.txt       # Python 依赖包列表
├── .env.example          # 环境变量配置示例
├── .env                  # 环境变量配置（需自行创建）
├── README.md             # 项目说明文档
├── scripts/              # 启动和管理脚本
│   ├── start.sh         # macOS/Linux 启动脚本
│   └── stop.sh          # macOS/Linux 停止脚本
├── static/               # 静态文件目录
│   ├── pc.html          # 电脑端界面
│   └── mobile.html      # 手机端界面
├── logs/                 # 日志目录（自动创建）
│   └── server.log       # 服务运行日志
└── data/                 # 数据存储目录（自动创建）
    └── [计划名称]/
        ├── config.json   # 计划配置
        ├── images/       # 作业图片
        └── records/      # 批改记录
```

## 常见问题

### Q1: 提示"未检测到 Python"怎么办？
**A**: 请确保已正确安装 Python，并将 Python 添加到系统环境变量 PATH 中。

### Q2: pip 安装依赖失败怎么办？
**A**: 
```bash
# 尝试升级 pip
python -m pip install --upgrade pip

# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q3: OCR 识别失败怎么办？
**A**: 
- 检查 `.env` 文件中的 OCR 配置是否正确
- 确保网络连接正常
- 查看控制台输出的错误信息

### Q4: 手机无法访问系统怎么办？
**A**: 
- 确保手机和电脑在同一局域网
- 检查电脑防火墙设置，允许 8000 端口
- Windows 系统可能需要在防火墙中添加规则

### Q5: 如何在局域网内其他设备访问？
**A**: 
1. 查看启动日志中显示的本机 IP 地址
2. 在其他设备浏览器访问 `http://本机IP:8000/static/pc.html`
3. 手机扫码时确保在同一局域网内

## 技术栈

- **后端框架**: FastAPI
- **OCR 服务**: 腾讯云 OCR / 百度 OCR / 阿里云 OCR
- **AI 模型**: DeepSeek Chat
- **前端**: 原生 HTML + CSS + JavaScript
- **数据存储**: JSON 本地文件

## 开发说明

### 添加新的 OCR 提供商

1. 在 `ocr_adapters.py` 中创建新的适配器类
2. 继承 `OCRAdapter` 基类
3. 实现 `recognize()` 方法
4. 在 `create_ocr_adapter()` 工厂方法中注册

### 自定义批改 Prompt

在创建批改计划时，可以自定义批改要求。建议的 Prompt 格式：

```
你是一名耐心且专业的[年级][科目]老师。请仔细查看学生提交的作业图片，并提供详细的批改意见。

批改要求：
1. 指出错误并说明原因
2. 给出正确答案
3. 提供改进建议
4. 评分（满分100分）

请使用友好、鼓励的语气，帮助学生理解和进步。
```

## 许可证

本项目仅供学习和研究使用。

## 联系方式

如有问题或建议，欢迎提出 Issue。
