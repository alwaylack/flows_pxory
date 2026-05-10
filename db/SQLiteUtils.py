#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""==================================================================
Copyright(c) 2025 Hangzhou Hikvision Digital Technology Co.,Ltd
简要描述: SQLiteUtils.py
编写作者: dongruihua
创建日期: 2025/1/14
修订说明: 使用SQLite类来操作数据库，存放数据到本地db文件中
==================================================================="""

import os
import sqlite3

from utils.logger import Log
from config import Config

# logger = MyLogger("sqlite").get_logger()
# db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mitmproxy_records.db")

db_path = Config.DATA_PATH

logger = Log('SQLiteUtils')


class SQLiteUtils:

    def __init__(self):
        self.db_path = Config.DATA_NAME
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_table_if_not_exists()

    def _connect(self):
        try:

            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            logger.debug(f"连接SQLite数据库成功: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"连接SQLite数据库失败: {self.db_path}")
            logger.error(f"连接SQLite数据库失败: {e}")

    def _create_table_if_not_exists(self):
        table_name = Config.TABLE_NAME
        sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id TEXT not null, 
                    url TEXT not null,
                    method TEXT not null, 
                    headers TEXT not null, 
                    body text comment, 
                    response_code TEXT not null, 
                    response_body text,
                    create_time datetime default current_timestamp
                )
                """
        try:
            self.cursor.execute(sql)
            logger.debug(sql)
            logger.debug("SQLite创建表成功或确认表已存在")
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"SQLite创建表失败: {e}")
            self.conn.rollback()
        except Exception as e:
            logger.error(f"SQLite创建表时发生未知错误: {e}")
            self.conn.rollback()
            raise

    def insert_data(self, table_name, data):
        # 使用列表推导式创建占位符，避免不必要的计算
        placeholder = ','.join(['?'] * len(data))
        insert_sql = (
            f"INSERT INTO {table_name} (record_id, url, method, headers, body, response_code, response_body) "
            f"VALUES ({placeholder})")
        try:
            self.cursor.execute(insert_sql, data)
            logger.debug(f"SQLite执行SQL: {insert_sql}, 数据: {data}")
            self.conn.commit()
        except sqlite3.IntegrityError as e:
            logger.error(f"SQLite插入数据失败: {e}", exc_info=True)
            self.conn.rollback()
        except Exception as e:
            logger.error(f"SQLite插入数据时发生未知错误: {e}")
            self.conn.rollback()

    # finally:
    #     if self.cursor and self.conn:
    #         self.cursor.close()
    #         self.conn.close()

    def query_data(self, sql):
        try:
            self.cursor.execute(sql)
            result = self.cursor.fetchall()
            logger.debug(f"SQLite执行SQL: {sql}, 结果: {result}")
            return result
        except sqlite3.Error as e:
            logger.error(f"SQLite查询数据失败: {e}")
            return None
        except Exception as e:
            logger.error(f"SQLite查询数据时发生未知错误: {e}")
            return None

    def close(self):
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
            logger.debug("SQLite数据库连接已关闭")
        except sqlite3.Error as e:
            logger.error(f"关闭SQLite数据库连接失败: {e}")
        except Exception as e:
            logger.error(f"关闭SQLite数据库连接时发生未知错误: {e}")
