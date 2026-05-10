
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""==================================================================
Copyright(c) 2025 Hangzhou Hikvision Digital Technology Co.,Ltd
简要描述: config_manager.py - 动态配置管理器
编写作者: dongruihua
创建日期: 2025/1/20
修订说明: 支持动态加载配置文件，当config.py发生变化时自动重新加载
         无需重启mitmproxy即可使配置变更生效
==================================================================="""
import os
import sys
import time
import hashlib
import importlib
import threading
from datetime import datetime
from typing import Dict, Any, Optional

from utils.logger import Log

logger = Log('ConfigManager')


class ConfigManager:
    """
    动态配置管理器
    支持热重载配置文件，自动检测配置变更
    """

    def __init__(self, config_module_path: str = 'config'):
        """
        初始化配置管理器
        :param config_module_path: 配置模块路径，例如 'config' 或 'config.config'
        """
        self.config_module_path = config_module_path
        self.config_module = None
        self.config_file_path = None
        self._last_hash = None
        self._last_check_time = None
        self._lock = threading.Lock()
        self._reload_callbacks = []
        self._check_interval = 2  # 检查间隔(秒)
        self._auto_reload_enabled = True
        self._monitor_thread = None
        self._running = False

        self._init_config()

    def _init_config(self):
        """初始化配置模块"""
        try:
            # 尝试导入配置模块
            self.config_module = importlib.import_module(self.config_module_path)
            # 获取配置文件的实际路径
            self.config_file_path = self._get_config_file_path()
            self._last_hash = self._calculate_file_hash()
            self._last_check_time = time.time()
            logger.info(f"配置模块加载成功: {self.config_file_path}")
        except Exception as e:
            logger.error(f"配置模块加载失败: {e}")
            raise

    def _get_config_file_path(self) -> str:
        """
        获取配置文件的实际路径
        :return: 配置文件路径
        """
        if hasattr(self.config_module, '__file__'):
            return self.config_module.__file__
        # 如果没有__file__属性，尝试从模块路径构建
        module_parts = self.config_module_path.split('.')
        base_path = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(base_path, *module_parts) + '.py'
        return config_file

    def _calculate_file_hash(self) -> Optional[str]:
        """
        计算配置文件的MD5哈希值
        :return: 文件哈希值，如果文件不存在则返回None
        """
        try:
            if not os.path.exists(self.config_file_path):
                logger.warning(f"配置文件不存在: {self.config_file_path}")
                return None
            with open(self.config_file_path, 'rb') as f:
                file_content = f.read()
                return hashlib.md5(file_content).hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希失败: {e}")
            return None

    def _reload_config(self) -> bool:
        """
        重新加载配置模块
        :return: 是否重新加载成功
        """
        try:
            with self._lock:
                # 重新计算文件哈希
                current_hash = self._calculate_file_hash()
                if current_hash is None:
                    return False

                # 如果哈希值没有变化，不重新加载
                if current_hash == self._last_hash:
                    return False

                logger.info(f"检测到配置文件变更，正在重新加载...")
                logger.info(f"旧哈希: {self._last_hash}")
                logger.info(f"新哈希: {current_hash}")

                # 重新导入配置模块
                importlib.reload(self.config_module)
                self._last_hash = current_hash
                self._last_check_time = time.time()

                logger.info("配置文件重新加载成功")

                # 触发重载回调
                self._trigger_reload_callbacks()
                return True
        except Exception as e:
            logger.error(f"重新加载配置失败: {e}")
            return False

    def _trigger_reload_callbacks(self):
        """触发所有重载回调函数"""
        for callback in self._reload_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"执行重载回调失败: {e}")

    def register_reload_callback(self, callback):
        """
        注册配置重载回调函数
        :param callback: 回调函数
        """
        if callback not in self._reload_callbacks:
            self._reload_callbacks.append(callback)
            logger.debug(f"注册重载回调: {callback.__name__ if hasattr(callback, '__name__') else callback}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项的值
        :param key: 配置项键名
        :param default: 默认值
        :return: 配置项的值
        """
        try:
            if hasattr(self.config_module, key):
                return getattr(self.config_module, key)
            return default
        except Exception as e:
            logger.error(f"获取配置项失败: key={key}, error={e}")
            return default

    def set(self, key: str, value: Any) -> bool:
        """
        设置配置项的值（仅内存中，不持久化）
        :param key: 配置项键名
        :param value: 配置项值
        :return: 是否设置成功
        """
        try:
            setattr(self.config_module, key, value)
            logger.info(f"配置项已更新: {key} = {value}")
            return True
        except Exception as e:
            logger.error(f"设置配置项失败: key={key}, error={e}")
            return False

    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置项
        :return: 配置项字典
        """
        config_dict = {}
        try:
            for key in dir(self.config_module):
                if not key.startswith('_'):
                    config_dict[key] = getattr(self.config_module, key)
        except Exception as e:
            logger.error(f"获取所有配置项失败: {e}")
        return config_dict

    def check_and_reload(self) -> bool:
        """
        检查配置文件是否有变更，如果有则重新加载
        :return: 是否重新加载
        """
        try:
            current_hash = self._calculate_file_hash()
            if current_hash is not None and current_hash != self._last_hash:
                return self._reload_config()
            return False
        except Exception as e:
            logger.error(f"检查配置文件失败: {e}")
            return False

    def start_auto_reload(self, interval: int = 2):
        """
        启动自动重载监控线程
        :param interval: 检查间隔(秒)
        """
        if self._running:
            logger.warning("自动重载监控已在运行")
            return

        self._check_interval = interval
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info(f"已启动自动重载监控，检查间隔: {interval}秒")

    def stop_auto_reload(self):
        """停止自动重载监控"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("已停止自动重载监控")

    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                time.sleep(self._check_interval)
                self.check_and_reload()
            except Exception as e:
                logger.error(f"监控循环发生错误: {e}")

    def is_auto_reload_running(self) -> bool:
        """检查自动重载监控是否正在运行"""
        return self._running

    def get_status(self) -> Dict[str, Any]:
        """
        获取配置管理器状态
        :return: 状态字典
        """
        return {
            'config_file': self.config_file_path,
            'file_exists': os.path.exists(self.config_file_path),
            'last_hash': self._last_hash,
            'last_check_time': datetime.fromtimestamp(self._last_check_time).isoformat() if self._last_check_time else None,
            'auto_reload_enabled': self._auto_reload_enabled,
            'auto_reload_running': self._running,
            'check_interval': self._check_interval,
            'callback_count': len(self._reload_callbacks),
            'config_items': len(self.get_all())
        }


# 全局配置管理器实例
_config_manager = None


def get_config_manager() -> ConfigManager:
    """
    获取全局配置管理器实例
    :return: ConfigManager实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def reload_config() -> bool:
    """
    手动触发配置重载
    :return: 是否重载成功
    """
    manager = get_config_manager()
    return manager._reload_config()
