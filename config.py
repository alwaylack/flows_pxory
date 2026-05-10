#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""==================================================================
简要描述: config.py
编写作者: dongruihua
创建日期: 2025/1/16
修订说明:配置文件
==================================================================="""
import os


class Config(object):
    """配置文件"""

    # --------------过滤配置------------------------------------
    # Host设置
    HOST = ["isgp.hik-partner.com"] # 需要抓取的域名列表
    APIS = [] # 需要抓取的API列表

    # ---------------日志相关配置----------------------------
    # 日志和数据存储上级目录路径
    PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    # 日志路径
    LOG_PATH = os.path.join(PATH, "logs")
    if not os.path.exists(LOG_PATH):
        os.makedirs(LOG_PATH)
    LOG_NAME = os.path.join(LOG_PATH, "mitmproxy_records.log")
    # filehandler设置 开关
    FILE_HANDLER_ENABLED = True

    # StreamHandler设置 开关
    STREAM_HANDLER_ENABLED = False

    # 日志级别
    # """
    # CRITICAL = 15
    # ERROR = 14
    # WARNING = 13
    # INFO = 11
    # DEBUG = 10
    # """
    LOG_LEVEL = 11  # 日志级别

    # --------------数据库相关配置-------------------
    # 数据存储路径
    DATA_PATH = os.path.join(PATH, "data")
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
    DATA_NAME = os.path.join(DATA_PATH, "mitmproxy_records.db")

    TABLE_NAME = "mitmproxy_records"

    # 数据库启用开关
    SQLITE_ENABLED = True  # 启用sqlite数据库
    ES_ENABLED = False  # 启用ES数据库
    SQL_ENABLED = False  # 启用SQL数据库

    # 动态配置管理
    AUTO_CONFIG_RELOAD = True  # 自动重载配置
    CONFIG_CHECK_INTERVAL = 2  # 配置检查间隔(秒)

    # SSL证书管理
    SSL_CERT_AUTO_MANAGE = True  # 自动管理SSL证书
    SSL_CERT_CHECK_INTERVAL = 3600  # 证书检查间隔(秒)
    SSL_CERT_EXPIRY_THRESHOLD = 30  # 证书过期阈值(天)
