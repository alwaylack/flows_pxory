#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""==================================================================
简要描述: flowproxy.py
编写作者: dongruihua
创建日期: 2025/1/13
修订说明:使用mitmproxy进行流量录制，并记录请求和响应数据，并写入数据库和es中。
         支持动态配置热重载和SSL证书自动管理

【使用说明】：
1.安装依赖包: pip install -r requirements.txt
2.修改配置文件: 在config/filter_conf.py中配置需要抓包的hosts和apis
3.修改环境变量: 在.env文件中配置数据库连接信息和es连接信息,以及是否启用数据库和es写入
4.运行脚本:mitmproxy -s flowproxy.py
5.查看结果: 数据库表records_*, es索引mitmproxy_records_*

【证书安装】
需要在C:\\Users\\{用户名}\\.mitmproxy目录下双击cer文件，安装证书，选择本地计算机，选择"受信任的根证书颁发机构"，然后点击确定即可。
==================================================================="""

import json
import os
import re
import time
import uuid
import signal
import threading
from datetime import datetime, timezone
from difflib import SequenceMatcher

from dotenv import load_dotenv
from mitmproxy import http

from config_manager import get_config_manager
from ssl_cert_manager import get_cert_manager, ensure_certificate
from config import Config
from db.DBUtils import DBUtils
from db.Elastic import Elastic
from db.SQLiteUtils import SQLiteUtils
from utils.logger import Log
from utils.utils import generate_name_current_time, write_msg_into_log

load_dotenv()  # 加载环境变量

mitm_log = Log("flowproxy")


class RecordHandler(object):
    """
    流量记录处理器
    支持动态配置热重载和SSL证书自动管理
    """

    def __init__(self):
        self.record_id = str(uuid.uuid1())  # 初始化记录id
        mitm_log.info(f"记录id: {self.record_id}")
        self.result = []  # 初始化记录结果
        self.id_result_map = {}  # 初始化请求结果映射
        self.count = 1  # 初始化计数器
        self.file_path = os.path.join(
            Config.PATH, "logs", f"records_{generate_name_current_time()}.txt"
        )  # 初始化日志路径

        # 初始化数据库处理器
        self.db_handler = None
        self.es_handler = None
        self.sqlite_handler = None

        # 初始化配置管理器
        self.config_manager = get_config_manager()
        self._init_database_handlers()

        # 设置配置重载回调
        self.config_manager.register_reload_callback(self._on_config_reload)

        # 启动配置自动重载监控
        if Config.get("AUTO_CONFIG_RELOAD", True):
            self.config_manager.start_auto_reload(
                interval=Config.get("CONFIG_CHECK_INTERVAL", 2)
            )
            mitm_log.info("已启动配置自动重载监控")

        # 确保证书状态
        self._ensure_certificate()

        write_msg_into_log(
            self.file_path, f"mitmproxy记录开始;记录id:{self.record_id}"
        )  # 写入log

    def _init_database_handlers(self):
        """初始化数据库处理器"""
        try:
            if Config.SQLITE_ENABLED:
                self.sqlite_handler = SQLiteUtils()
                mitm_log.debug("SQLite数据库处理器已初始化")
            else:
                mitm_log.debug("SQLite数据库写入未启用")
        except Exception as e:
            mitm_log.error(f"SQLite数据库处理器初始化失败: {e}")

        try:
            if Config.SQL_ENABLED:
                self.db_handler = DBUtils()
                mitm_log.debug("MySQL数据库处理器已初始化")
            else:
                mitm_log.debug("MySQL数据库写入未启用")
        except Exception as e:
            mitm_log.error(f"MySQL数据库处理器初始化失败: {e}")

        try:
            if Config.ES_ENABLED:
                self.es_handler = Elastic()
                mitm_log.debug("Elasticsearch处理器已初始化")
            else:
                mitm_log.debug("ES数据库写入未启用")
        except Exception as e:
            mitm_log.error(f"Elasticsearch处理器初始化失败: {e}")

    def _ensure_certificate(self):
        """确保证书状态"""
        try:
            if Config.get("SSL_CERT_AUTO_MANAGE", True):
                mitm_log.info("正在确保证书状态...")
                if ensure_certificate():
                    mitm_log.info("证书状态确认成功")
                else:
                    mitm_log.warning("证书状态确认失败")
            else:
                mitm_log.info("SSL证书自动管理已禁用")
        except Exception as e:
            mitm_log.error(f"确保证书状态时发生错误: {e}")

    def _on_config_reload(self):
        """
        配置重载回调函数
        重新初始化数据库处理器和相关配置
        """
        mitm_log.info("配置已重载，正在重新初始化数据库处理器...")

        # 创建新的数据库处理器
        new_sqlite = SQLiteUtils() if Config.SQLITE_ENABLED else None
        new_mysql = DBUtils() if Config.SQL_ENABLED else None
        new_es = Elastic() if Config.ES_ENABLED else None

        # 原子替换处理器
        old_sqlite = self.sqlite_handler
        old_mysql = self.db_handler
        old_es = self.es_handler

        self.sqlite_handler = new_sqlite
        self.db_handler = new_mysql
        self.es_handler = new_es

        # 异步关闭旧的数据库连接（不阻塞新请求）
        def close_old():
            try:
                if old_sqlite:
                    old_sqlite.close()
            except Exception as e:
                mitm_log.error(f"关闭旧SQLite处理器失败: {e}")
            try:
                if old_mysql:
                    old_mysql.close()
            except Exception as e:
                mitm_log.error(f"关闭旧MySQL处理器失败: {e}")
            try:
                if old_es:
                    old_es.close()
            except Exception as e:
                mitm_log.error(f"关闭旧ES处理器失败: {e}")

        import threading

        threading.Thread(target=close_old, daemon=True).start()

        # 重新确保证书状态
        self._ensure_certificate()

        mitm_log.info("配置重载完成")

    @classmethod
    def calculate_similarity(cls, uri):
        """
        计算APIS中的api与uri的相似度
        :param uri: 请求的uri
        :return:
        """
        for api in Config.APIS:
            match = SequenceMatcher(None, uri, api).ratio()
            if match > 0.6:
                mitm_log.debug(f"匹配成功: {api}: {match}")
                return True
        return False

    @classmethod
    def filter_flow(cls, flow: http.HTTPFlow):
        """
        过滤流量
        :param flow: 流量对象
        :return:
        """
        if flow.request.path.endswith(
            (
                ".ico",
                ".css",
                ".js",
                ".png",
                "jpg",
                "gif",
                "svg",
                "ttf",
                "woff",
                "woff2",
                "eot",
                "otf",
            )
        ):
            return False
        if flow.request.pretty_host not in Config.HOST:
            return False
        if ("hpp" or "hcc" or "ccf") not in flow.request.url:
            return False
        if Config.APIS and not cls.calculate_similarity(flow.request.path):
            return False
        return True

    def request(self, flow: http.HTTPFlow):
        """
        处理请求
        :param flow: 流量对象
        :return:
        """
        if not self.filter_flow(flow):
            return

        request_id = flow.id  # 请求id
        request = flow.request

        # 限制请求体大小，防止内存溢出 (最大10MB)
        body_text = request.get_text()
        if len(body_text) > 10 * 1024 * 1024:
            body_text = body_text[: 10 * 1024 * 1024] + "...[内容过长已截断]"

        self.result = [
            self.record_id,
            request.path,
            request.method,
            request.headers.get("Content-Type", "application/json;charset=UTF-8"),
            body_text,
        ]
        self.id_result_map[request_id] = self.result

    def response(self, flow: http.HTTPFlow):
        """
        处理响应
        :param flow: 流量对象
        :return:
        """
        if not self.filter_flow(flow):
            return

        response_id = flow.id
        response = flow.response

        self.result = self.id_result_map.get(response_id)
        if not self.result:
            return

        if flow.request.path != self.result[1]:
            return

        # 限制响应体大小，防止内存溢出 (最大10MB)
        response_text = response.get_text()
        if len(response_text) > 10 * 1024 * 1024:
            response_text = response_text[: 10 * 1024 * 1024] + "...[内容过长已截断]"

        self.result.extend([response.status_code, response_text])

        log_data = {
            str(self.count): {
                "uri": self.result[1],
                "method": self.result[2],
                "headers": self.result[3],
                "body": self.result[4],
                "response_status": self.result[5],
                "response_text": self.result[6],
            }
        }

        # 写入文件
        write_msg_into_log(
            self.file_path, f"{json.dumps(log_data, indent=4, ensure_ascii=False)}"
        )

        # 替换文件中的自动生产的id信息 (支持大小写字母数字)
        if re.findall(r"/[0-9a-zA-Z]{30,}", self.result[1]):
            self.result[1] = re.sub(r"/[0-9a-zA-Z]{30,}", "/*", self.result[1])

        # 写入SQLite数据库
        if Config.SQLITE_ENABLED:
            try:
                if self.sqlite_handler:
                    self.sqlite_handler.insert_data("mitmproxy_records", self.result)
                else:
                    # 如果处理器为空，重新初始化
                    self.sqlite_handler = SQLiteUtils()
                    self.sqlite_handler.insert_data("mitmproxy_records", self.result)
            except Exception as e:
                mitm_log.error(f"SQLite数据库写入失败: {e}")

        # 写入MYSQL数据库
        if Config.SQL_ENABLED:
            try:
                if self.db_handler:
                    self.db_handler.insert_data(
                        "records_%s" % time.strftime("%Y%m%d", time.localtime()),
                        self.result,
                    )
                else:
                    # 如果处理器为空，重新初始化
                    self.db_handler = DBUtils()
                    self.db_handler.insert_data(
                        "records_%s" % time.strftime("%Y%m%d", time.localtime()),
                        self.result,
                    )
            except Exception as e:
                mitm_log.error(f"MySQL数据库写入失败: {e}")

        # 写入ElasticSearch
        if Config.ES_ENABLED:
            data = {
                "record_id": self.result[0],
                "url": self.result[1],
                "method": self.result[2],
                "headers": self.result[3],
                "body": self.result[4],
                "response_status": self.result[5],
                "response_text": self.result[6],
                "created_time": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
            index_name = "mitmproxy_records"
            try:
                if self.es_handler:
                    self.es_handler.insert_data(index_name, data)
                else:
                    # 如果处理器为空，重新初始化
                    self.es_handler = Elastic()
                    self.es_handler.insert_data(index_name, data)
            except Exception as e:
                mitm_log.error(f"ES数据库写入失败: {e}")

        self.count += 1

    def __del__(self):
        """析构函数，清理资源"""
        try:
            if Config.SQL_ENABLED and self.db_handler:
                self.db_handler.close()
        except Exception:
            pass

        try:
            if Config.ES_ENABLED and self.es_handler:
                self.es_handler.close()
        except Exception:
            pass

        try:
            if Config.SQLITE_ENABLED and self.sqlite_handler:
                self.sqlite_handler.close()
        except Exception:
            pass

        try:
            if self.config_manager:
                self.config_manager.stop_auto_reload()
        except Exception:
            pass

        try:
            write_msg_into_log(self.file_path, "mitmproxy记录结束")
        except Exception:
            pass


addons = [RecordHandler()]
