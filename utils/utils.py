#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""==================================================================
简要描述: utils.py
编写作者: dongruihua
创建日期: 2025/1/16
修订说明:
==================================================================="""
import functools
import time

from utils.logger import Log


def generate_name_current_time():
    current_time = time.strftime("%Y-%m-%d_%H", time.localtime())
    return current_time


def write_msg_into_log(path, msg):
    try:
        with open(path, 'a+', encoding='utf-8') as f:
            f.write(str(msg) + "\n")
    except IOError as e:
        Log("utils").error(
            f"Failed to write message into log file {path}. Error: {e}")


def record_exception(func):
    functools.wraps(func)

    def wrapper(*args, **kwargs):
        cls = args[0]  # 这里的args[0]就是调用该装饰器的类的实例
        try:
            return func(*args, **kwargs)
        except Exception as e:
            function_name = func.__name__
            import traceback
            err = traceback.format_exc()
            cls.logger.error(f"{function_name}:{err}")

            raise Exception(str(e))

    return wrapper
