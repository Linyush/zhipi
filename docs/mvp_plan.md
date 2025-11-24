# AI 作业批改系统 MVP 版开发计划

## 一、项目目标

开发一个可在手机和电脑同时使用的网页应用，实现作业的拍照上传与 AI 批改显示功能：

* 手机端：用于拍照、录入作业
* 电脑端：用于查看作业与批改结果
* 服务端：负责保存数据并调用 deepseek 多模态模型进行批改

本版本为 MVP（最小可用版本）：

* 不需要登录
* 不需要权限控制
* 不需要复杂 UI
* 不需要数据库
* 不需要部署到公网
* 可本地运行，局域网内手机+电脑访问即可
* 支持 windows 系统和 macOS 系统，可在本地运行(注意区分存储目录)

目标：本人每天可以实际用来批改作业

## 二、技术栈

### 后端

* Python 3.9+
* FastAPI
* Uvicorn
* 本地文件系统存储
* requests（用于调 deepseek API）

安装依赖：

```bash
pip install fastapi uvicorn python-multipart requests qrcode[pil] python-dotenv
```

**依赖说明**：
* `qrcode[pil]`：生成二维码
* `python-dotenv`：管理环境变量（API Key 等）

### 前端

* 纯 HTML + JavaScript + CSS
* 两个页面：

    * `mobile.html` —— 手机端
    * `pc.html` —— 电脑端

## 三、核心功能范围

### 电脑端（管理页面）

**批改计划管理**：
1. 显示所有批改计划列表
2. 创建新的批改计划（输入计划名称）
3. 编辑批改计划的 prompt
4. 生成当前批改计划的二维码（包含局域网 IP + 计划名称）
5. 修改 prompt 后，可选择批量重新批改已有作业

**批改记录查看**：
1. 选择某个批改计划，查看其下所有批改记录
2. 自动每 5 秒刷新记录列表
3. 列表显示：学生姓名、提交时间、状态、重新批改次数
4. 点击展开显示：作业图片 + 批改结果（Markdown 格式）
5. 支持勾选多个记录，批量重新批改
6. 如果有历史批改结果，可以查看对比

### 手机端

1. 输入学生姓名 / 学号
2. 选择 / 拍摄 1 ~ 多张作业照片
3. 点击【提交批改】按钮
4. 显示上传成功提示，并重复步骤 1 ~ 3

### 后端 API

**批改计划管理**：
1. `POST /plans`：创建批改计划
   - 请求体：`{"plan_name": "语文作业1", "prompt": "..."}`
   - 返回：计划信息
2. `GET /plans`：获取所有批改计划列表
3. `GET /plans/{plan_name}`：获取单个计划详情
4. `PUT /plans/{plan_name}/prompt`：更新批改 prompt
   - 请求体：`{"prompt": "新的批改要求..."}`
5. `POST /plans/{plan_name}/regrade`：批量重新批改
   - 请求体：`{"record_ids": ["id1", "id2", ...]}`（可选，不传则批改所有）
   - 功能：将指定记录状态重置为 `pending`，触发重新批改
   - 保留原批改结果到 `previous_result` 字段
   - 返回：受影响的记录数量
6. `GET /plans/{plan_name}/qrcode`：生成二维码图片
   - 返回：PNG 图片
   - 二维码内容：`http://{局域网IP}:8000/static/mobile.html?plan={plan_name}`

**作业提交与批改**：
7. `POST /upload/{plan_name}`：上传作业图片
   - 表单数据：`student`（学生姓名）、`images`（图片文件）
   - 创建批改任务，状态为 `pending`
   - **异步调用** deepseek API 进行批改
   - 返回：任务 ID
8. `GET /records/{plan_name}`：获取批改计划下所有记录列表
9. `GET /records/{plan_name}/{id}`：获取单条批改记录详情

**系统信息**：
10. `GET /system/ip`：获取本机局域网 IP 地址（用于二维码生成）

### 数据存储

**目录结构**：

```
项目根目录/
  .env                        ← DeepSeek API Key 配置
  data/
    /${plan_name}/
      config.json             ← 批改计划配置（prompt、创建时间等）
      images/                 ← 作业图片
        ${timestamp}_1.jpg
        ${timestamp}_2.jpg
      records/                ← 批改记录 JSON
        ${timestamp}.json
```

**批改计划配置示例** (`config.json`)：

```json
{
  "plan_name": "语文作业1",
  "prompt": "你是一名耐心且专业的小学四年级语文老师...",
  "created_at": "2025-01-15T10:30:00"
}
```

**批改记录示例** (`records/${timestamp}.json`)：

```json
{
  "id": "1737012345678",
  "student": "张三",
  "images": ["images/1737012345678_1.jpg", "images/1737012345678_2.jpg"],
  "status": "done",
  "result": "这里是 deepseek 返回的批改内容（Markdown 格式）",
  "previous_result": "上一次批改结果（重新批改后保留）",
  "regrade_count": 1,
  "created_at": "2025-01-15T14:30:45",
  "updated_at": "2025-01-15T14:30:50"
}
```

**字段说明**：
- `previous_result`：重新批改时保留的上一次结果（首次批改时不存在）
- `regrade_count`：重新批改次数（默认 0）

**状态说明**：
* `pending`：等待批改
* `processing`：批改中
* `done`：批改完成
* `failed`：批改失败（包含错误信息）

**路径处理**：
* Windows：使用 `os.path.join()` 和 `pathlib.Path`
* macOS/Linux：同样使用标准库，自动适配

### deepseek 调用说明

**API 配置**：
* API Key 存储在 `.env` 文件中：`DEEPSEEK_API_KEY=sk-xxx`
* API 地址：`https://api.deepseek.com/v1/chat/completions`
* 使用模型：`deepseek-chat`（支持视觉多模态）

**调用方式**：
* **异步调用**：上传接口立即返回，后台异步调用 AI
* 状态更新：`pending` → `processing` → `done/failed`
* 超时时间：60 秒
* 错误重试：失败后不自动重试，状态标记为 `failed`，记录错误信息

**输入**：
* 图片：Base64 编码或图片 URL
* Prompt：从 `config.json` 读取当前计划的批改要求

**输出**：
* 批改结果保存到 `record['result']`，支持 Markdown 格式

**图片限制**：
* 单次最多 10 张图片
* 单张图片最大 10MB
* 支持格式：JPG、PNG、WEBP

**Prompt 示例**：

```
你是一名耐心且专业的小学四年级语文老师。请仔细查看学生提交的作业图片，并提供详细的批改意见。

要求：
1. 指出错误的字词，并给出正确写法
2. 评价书写工整度
3. 提出改进建议
4. 给出鼓励性评语

请用 Markdown 格式输出，包含：
- 总体评价
- 具体问题列表
- 改进建议
- 得分（满分100）
```

**错误处理**：
* API 调用失败：记录错误信息到 `record['error']`，状态设为 `failed`
* 网络超时：同上
* 图片格式错误：上传时提前验证并拒绝


## 四、项目目录结构

```
ai-homework/
  main.py                    # FastAPI 主程序
  .env                       # 环境变量配置（API Key）
  .env.example               # 环境变量示例
  requirements.txt           # Python 依赖
  data/                      # 数据目录（自动创建）
    语文作业1/
      config.json
      images/
      records/
    数学作业1/
      config.json
      images/
      records/
  static/                    # 静态文件
    mobile.html              # 手机端页面
    pc.html                  # 电脑端页面
    style.css                # 样式文件（可选）
```

**配置文件示例** (`.env`)：

```env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
SERVER_PORT=8000
DATA_DIR=./data
```

**访问方式**：

* 电脑：运行 `python main.py` 后，自动在浏览器打开 `http://localhost:8000/static/pc.html`
* 手机：在电脑端选择批改计划，点击生成二维码，手机扫描后打开 `http://{局域网IP}:8000/static/mobile.html?plan={plan_name}`

## 五、开发步骤

### 第零步：项目初始化

* 创建项目目录和基本结构
* 创建 `requirements.txt` 和 `.env.example`
* 实现配置管理（读取 `.env`）
* 实现跨平台路径处理
* **验收**：能正确读取配置，自动创建 `data/` 目录

### 第一步：批改计划管理

* 实现 `POST /plans` - 创建批改计划
* 实现 `GET /plans` - 获取计划列表
* 实现 `PUT /plans/{plan_name}/prompt` - 更新 prompt
* 自动创建 `config.json` 并保存
* **验收**：能创建计划、读取计划列表、更新 prompt

### 第二步：二维码生成

* 实现 `GET /system/ip` - 获取本机局域网 IP
* 实现 `GET /plans/{plan_name}/qrcode` - 生成二维码
* **验收**：能生成包含正确 URL 的二维码图片

### 第三步：作业上传功能

* 实现 `POST /upload/{plan_name}` 接口
* 验证图片格式和大小
* 保存图片到本地
* 创建批改记录 JSON，状态为 `pending`
* **验收**：手机能上传图片，本地能看到图片和 JSON 文件

### 第四步：记录查询接口

* 实现 `GET /records/{plan_name}` - 获取记录列表
* 实现 `GET /records/{plan_name}/{id}` - 获取单条记录
* **验收**：电脑端能看到上传的任务列表

### 第五步：接入 deepseek（异步）

* 实现异步任务处理（使用 `asyncio` 或 `threading`）
* 上传后触发后台批改任务
* 状态更新：`pending` → `processing` → `done/failed`
* 调用 deepseek API，传入图片和 prompt
* 保存批改结果到 JSON
* **验收**：上传后能自动批改，JSON 文件中出现批改结果

### 第六步：电脑端页面

* 实现批改计划列表和创建界面
* 实现 prompt 编辑功能
* 实现二维码显示
* 实现批改记录列表（自动每 5 秒刷新）
* 实现记录详情展示（图片 + Markdown 结果）
* 实现批量重新批改功能（勾选 + 批量操作）
* 实现历史批改结果对比查看
* **验收**：电脑端能完整管理计划、查看批改结果、批量重新批改

### 第七步：手机端页面

* 实现学生姓名输入
* 实现图片选择/拍照功能
* 实现上传按钮和进度提示
* 上传成功后清空表单，可连续录入
* **验收**：手机端能流畅上传多份作业

### 第八步：完善和测试

* 错误处理和提示优化
* 加载状态和进度提示
* 跨浏览器兼容性测试
* Windows/macOS 兼容性测试
* **验收**：全流程无需人工干预，实际使用无障碍

## 六、MVP 达标标准

✅ 手机拍照上传成功
✅ 学生名字与图片保存成功
✅ deepseek 参与批改
✅ 电脑端能看到结果
✅ 修改 prompt 后能批量重新批改
✅ 全流程无需人工干预

## 七、使用场景示例

**场景 1：首次使用**
1. 电脑端创建"语文作业第一单元"计划，设置批改 prompt
2. 生成二维码，打印或分享给学生
3. 学生手机扫码，上传作业照片
4. 系统自动批改，老师在电脑端查看结果

**场景 2：调整批改标准**
1. 老师发现批改要求不够严格，需要调整 prompt
2. 在电脑端修改 prompt，增加更多批改要求
3. 勾选已批改的作业，点击"批量重新批改"
4. 系统使用新 prompt 重新批改，可对比新旧结果
5. 老师确认新结果更合理，采用新批改结果
