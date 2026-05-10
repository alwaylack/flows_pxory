#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""==================================================================
简要描述: web_api.py - 配置管理API接口
编写作者: dongruihua
创建日期: 2025/1/20
修订说明: 提供HTTP API接口用于动态配置管理和证书管理
==================================================================="""

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Any, Dict, Optional
import asyncio
import threading

from config_manager import get_config_manager, reload_config
from ssl_cert_manager import get_cert_manager, ensure_certificate
from config import Config

app = FastAPI(
    title="流量录制配置管理API",
    description="提供动态配置管理和SSL证书管理的API接口",
    version="1.0.0",
)

templates = Jinja2Templates(directory="templates")


class ConfigUpdateRequest(BaseModel):
    """配置更新请求模型"""

    key: str
    value: Any


class ConfigBatchUpdateRequest(BaseModel):
    """批量配置更新请求模型"""

    updates: Dict[str, Any]


@app.get("/", response_class=HTMLResponse, tags=["系统"])
async def index(request: Request):
    """系统首页"""
    return templates.TemplateResponse(
        "index.html", {"request": request, "title": "流量录制系统"}
    )


@app.get("/config", tags=["配置管理"])
async def get_config():
    """
    获取当前所有配置（过滤敏感信息）
    :return: 配置字典
    """
    config_manager = get_config_manager()
    all_config = config_manager.get_all()

    # 过滤敏感配置项
    SENSITIVE_KEYS = {"PASSWORD", "PASS", "SECRET", "KEY", "TOKEN", "AUTH"}
    safe_config = {}
    for k, v in all_config.items():
        if any(s in k.upper() for s in SENSITIVE_KEYS):
            safe_config[k] = "*** (已隐藏)"
        else:
            safe_config[k] = v

    from datetime import datetime

    return {
        "status": "success",
        "data": safe_config,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/config/{key}", tags=["配置管理"])
async def get_config_value(key: str):
    """
    获取指定配置项的值
    :param key: 配置项键名
    :return: 配置项值
    """
    config_manager = get_config_manager()
    value = config_manager.get(key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"配置项 '{key}' 不存在")
    return {"status": "success", "key": key, "value": value}


@app.post("/config", tags=["配置管理"])
async def update_config(config_req: ConfigUpdateRequest):
    """
    更新单个配置项
    :param config_req: 配置更新请求
    :return: 更新结果
    """
    config_manager = get_config_manager()
    success = config_manager.set(config_req.key, config_req.value)
    if not success:
        raise HTTPException(
            status_code=500, detail=f"更新配置项 '{config_req.key}' 失败"
        )
    return {
        "status": "success",
        "message": f"配置项 '{config_req.key}' 已更新",
        "key": config_req.key,
        "value": config_req.value,
    }


@app.put("/config/batch", tags=["配置管理"])
async def batch_update_config(batch_req: ConfigBatchUpdateRequest):
    """
    批量更新配置项
    :param batch_req: 批量更新请求
    :return: 更新结果
    """
    config_manager = get_config_manager()
    results = {}
    errors = {}

    for key, value in batch_req.updates.items():
        try:
            success = config_manager.set(key, value)
            if success:
                results[key] = value
            else:
                errors[key] = "更新失败"
        except Exception as e:
            errors[key] = str(e)

    response = {
        "status": "success" if not errors else "partial_success",
        "updated": results,
        "errors": errors,
    }

    if errors:
        return JSONResponse(status_code=207, content=response)
    return response


@app.post("/config/reload", tags=["配置管理"])
async def reload_configuration():
    """
    手动触发配置重载
    :return: 重载结果
    """
    try:
        success = reload_config()
        if success:
            return {"status": "success", "message": "配置已重载"}
        else:
            raise HTTPException(status_code=500, detail="配置重载失败，文件可能未变更")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置重载失败: {str(e)}")


@app.get("/config/status", tags=["配置管理"])
async def get_config_status():
    """
    获取配置管理器状态
    :return: 状态信息
    """
    config_manager = get_config_manager()
    return {"status": "success", "data": config_manager.get_status()}


@app.get("/ssl/cert", tags=["SSL证书管理"])
async def get_cert_info():
    """
    获取SSL证书信息
    :return: 证书信息
    """
    cert_manager = get_cert_manager()
    info = cert_manager.get_cert_info()
    # 过滤证书路径中的用户主目录信息
    import os

    home = os.path.expanduser("~")
    for key, file_info in info.get("cert_files", {}).items():
        if isinstance(file_info, dict) and "path" in file_info:
            file_info["path"] = file_info["path"].replace(home, "~")
    return {"status": "success", "data": info}


@app.post("/ssl/cert/ensure", tags=["SSL证书管理"])
async def ensure_cert():
    """
    确保证书状态（检查并重新生成如果需要）
    :return: 操作结果
    """
    try:
        success = ensure_certificate()
        if success:
            cert_manager = get_cert_manager()
            return {
                "status": "success",
                "message": "证书状态确认成功",
                "data": cert_manager.get_cert_info(),
            }
        else:
            raise HTTPException(status_code=500, detail="证书状态确认失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"证书操作失败: {str(e)}")


@app.post("/ssl/cert/generate", tags=["SSL证书管理"])
async def generate_cert():
    """
    强制重新生成SSL证书
    :return: 操作结果
    """
    cert_manager = get_cert_manager()

    # 使用openssl生成新证书
    if cert_manager._generate_ssl_cert():
        # 安装到系统信任存储
        if cert_manager.AUTO_INSTALL_TRUSTED:
            cert_manager.auto_install_certificate()

        return {
            "status": "success",
            "message": "SSL证书已重新生成",
            "data": cert_manager.get_cert_info(),
        }
    else:
        raise HTTPException(status_code=500, detail="证书生成失败")


@app.post("/ssl/cert/install", tags=["SSL证书管理"])
async def install_cert():
    """
    将证书安装到系统信任存储
    :return: 操作结果
    """
    cert_manager = get_cert_manager()
    success = cert_manager.auto_install_certificate()
    if success:
        return {"status": "success", "message": "证书已安装到系统信任存储"}
    else:
        raise HTTPException(status_code=500, detail="证书安装失败")


@app.get("/ssl/cert/check", tags=["SSL证书管理"])
async def check_cert():
    """
    检查证书有效性
    :return: 检查结果
    """
    cert_manager = get_cert_manager()
    is_valid, days_remaining, expiry_date = cert_manager.check_cert_validity()

    if is_valid:
        return {
            "status": "success",
            "valid": True,
            "message": f"证书有效，剩余{days_remaining}天",
            "days_remaining": days_remaining,
            "expiry_date": expiry_date,
        }
    else:
        return {
            "status": "warning",
            "valid": False,
            "message": f"证书即将过期或无效，剩余{days_remaining}天",
            "days_remaining": days_remaining,
            "expiry_date": expiry_date,
        }


@app.post("/ssl/cert/cleanup", tags=["SSL证书管理"])
async def cleanup_certs(keep_backups: int = 3):
    """
    清理旧的证书备份
    :param keep_backups: 保留的备份数量
    :return: 操作结果
    """
    cert_manager = get_cert_manager()
    success = cert_manager.cleanup_old_certs(keep_backups)
    if success:
        return {
            "status": "success",
            "message": f"已清理旧证书备份（保留{keep_backups}个）",
        }
    else:
        raise HTTPException(status_code=500, detail="清理失败")


@app.get("/health", tags=["系统"])
async def health_check():
    """
    健康检查
    :return: 健康状态
    """
    cert_manager = get_cert_manager()
    config_manager = get_config_manager()

    cert_info = cert_manager.get_cert_info()
    config_status = config_manager.get_status()

    health_status = {
        "status": "healthy",
        "timestamp": Config.get("CURRENT_TIME", ""),
        "services": {
            "config_manager": {
                "status": "running",
                "auto_reload": config_status["auto_reload_running"],
            },
            "ssl_cert_manager": {
                "status": "active",
                "cert_valid": cert_info["is_valid"],
            },
        },
        "cert_info": {
            "valid": cert_info["is_valid"],
            "days_remaining": cert_info["days_remaining"],
        },
    }

    # 如果证书即将过期，健康状态为警告
    if cert_info["days_remaining"] is not None and cert_info["days_remaining"] < 7:
        health_status["status"] = "warning"
        health_status["message"] = "证书即将过期"

    return health_status


def start_web_api(host: str = "0.0.0.0", port: int = 8000):
    """
    启动Web API服务
    :param host: 监听地址
    :param port: 监听端口
    """
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    # 添加时间到配置
    from datetime import datetime

    Config.CURRENT_TIME = datetime.now().isoformat()

    print("启动流量录制配置管理API...")
    print(f"访问地址: http://localhost:8000")
    print(f"API文档: http://localhost:8000/docs")
    print(f"健康检查: http://localhost:8000/health")

    start_web_api()
