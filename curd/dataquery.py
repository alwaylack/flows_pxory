#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""==================================================================
简要描述: dataquery.py
编写作者: dongruihua
创建日期: 2025/1/16
修订说明:
==================================================================="""
from db.SQLiteUtils import SQLiteUtils
from config import Config
from utils.logger import Log
from utils.utils import record_exception


class DataQuery(object):
    logger = Log('DataQuery')

    @classmethod
    @record_exception
    def get_all_data(cls, table_name=Config.TABLE_NAME):
        """
        获取数据库中的所有数据
        :param table_name:  数据库表名称
        :return: 
        """
        db_handler = SQLiteUtils()
        sql = f"SELECT * FROM {table_name} ORDER BY create_time DESC"
        result = db_handler.query_data(sql)
        db_handler.close()
        return result

    @classmethod
    @record_exception
    def get_data_by_id(cls, record_id, table_name=Config.TABLE_NAME):
        """
        根据id获取数据库中的数据
        :param record_id:   记录id
        :param table_name:  数据库表名称
        :return: 
        """
        db_handler = SQLiteUtils()
        sql = f"SELECT * FROM {table_name} WHERE id={record_id} order by create_time DESC"
        result = db_handler.query_data(sql)
        db_handler.close()
        return result
