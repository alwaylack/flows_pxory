#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""==================================================================
Copyright(c) 2024 Hangzhou Hikvision Digital Technology Co.,Ltd
简要描述: DBUtils.py
编写作者: dongruihua
创建日期: 2024/03/27
修订说明:
使用MySQL数据库存储mitmproxy的请求数据
=================================================================="""
import os

import pymysql

from utils.logger import Log

logger = Log("DBUtils")


class DBUtils(object):

    def __init__(self):
        self.conn = None
        self.cursor = None
        self._connect()

    def _connect(self):
        try:
            self.conn = pymysql.connect(host=os.getenv("SQL_HOSTS"),
                                        port=int(os.getenv("SQL_PORT")),
                                        user=os.getenv("SQL_USERNAME"),
                                        password=os.getenv("SQL_PASSWORD"),
                                        database=os.getenv("SQL_DATABASE"))
            self.cursor = self.conn.cursor()
        except pymysql.MySQLError as e:
            logger.error(f"MySQL数据库连接失败: {e}")
            raise
        except Exception as e:
            logger.error(f"连接MySQL数据库时发生未知错误: {e}")
            raise

    def create_table(self, table_name):
        sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id int AUTO_INCREMENT PRIMARY KEY,
            record_id varchar(100) not null comment '请求记录ID', 
            url varchar(100) not null comment '请求URL',
            method varchar(10) not null comment '请求方法', 
            headers varchar(100) not null comment '请求头', 
            body text comment '请求体', 
            response_code varchar(10) not null comment '响应状态码', 
            response_body text comment '响应体',
            create_time datetime default current_timestamp comment '数据插入时间'
        )
        """
        try:
            self.cursor.execute(sql)
            logger.debug(sql)
            self.conn.commit()
        except pymysql.MySQLError as e:
            logger.error(f"MySQL创建表失败: {e}")
            self.conn.rollback()
        except Exception as e:
            logger.error(f"MySQL创建表时发生未知错误: {e}")
            if self.conn:
                self.conn.rollback()

    def insert_data(self, table_name, data):
        # 创建表的操作应放在插入数据之前，但不需要每次插入数据时都创建表
        if not self._table_exists(table_name):
            self.create_table(table_name)

        # 使用列表推导式创建占位符，避免不必要的计算
        placeholder = ','.join(['%s'] * len(data))
        insert_sql = (
            f"INSERT INTO {table_name} (record_id, url, method, headers, body, response_code, response_body) "
            f"VALUES "
            f"({placeholder})")
        try:
            self.cursor.execute(insert_sql, data)
            logger.debug(f"MySQL执行SQL: {insert_sql}, 数据: {data}")
            self.conn.commit()
        except pymysql.err.IntegrityError as e:
            logger.error(f"MySQL插入数据失败: {e}", exc_info=True)
            self.conn.rollback()
        except Exception as e:
            logger.error(f"MySQL插入数据时发生未知错误: {e}")
            if self.conn:
                self.conn.rollback()
        # finally:
        #     if self.cursor and self.conn:
        #         self.cursor.close()
        #         self.conn.close()

    def _table_exists(self, table_name):
        check_sql = f"SHOW TABLES LIKE '{table_name}'"
        try:
            self.cursor.execute(check_sql)
            result = self.cursor.fetchone()
            return result is not None
        except pymysql.MySQLError as e:
            logger.error(f"MySQL检查表是否存在时发生错误: {e}")
            return False

    def close(self):
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
        except pymysql.MySQLError as e:
            logger.error(f"关闭MySQL数据库连接失败: {e}")
        except Exception as e:
            logger.error(f"关闭MySQL数据库连接时发生未知错误: {e}")
