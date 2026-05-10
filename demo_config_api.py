
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""==================================================================
Copyright(c) 2025 Hangzhou Hikvision Digital Technology Co.,Ltd
简要描述: demo_config_api.py - 配置API演示脚本
编写作者: dongruihua
创建日期: 2025/1/20
修订说明: 演示如何使用配置管理API
==================================================================="""
import requests
import json
import time

BASE_URL = "http://localhost:8000"


def demo_config_management():
    """演示配置管理功能"""
    print("=" * 60)
    print("配置管理API演示")
    print("=" * 60)

    # 1. 获取所有配置
    print("\n1. 获取所有配置:")
    response = requests.get(f"{BASE_URL}/config")
    if response.status_code == 200:
        config = response.json()
        print(json.dumps(config, indent=2, ensure_ascii=False))
    else:
        print(f"获取配置失败: {response.status_code}")

    # 2. 获取特定配置项
    print("\n2. 获取LOG_LEVEL配置:")
    response = requests.get(f"{BASE_URL}/config/LOG_LEVEL")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"获取配置项失败: {response.status_code}")

    # 3. 更新配置项
    print("\n3. 更新LOG_LEVEL配置 (11 -> 10):")
    update_data = {
        "key": "LOG_LEVEL",
        "value": 10
    }
    response = requests.post(f"{BASE_URL}/config", json=update_data)
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"更新配置失败: {response.status_code}")

    # 4. 批量更新配置
    print("\n4. 批量更新配置:")
    batch_data = {
        "updates": {
            "LOG_LEVEL": 11,
            "AUTO_CONFIG_RELOAD": True
        }
    }
    response = requests.put(f"{BASE_URL}/config/batch", json=batch_data)
    if response.status_code in [200, 207]:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"批量更新失败: {response.status_code}")

    # 5. 重载配置
    print("\n5. 重载配置:")
    response = requests.post(f"{BASE_URL}/config/reload")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"配置重载失败: {response.status_code}")

    # 6. 获取配置状态
    print("\n6. 获取配置状态:")
    response = requests.get(f"{BASE_URL}/config/status")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"获取状态失败: {response.status_code}")


def demo_ssl_cert_management():
    """演示SSL证书管理功能"""
    print("\n" + "=" * 60)
    print("SSL证书管理API演示")
    print("=" * 60)

    # 1. 获取证书信息
    print("\n1. 获取证书信息:")
    response = requests.get(f"{BASE_URL}/ssl/cert")
    if response.status_code == 200:
        cert_info = response.json()
        print(json.dumps(cert_info, indent=2, ensure_ascii=False))
    else:
        print(f"获取证书信息失败: {response.status_code}")

    # 2. 检查证书有效性
    print("\n2. 检查证书有效性:")
    response = requests.get(f"{BASE_URL}/ssl/cert/check")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"证书检查失败: {response.status_code}")

    # 3. 确保证书
    print("\n3. 确保证书状态:")
    response = requests.post(f"{BASE_URL}/ssl/cert/ensure")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"证书确认失败: {response.status_code}")

    # 4. 健康检查
    print("\n4. 系统健康检查:")
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"健康检查失败: {response.status_code}")


if __name__ == "__main__":
    print("演示配置管理和SSL证书管理API")
    print("请确保web_api.py服务正在运行...")
    print("等待5秒确保服务启动...")
    time.sleep(5)

    try:
        demo_config_management()
        demo_ssl_cert_management()
        print("\n" + "=" * 60)
        print("演示完成")
        print("=" * 60)
    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到API服务")
        print("请确保web_api.py服务已启动")
        print("运行: python web_api.py")
