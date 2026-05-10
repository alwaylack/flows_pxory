#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""==================================================================
简要描述: logger.py
编写作者: dongruihua
创建日期: 2025/1/16
修订说明:
==================================================================="""

import logbook
from logbook.more import ColorizedStderrHandler
from config import Config


class Log(object):
    def __init__(self, name="mitmproxy", filename=Config.LOG_NAME):
        """
        初始化日志类
        :param name: 模块名称
        :param filename: 文件名称
        """
        self._logger = logbook.Logger(name, level=Config.LOG_LEVEL)
        self._logger.handlers = []
        logbook.set_datetime_format('local')
        log_format = ('{record.time:%Y-%m-%d %H:%M:%S.%f} {record.level_name} {record.filename}[line:{record.lineno}] {'
                      'record.channel}: {record.message}')
        if Config.FILE_HANDLER_ENABLED:
            log_file = logbook.FileHandler(filename, mode="a+", encoding="utf-8", format_string=log_format)
            self._logger.handlers.append(log_file)
        if Config.STREAM_HANDLER_ENABLED:
            log_std = ColorizedStderrHandler(bubble=True, encodings="utf-8", format_string=log_format)
            self._logger.handlers.append(log_std)

    def info(self, *args, **kwargs):
        return self._logger.info(*args, **kwargs)

    def error(self, *args, **kwargs):
        return self._logger.error(*args, **kwargs)

    def debug(self, *args, **kwargs):
        return self._logger.debug(*args, **kwargs)

    def warning(self, *args, **kwargs):
        return self._logger.warning(*args, **kwargs)

    def exception(self, *args, **kwargs):
        return self._logger.exception(*args, **kwargs)

    def critical(self, *args, **kwargs):
        return self._logger.critical(*args, **kwargs)
