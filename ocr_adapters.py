"""
OCR 适配器模块
支持多个 OCR 服务提供商，可通过配置切换
"""

import os
import json
import base64
import hashlib
import hmac
import time
from abc import ABC, abstractmethod
from typing import List, Dict
import requests


class OCRAdapter(ABC):
    """OCR 适配器基类"""

    @abstractmethod
    def recognize(self, image_base64: str) -> str:
        """
        识别图片中的文字

        Args:
            image_base64: base64 编码的图片数据

        Returns:
            识别出的文字内容
        """
        pass


class TencentOCRAdapter(OCRAdapter):
    """腾讯云 OCR 适配器"""

    def __init__(self, secret_id: str, secret_key: str, region: str = "ap-guangzhou"):
        """
        初始化腾讯云 OCR

        Args:
            secret_id: 腾讯云 SecretId
            secret_key: 腾讯云 SecretKey
            region: 地域，默认广州
        """
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.endpoint = "ocr.tencentcloudapi.com"
        self.service = "ocr"
        self.version = "2018-11-19"

    def _sign(self, params: dict, timestamp: int) -> str:
        """生成腾讯云 API 签名"""
        # 1. 拼接规范请求串
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        canonical_headers = f"content-type:application/json\nhost:{self.endpoint}\n"
        signed_headers = "content-type;host"
        payload = json.dumps(params)
        hashed_request_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        canonical_request = (
            http_request_method + "\n" +
            canonical_uri + "\n" +
            canonical_querystring + "\n" +
            canonical_headers + "\n" +
            signed_headers + "\n" +
            hashed_request_payload
        )

        # 2. 拼接待签名字符串
        algorithm = "TC3-HMAC-SHA256"
        date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))
        credential_scope = f"{date}/{self.service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = (
            algorithm + "\n" +
            str(timestamp) + "\n" +
            credential_scope + "\n" +
            hashed_canonical_request
        )

        # 3. 计算签名
        def _hmac_sha256(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

        secret_date = _hmac_sha256(("TC3" + self.secret_key).encode("utf-8"), date)
        secret_service = _hmac_sha256(secret_date, self.service)
        secret_signing = _hmac_sha256(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        # 4. 拼接 Authorization
        authorization = (
            algorithm + " " +
            "Credential=" + self.secret_id + "/" + credential_scope + ", " +
            "SignedHeaders=" + signed_headers + ", " +
            "Signature=" + signature
        )

        return authorization

    def recognize(self, image_base64: str) -> str:
        """
        使用腾讯云 OCR 识别图片

        Args:
            image_base64: base64 编码的图片数据

        Returns:
            识别出的文字内容
        """
        action = "GeneralBasicOCR"
        timestamp = int(time.time())

        # 请求参数
        params = {
            "ImageBase64": image_base64
        }

        # 生成签名
        authorization = self._sign(params, timestamp)

        # 请求头
        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json",
            "Host": self.endpoint,
            "X-TC-Action": action,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": self.version,
            "X-TC-Region": self.region
        }

        # 发送请求
        url = f"https://{self.endpoint}"
        response = requests.post(url, headers=headers, json=params, timeout=30)

        if response.status_code != 200:
            raise Exception(f"腾讯云 OCR 调用失败: {response.status_code} - {response.text}")

        result = response.json()

        # 检查错误
        if "Response" not in result:
            raise Exception(f"腾讯云 OCR 返回格式错误: {result}")

        if "Error" in result["Response"]:
            error = result["Response"]["Error"]
            raise Exception(f"腾讯云 OCR 错误: {error.get('Code')} - {error.get('Message')}")

        # 提取识别的文字
        text_detections = result["Response"].get("TextDetections", [])
        recognized_text = "\n".join([item["DetectedText"] for item in text_detections])

        return recognized_text


class BaiduOCRAdapter(OCRAdapter):
    """百度 OCR 适配器（占位，可扩展）"""

    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = None

    def _get_access_token(self) -> str:
        """获取百度 OCR access token"""
        if self.access_token:
            return self.access_token

        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }
        response = requests.post(url, params=params, timeout=10)
        result = response.json()

        if "access_token" not in result:
            raise Exception(f"获取百度 access_token 失败: {result}")

        self.access_token = result["access_token"]
        return self.access_token

    def recognize(self, image_base64: str) -> str:
        """使用百度 OCR 识别图片"""
        access_token = self._get_access_token()
        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={access_token}"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"image": image_base64}

        response = requests.post(url, headers=headers, data=data, timeout=30)
        result = response.json()

        if "error_code" in result:
            raise Exception(f"百度 OCR 错误: {result.get('error_code')} - {result.get('error_msg')}")

        words_result = result.get("words_result", [])
        recognized_text = "\n".join([item["words"] for item in words_result])

        return recognized_text


class AliOCRAdapter(OCRAdapter):
    """阿里云 OCR 适配器（占位，可扩展）"""

    def __init__(self, access_key_id: str, access_key_secret: str):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret

    def recognize(self, image_base64: str) -> str:
        """使用阿里云 OCR 识别图片"""
        # TODO: 实现阿里云 OCR 调用
        raise NotImplementedError("阿里云 OCR 适配器待实现")


def create_ocr_adapter(provider: str, **kwargs) -> OCRAdapter:
    """
    工厂方法：创建 OCR 适配器

    Args:
        provider: OCR 提供商 (tencent/baidu/ali)
        **kwargs: 提供商特定的参数

    Returns:
        OCR 适配器实例
    """
    provider = provider.lower()

    if provider == "tencent":
        return TencentOCRAdapter(
            secret_id=kwargs.get("secret_id"),
            secret_key=kwargs.get("secret_key"),
            region=kwargs.get("region", "ap-guangzhou")
        )
    elif provider == "baidu":
        return BaiduOCRAdapter(
            api_key=kwargs.get("api_key"),
            secret_key=kwargs.get("secret_key")
        )
    elif provider == "ali":
        return AliOCRAdapter(
            access_key_id=kwargs.get("access_key_id"),
            access_key_secret=kwargs.get("access_key_secret")
        )
    else:
        raise ValueError(f"不支持的 OCR 提供商: {provider}，支持的有: tencent, baidu, ali")
