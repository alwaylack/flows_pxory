#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""==================================================================
Copyright(c) 2025 Hangzhou Hikvision Digital Technology Co.,Ltd
简要描述: Elastic.py
编写作者: dongruihua
创建日期: 2025/1/9
修订说明:
使用ElasticSearch存储mitmproxy的请求数据
==================================================================="""
import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from threading import Lock
from elasticsearch import Elasticsearch, NotFoundError, exceptions, ElasticsearchException

from utils.logger import Log

logger = Log("Elastic")


class Elastic(object):

    def __init__(self):
        self.es = None
        self.lock = Lock()
        self._connect_to_elasticsearch()

    def _connect_to_elasticsearch(self):
        hosts = [os.getenv("ES_HOSTS")]
        http_auth = (os.getenv("ES_USERNAME"), os.getenv("ES_PASSWORD"))
        max_retries = int(os.getenv("ES_MAX_RETRIES"))
        retry_delay = int(os.getenv("ES_RETRY_DELAY"))
        for attempt in range(max_retries):
            try:
                self.es = Elasticsearch(hosts=hosts,
                                        http_auth=http_auth,
                                        max_retries=max_retries,
                                        retry_on_timeout=True,
                                        timeout=30)
                if self.es.ping():
                    logger.info("成功连接到 Elasticsearch")
                    return
                else:
                    raise exceptions.ConnectionError("无法连接到 Elasticsearch")
            except (exceptions.ConnectionError,
                    exceptions.AuthenticationException) as e:
                logger.error(f"连接 Elasticsearch 失败: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"{retry_delay}秒后重试连接 Elasticsearch...")
                    time.sleep(retry_delay)
                else:
                    raise
            except Exception as e:
                logger.error(f"连接 Elasticsearch 未知错误: {e}")
                raise

    def create_index(self, index_name, timestamp):
        """
        创建索引（带时间戳），并将其绑定到别名
        """
        # 生成带时间戳的索引名
        index_name_with_timestamp = f"{index_name}_{timestamp}"

        # 定义索引的映射（类似于表结构）
        mapping = {
            "mappings": {
                "properties": {
                    "record_id": {
                        "type": "keyword"
                    },
                    "url": {
                        "type": "keyword"
                    },
                    "method": {
                        "type": "keyword"
                    },
                    "headers": {
                        "type": "text"
                    },
                    "body": {
                        "type": "text"
                    },
                    "response_code": {
                        "type": "keyword"
                    },
                    "response_body": {
                        "type": "text"
                    },
                    "create_time": {
                        "type": "date",
                        "format": "epoch_millis"
                    }
                }
            }
        }
        with self.lock:
            if not self.index_exists(index_name_with_timestamp):
                self.es.indices.create(index=index_name_with_timestamp,
                                       body=mapping)  # 创建索引
                logger.debug(f"创建索引: {index_name_with_timestamp}")
            else:
                logger.debug(f"索引 {index_name_with_timestamp} 已经存在")

            alias_name = f"{index_name}_alias"
            self.es.indices.update_aliases({
                "actions": [{
                    "add": {
                        "index": index_name_with_timestamp,
                        "alias": alias_name
                    }
                }]
            })
            logger.debug(f"将索引 {index_name_with_timestamp} 绑定到别名 {alias_name}")

    def insert_data(self, index_name, data):
        """
        插入数据到 Elasticsearch
        """
        # 使用别名插入数据
        alias_name = f"{index_name}_alias"
        # 生成带时间戳的索引名
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H")
        index_name_with_timestamp = f"{index_name}_{timestamp}"
        # 检查别名是否存在
        if not self.table_exists(index_name):
            logger.debug(f"别名 {alias_name} 不存在，开始创建索引...")
            self.create_index(index_name, timestamp)
            logger.debug(f"别名 {alias_name} 创建成功")
        try:
            # 插入文档
            # self.es.index(index=alias_name, body=data) # 插入数据到别名
            self.es.index(index=index_name_with_timestamp,
                          body=data)  # 插入数据到索引

            logger.debug(f"插入数据到索引: {index_name_with_timestamp}, 数据: {data}")
            # self.es.indices.refresh(index=alias_name)  # 刷新索引以确保数据立即可用
            self.es.indices.refresh(
                index=index_name_with_timestamp)  # 刷新索引以确保数据立即可用
        except Exception as e:
            logger.error(f"ElasticSearch插入数据失败: {e}", exc_info=True)
            raise

    def table_exists(self, index_name):
        """
        检查索引别名是否存在
        """
        alias_name = f"{index_name}_alias"
        try:
            self.es.indices.get_alias(name=alias_name)
            return True
        except NotFoundError:
            logger.warning(f"别名 {alias_name} 不存在")
            return False
        except ElasticsearchException as e:
            logger.error(f"检查别名是否存在时发生 Elasticsearch 错误: {e}")
            return False
        except Exception as e:
            logger.error(f"检查别名是否存在时发生错误: {e}")
            return False

    def index_exists(self, index_name):
        """
        检查索引是否存在
        :param index_name:
        :return:
        """
        try:
            return self.es.indices.get(index_name)
        except NotFoundError:
            logger.warning(f"索引 {index_name} 不存在")
            return False
        except ElasticsearchException as e:
            logger.error(f"检查索引是否存在时发生 Elasticsearch 错误: {e}")
            return False
        except Exception as e:
            logger.error(f"检查索引是否存在时发生错误: {e}")
            return False

    def search_data(self, index_name, query):
        """
        查询数据
        """
        alias_name = f"{index_name}_alias"
        try:
            # 执行查询
            result = self.es.search(index=alias_name, body=query)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"查询数据: 执行SQL: {alias_name}, 查询条件: {self.sanitize_query(query)}"
                )
            return result
        except NotFoundError:
            logger.error(f"查询数据失败: 索引 {alias_name} 不存在")
            return {"error": "Index not found"}
        except ElasticsearchException as e:
            logger.error(f"查询数据失败: ElasticSearch 错误:{e}")
            return {'error': 'Elasticsearch error', 'details': str(e)}
        except Exception as e:
            logger.error(f"查询数据失败:未知错误: {e}")
            return {'error': 'Unknown error', 'details': str(e)}

    @classmethod
    def sanitize_query(cls, query):
        """
        对查询条件进行脱敏处理，防止敏感信息泄露
        """
        # 假设 query 是一个字典，可以根据实际需求调整
        sanitized_query = query.copy() if isinstance(query, dict) else {}

        def recursive_sanitize(data):
            if isinstance(data, dict):
                for key, value in data.items():
                    if key == 'password':
                        data[key] = cls.hash_password(value)
                    else:
                        recursive_sanitize(value)
            elif isinstance(data, list):
                for item in data:
                    recursive_sanitize(item)

        recursive_sanitize(sanitized_query)
        return sanitized_query

    @staticmethod
    def hash_password(password):
        """
        使用SHA-256算法对密码进行哈希处理
        """
        if not isinstance(password, str):
            return password
        return hashlib.sha256(password.encode()).hexdigest()

    def close(self):
        """
        关闭 Elasticsearch 连接
        """
        try:
            if self.es:
                self.es.close()
                logger.info("成功关闭 Elasticsearch 连接")
        except ConnectionError as e:
            logger.error(f"关闭 Elasticsearch 连接失败:连 接错误 {e}")
        except TimeoutError as e:
            logger.error(f"关闭 Elasticsearch 连接失败: 超时错误 {e}")
        except Exception as e:
            logger.error(f"关闭 Elasticsearch 连接失败: 未知错误{e}")
