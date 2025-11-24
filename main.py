import os
import json
import time
import socket
import threading
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import qrcode
from io import BytesIO
import base64
import requests

# 导入 OCR 适配器
from ocr_adapters import create_ocr_adapter, OCRAdapter


# ==================== 配置管理 ====================

# 加载环境变量
load_dotenv()

class Config:
    """全局配置类"""
    # DeepSeek API 配置
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

    # OCR 配置
    OCR_PROVIDER = os.getenv("OCR_PROVIDER", "tencent").lower()

    # 腾讯云 OCR 配置
    TENCENT_SECRET_ID = os.getenv("TENCENT_SECRET_ID", "")
    TENCENT_SECRET_KEY = os.getenv("TENCENT_SECRET_KEY", "")
    TENCENT_REGION = os.getenv("TENCENT_REGION", "ap-guangzhou")

    # 百度 OCR 配置
    BAIDU_API_KEY = os.getenv("BAIDU_API_KEY", "")
    BAIDU_SECRET_KEY = os.getenv("BAIDU_SECRET_KEY", "")

    # 阿里云 OCR 配置
    ALI_ACCESS_KEY_ID = os.getenv("ALI_ACCESS_KEY_ID", "")
    ALI_ACCESS_KEY_SECRET = os.getenv("ALI_ACCESS_KEY_SECRET", "")

    # 服务器配置
    SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
    DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))

    # 文件上传限制
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_IMAGES_PER_UPLOAD = 10
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

    # OCR 适配器实例（延迟初始化）
    _ocr_adapter: Optional[OCRAdapter] = None

    @classmethod
    def init(cls):
        """初始化配置，创建必要的目录和 OCR 适配器"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        print(f"✓ 数据目录已创建: {cls.DATA_DIR.absolute()}")
        print(f"✓ 服务端口: {cls.SERVER_PORT}")

        if not cls.DEEPSEEK_API_KEY:
            print("⚠ 警告: DEEPSEEK_API_KEY 未设置")

        # 初始化 OCR 适配器
        try:
            cls._ocr_adapter = cls._create_ocr_adapter()
            print(f"✓ OCR 提供商: {cls.OCR_PROVIDER}")
        except Exception as e:
            print(f"⚠ 警告: OCR 适配器初始化失败: {e}")
            print(f"⚠ 请检查 .env 文件中的 OCR 配置")

    @classmethod
    def _create_ocr_adapter(cls) -> OCRAdapter:
        """创建 OCR 适配器"""
        if cls.OCR_PROVIDER == "tencent":
            if not cls.TENCENT_SECRET_ID or not cls.TENCENT_SECRET_KEY:
                raise ValueError("腾讯云 OCR 配置不完整，请设置 TENCENT_SECRET_ID 和 TENCENT_SECRET_KEY")
            return create_ocr_adapter(
                "tencent",
                secret_id=cls.TENCENT_SECRET_ID,
                secret_key=cls.TENCENT_SECRET_KEY,
                region=cls.TENCENT_REGION
            )
        elif cls.OCR_PROVIDER == "baidu":
            if not cls.BAIDU_API_KEY or not cls.BAIDU_SECRET_KEY:
                raise ValueError("百度 OCR 配置不完整，请设置 BAIDU_API_KEY 和 BAIDU_SECRET_KEY")
            return create_ocr_adapter(
                "baidu",
                api_key=cls.BAIDU_API_KEY,
                secret_key=cls.BAIDU_SECRET_KEY
            )
        elif cls.OCR_PROVIDER == "ali":
            if not cls.ALI_ACCESS_KEY_ID or not cls.ALI_ACCESS_KEY_SECRET:
                raise ValueError("阿里云 OCR 配置不完整，请设置 ALI_ACCESS_KEY_ID 和 ALI_ACCESS_KEY_SECRET")
            return create_ocr_adapter(
                "ali",
                access_key_id=cls.ALI_ACCESS_KEY_ID,
                access_key_secret=cls.ALI_ACCESS_KEY_SECRET
            )
        else:
            raise ValueError(f"不支持的 OCR 提供商: {cls.OCR_PROVIDER}")

    @classmethod
    def get_ocr_adapter(cls) -> OCRAdapter:
        """获取 OCR 适配器实例"""
        if cls._ocr_adapter is None:
            cls._ocr_adapter = cls._create_ocr_adapter()
        return cls._ocr_adapter


# ==================== 路径工具 ====================

class PathHelper:
    """跨平台路径处理工具"""

    @staticmethod
    def get_plan_dir(plan_name: str) -> Path:
        """获取批改计划目录"""
        return Config.DATA_DIR / plan_name

    @staticmethod
    def get_config_path(plan_name: str) -> Path:
        """获取配置文件路径"""
        return PathHelper.get_plan_dir(plan_name) / "config.json"

    @staticmethod
    def get_images_dir(plan_name: str) -> Path:
        """获取图片目录"""
        return PathHelper.get_plan_dir(plan_name) / "images"

    @staticmethod
    def get_records_dir(plan_name: str) -> Path:
        """获取记录目录"""
        return PathHelper.get_plan_dir(plan_name) / "records"

    @staticmethod
    def get_record_path(plan_name: str, record_id: str) -> Path:
        """获取批改记录文件路径"""
        return PathHelper.get_records_dir(plan_name) / f"{record_id}.json"

    @staticmethod
    def ensure_plan_dirs(plan_name: str):
        """确保批改计划的所有目录存在"""
        PathHelper.get_images_dir(plan_name).mkdir(parents=True, exist_ok=True)
        PathHelper.get_records_dir(plan_name).mkdir(parents=True, exist_ok=True)


# ==================== 数据模型 ====================

class PlanCreate(BaseModel):
    plan_name: str
    description: str
    prompt: str

class PromptUpdate(BaseModel):
    prompt: str

class RegradeRequest(BaseModel):
    record_ids: Optional[List[str]] = None


# ==================== FastAPI 应用 ====================

app = FastAPI(title="智批 - AI 作业批改系统", version="1.0.0")

# CORS 中间件（允许跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 启动事件 ====================

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化配置"""
    Config.init()
    print("=" * 50)
    print("🚀 智批 - AI 作业批改系统启动成功")
    print("=" * 50)


# ==================== 工具函数 ====================

def get_local_ip() -> str:
    """获取本机局域网 IP 地址（跨平台兼容）"""
    import platform
    import subprocess

    try:
        system = platform.system()

        if system == "Windows":
            # Windows 使用 ipconfig
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, encoding='gbk')
            lines = result.stdout.split('\n')

            for i, line in enumerate(lines):
                if 'IPv4' in line or 'IP Address' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        ip = parts[1].strip()
                        # 优先选择 192.168 网段的 IP（WiFi）
                        if ip.startswith('192.168.'):
                            return ip
                        # 其次选择 10.0 网段
                        elif ip.startswith('10.'):
                            return ip
                        # 最后是其他内网 IP
                        elif ip.startswith('172.'):
                            return ip
        else:
            # macOS/Linux 使用 ifconfig
            result = subprocess.run(['ifconfig'], capture_output=True, text=True)
            lines = result.stdout.split('\n')

            ips = []
            for i, line in enumerate(lines):
                if 'inet ' in line and '127.0.0.1' not in line:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        ip = parts[1]
                        # 优先选择 192.168 网段的 IP（WiFi）
                        if ip.startswith('192.168.'):
                            return ip
                        # 其次选择 10.0 网段
                        elif ip.startswith('10.'):
                            ips.append(ip)
                        # 最后是其他内网 IP
                        elif ip.startswith('172.'):
                            ips.append(ip)

            # 如果有其他内网 IP，返回第一个
            if ips:
                return ips[0]

        # 后备方法：使用 socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        print(f"获取 IP 失败: {e}")
        return "127.0.0.1"


def save_json(path: Path, data: dict):
    """保存 JSON 文件"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(path: Path) -> dict:
    """读取 JSON 文件"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ==================== API 路由 ====================

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "智批 - AI 作业批改系统 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/system/ip")
async def get_system_ip():
    """获取本机局域网 IP 地址"""
    return {"ip": get_local_ip()}


# ==================== 批改计划管理 API ====================

@app.post("/plans")
async def create_plan(plan: PlanCreate):
    """创建批改计划"""
    plan_name = plan.plan_name.strip()

    # 验证计划名称
    if not plan_name:
        raise HTTPException(status_code=400, detail="计划名称不能为空")

    if "/" in plan_name or "\\" in plan_name:
        raise HTTPException(status_code=400, detail="计划名称不能包含路径分隔符")

    # 检查计划是否已存在
    config_path = PathHelper.get_config_path(plan_name)
    if config_path.exists():
        raise HTTPException(status_code=400, detail=f"批改计划 '{plan_name}' 已存在")

    # 创建目录结构
    PathHelper.ensure_plan_dirs(plan_name)

    # 创建配置文件
    config_data = {
        "plan_name": plan_name,
        "description": plan.description,
        "prompt": plan.prompt,
        "created_at": datetime.now().isoformat()
    }
    save_json(config_path, config_data)

    return {
        "message": "批改计划创建成功",
        "plan": config_data
    }


@app.get("/plans")
async def get_plans():
    """获取所有批改计划列表"""
    plans = []

    if not Config.DATA_DIR.exists():
        return {"plans": plans}

    # 遍历数据目录
    for plan_dir in Config.DATA_DIR.iterdir():
        if plan_dir.is_dir():
            config_path = PathHelper.get_config_path(plan_dir.name)
            if config_path.exists():
                try:
                    config = load_json(config_path)

                    # 统计记录数量
                    records_dir = PathHelper.get_records_dir(plan_dir.name)
                    record_count = len(list(records_dir.glob("*.json"))) if records_dir.exists() else 0

                    plans.append({
                        "plan_name": config.get("plan_name", plan_dir.name),
                        "description": config.get("description", ""),
                        "prompt": config.get("prompt", ""),
                        "created_at": config.get("created_at"),
                        "record_count": record_count
                    })
                except Exception as e:
                    print(f"读取计划配置失败 {plan_dir.name}: {e}")

    # 按创建时间排序
    plans.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {"plans": plans}


@app.get("/plans/{plan_name}")
async def get_plan(plan_name: str):
    """获取单个批改计划详情"""
    config_path = PathHelper.get_config_path(plan_name)

    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"批改计划 '{plan_name}' 不存在")

    try:
        config = load_json(config_path)

        # 统计记录数量和状态
        records_dir = PathHelper.get_records_dir(plan_name)
        stats = {
            "total": 0,
            "pending": 0,
            "processing": 0,
            "done": 0,
            "failed": 0
        }

        if records_dir.exists():
            for record_file in records_dir.glob("*.json"):
                try:
                    record = load_json(record_file)
                    status = record.get("status", "pending")
                    stats["total"] += 1
                    stats[status] = stats.get(status, 0) + 1
                except Exception:
                    pass

        return {
            "plan": config,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取配置失败: {str(e)}")


@app.put("/plans/{plan_name}/prompt")
async def update_prompt(plan_name: str, update: PromptUpdate):
    """更新批改计划的 prompt"""
    config_path = PathHelper.get_config_path(plan_name)

    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"批改计划 '{plan_name}' 不存在")

    try:
        config = load_json(config_path)
        config["prompt"] = update.prompt
        config["updated_at"] = datetime.now().isoformat()
        save_json(config_path, config)

        return {
            "message": "Prompt 更新成功",
            "plan": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


# ==================== 二维码生成 API ====================

@app.get("/plans/{plan_name}/qrcode")
async def generate_qrcode(plan_name: str):
    """生成批改计划的二维码"""
    config_path = PathHelper.get_config_path(plan_name)

    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"批改计划 '{plan_name}' 不存在")

    # 获取本机 IP
    ip = get_local_ip()

    # 生成二维码内容（手机端 URL）
    from urllib.parse import quote
    url = f"http://{ip}:{Config.SERVER_PORT}/static/mobile.html?plan={quote(plan_name)}"

    # 生成二维码
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # 生成图片
    img = qr.make_image(fill_color="black", back_color="white")

    # 转换为字节流
    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)

    return StreamingResponse(img_buffer, media_type="image/png")


# ==================== 作业上传与批改 API ====================

@app.post("/upload/{plan_name}")
async def upload_homework(
    plan_name: str,
    background_tasks: BackgroundTasks,
    student: str = Form(...),
    images: List[UploadFile] = File(...)
):
    """上传作业图片"""
    # 检查批改计划是否存在
    config_path = PathHelper.get_config_path(plan_name)
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"批改计划 '{plan_name}' 不存在")

    # 验证学生姓名
    if not student.strip():
        raise HTTPException(status_code=400, detail="学生姓名不能为空")

    # 验证图片数量
    if len(images) > Config.MAX_IMAGES_PER_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail=f"图片数量不能超过 {Config.MAX_IMAGES_PER_UPLOAD} 张"
        )

    # 生成记录 ID（时间戳）
    record_id = str(int(time.time() * 1000))
    images_dir = PathHelper.get_images_dir(plan_name)
    images_dir.mkdir(parents=True, exist_ok=True)

    # 保存图片并验证
    saved_images = []
    for idx, image in enumerate(images, 1):
        # 验证文件扩展名
        file_ext = Path(image.filename).suffix.lower()
        if file_ext not in Config.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的图片格式: {file_ext}，仅支持 {', '.join(Config.ALLOWED_EXTENSIONS)}"
            )

        # 读取文件内容
        content = await image.read()

        # 验证文件大小
        if len(content) > Config.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"图片 {image.filename} 超过大小限制 ({Config.MAX_IMAGE_SIZE / 1024 / 1024}MB)"
            )

        # 保存图片
        image_filename = f"{record_id}_{idx}{file_ext}"
        image_path = images_dir / image_filename
        with open(image_path, 'wb') as f:
            f.write(content)

        saved_images.append(f"images/{image_filename}")

    # 创建批改记录
    record = {
        "id": record_id,
        "student": student.strip(),
        "images": saved_images,
        "status": "pending",
        "result": "",
        "regrade_count": 0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    # 保存记录
    record_path = PathHelper.get_record_path(plan_name, record_id)
    save_json(record_path, record)

    # 触发后台批改任务
    background_tasks.add_task(process_homework, plan_name, record_id)

    return {
        "message": "作业上传成功",
        "record_id": record_id,
        "status": "pending"
    }


# ==================== 记录查询 API ====================

@app.get("/records/{plan_name}")
async def get_records(plan_name: str):
    """获取批改计划下所有记录列表"""
    config_path = PathHelper.get_config_path(plan_name)
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"批改计划 '{plan_name}' 不存在")

    records = []
    records_dir = PathHelper.get_records_dir(plan_name)

    if records_dir.exists():
        for record_file in records_dir.glob("*.json"):
            try:
                record = load_json(record_file)
                # 只返回部分信息（列表视图）
                records.append({
                    "id": record.get("id"),
                    "student": record.get("student"),
                    "status": record.get("status"),
                    "regrade_count": record.get("regrade_count", 0),
                    "created_at": record.get("created_at"),
                    "updated_at": record.get("updated_at")
                })
            except Exception as e:
                print(f"读取记录失败 {record_file}: {e}")

    # 按创建时间倒序排序
    records.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {"records": records}


@app.get("/records/{plan_name}/{record_id}")
async def get_record(plan_name: str, record_id: str):
    """获取单条批改记录详情"""
    record_path = PathHelper.get_record_path(plan_name, record_id)

    if not record_path.exists():
        raise HTTPException(status_code=404, detail=f"记录 {record_id} 不存在")

    try:
        record = load_json(record_path)
        return {"record": record}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取记录失败: {str(e)}")


@app.delete("/records/{plan_name}/{record_id}")
async def delete_record(plan_name: str, record_id: str):
    """删除批改记录"""
    config_path = PathHelper.get_config_path(plan_name)
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"批改计划 '{plan_name}' 不存在")

    record_path = PathHelper.get_record_path(plan_name, record_id)
    if not record_path.exists():
        raise HTTPException(status_code=404, detail=f"记录 {record_id} 不存在")

    try:
        # 读取记录以获取图片信息
        record = load_json(record_path)

        # 删除相关图片
        plan_dir = PathHelper.get_plan_dir(plan_name)
        for image_rel_path in record.get("images", []):
            image_path = plan_dir / image_rel_path
            if image_path.exists():
                image_path.unlink()

        # 删除记录文件
        record_path.unlink()

        return {
            "message": f"记录 {record_id} 已删除",
            "deleted": {
                "record_id": record_id,
                "student": record.get("student"),
                "images_count": len(record.get("images", []))
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除记录失败: {str(e)}")


# ==================== OCR + DeepSeek 批改处理 ====================

def process_homework(plan_name: str, record_id: str):
    """后台处理作业批改（OCR + DeepSeek）"""
    try:
        # 读取记录
        record_path = PathHelper.get_record_path(plan_name, record_id)
        record = load_json(record_path)

        # 更新状态为 processing
        record["status"] = "processing"
        record["updated_at"] = datetime.now().isoformat()
        save_json(record_path, record)

        # 读取批改计划配置
        config = load_json(PathHelper.get_config_path(plan_name))
        prompt = config.get("prompt", "请批改这份作业")

        # 步骤 1: 使用 OCR 识别图片中的文字
        print(f"开始 OCR 识别: {plan_name}/{record_id}")
        ocr_adapter = Config.get_ocr_adapter()
        recognized_texts = []
        plan_dir = PathHelper.get_plan_dir(plan_name)

        for idx, image_rel_path in enumerate(record["images"], 1):
            image_path = plan_dir / image_rel_path
            if image_path.exists():
                try:
                    # 读取图片并转换为 base64
                    with open(image_path, 'rb') as f:
                        img_data = f.read()
                        img_base64 = base64.b64encode(img_data).decode('utf-8')

                    # OCR 识别
                    text = ocr_adapter.recognize(img_base64)
                    if text.strip():
                        recognized_texts.append(f"【图片 {idx}】\n{text}")
                        print(f"OCR 识别成功: 图片 {idx}, 长度 {len(text)} 字符")
                    else:
                        print(f"OCR 识别结果为空: 图片 {idx}")
                except Exception as e:
                    print(f"OCR 识别失败 图片 {idx}: {e}")
                    recognized_texts.append(f"【图片 {idx}】\n(识别失败: {str(e)})")

        # 合并所有识别的文字
        if not recognized_texts:
            raise Exception("OCR 未识别到任何文字内容")

        all_text = "\n\n".join(recognized_texts)
        print(f"OCR 总共识别到 {len(all_text)} 字符")

        # 步骤 2: 调用 DeepSeek API 进行批改
        if not Config.DEEPSEEK_API_KEY:
            raise Exception("DEEPSEEK_API_KEY 未配置")

        # 构建完整的提示词
        full_prompt = f"""{prompt}

【学生作业内容】
{all_text}
"""

        print(f"调用 DeepSeek API 进行批改...")
        response = requests.post(
            Config.DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {Config.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.7
            },
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            correction = result["choices"][0]["message"]["content"]

            # 更新记录（保存 OCR 识别的文字和批改结果）
            record["status"] = "done"
            record["ocr_text"] = all_text  # 保存 OCR 识别的原始文字
            record["result"] = correction
            record["updated_at"] = datetime.now().isoformat()
            save_json(record_path, record)
            print(f"批改成功: {plan_name}/{record_id}")
        else:
            raise Exception(f"DeepSeek API 调用失败: {response.status_code} - {response.text}")

    except Exception as e:
        # 标记为失败
        try:
            record["status"] = "failed"
            record["error"] = str(e)
            record["updated_at"] = datetime.now().isoformat()
            save_json(record_path, record)
        except Exception:
            pass
        print(f"批改失败 {plan_name}/{record_id}: {e}")


# ==================== 批量重新批改 API ====================

@app.post("/plans/{plan_name}/regrade")
async def regrade_records(plan_name: str, request: RegradeRequest, background_tasks: BackgroundTasks):
    """批量重新批改"""
    config_path = PathHelper.get_config_path(plan_name)
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"批改计划 '{plan_name}' 不存在")

    records_dir = PathHelper.get_records_dir(plan_name)
    if not records_dir.exists():
        return {"message": "没有可批改的记录", "count": 0}

    # 确定要重新批改的记录
    if request.record_ids:
        # 指定记录
        record_ids = request.record_ids
    else:
        # 所有记录
        record_ids = [f.stem for f in records_dir.glob("*.json")]

    # 重新批改
    count = 0
    for record_id in record_ids:
        record_path = PathHelper.get_record_path(plan_name, record_id)
        if record_path.exists():
            try:
                record = load_json(record_path)

                # 保留上一次结果
                if record.get("result"):
                    record["previous_result"] = record["result"]

                # 重置状态
                record["status"] = "pending"
                record["result"] = ""
                record["regrade_count"] = record.get("regrade_count", 0) + 1
                record["updated_at"] = datetime.now().isoformat()
                save_json(record_path, record)

                # 触发后台批改任务
                background_tasks.add_task(process_homework, plan_name, record_id)
                count += 1
            except Exception as e:
                print(f"重新批改失败 {record_id}: {e}")

    return {
        "message": f"已触发 {count} 条记录重新批改",
        "count": count
    }


# ==================== 静态文件服务 ====================

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 挂载数据目录（用于访问上传的图片）
app.mount("/data", StaticFiles(directory=str(Config.DATA_DIR)), name="data")


# ==================== 主程序入口 ====================

if __name__ == "__main__":
    import uvicorn
    import webbrowser

    # 启动服务器
    print("\n正在启动服务器...")
    print(f"本机 IP: {get_local_ip()}")
    print(f"访问地址: http://localhost:{Config.SERVER_PORT}")
    print(f"API 文档: http://localhost:{Config.SERVER_PORT}/docs\n")

    # 自动打开浏览器（可选）
    # threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{Config.SERVER_PORT}/docs")).start()

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=Config.SERVER_PORT,
        reload=True
    )