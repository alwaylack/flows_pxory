
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

本项目是一个基于 mitmproxy 的 HTTP/HTTPS 流量录制工具，能够捕获网络请求和响应数据，并存储到 SQLite/MySQL/Elasticsearch 数据库中，同时提供 Web 界面进行查看。

## 核心架构

### 分层结构

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   mitmproxy     │    │   Web API        │    │   Web UI        │
│   (flowproxy)   │────│   (web_api.py)   │────│   (webdisplay)  │
└────────┬────────┘    └────────┬─────────┘    └─────────────────┘
         │                      │
┌────────▼────────┐    ┌────────▼─────────┐
│  RecordHandler  │    │ ConfigManager    │
│  (flowproxy)    │    │ (config_manager) │
└────────┬────────┘    └────────┬─────────┘
         │                      │
┌────────▼────────┐    ┌────────▼─────────┐
│  Database Layer │    │  SSL Cert Mgr    │
│  (SQLite/MySQL) │    │ (ssl_cert_manager)│
└─────────────────┘    └──────────────────┘
```

### 数据流

1. **流量捕获阶段**：
   - mitmproxy 拦截 HTTP 请求/响应
   - `RecordHandler.filter_flow()` 过滤目标流量
   - `request()` 保存请求数据到 `id_result_map`
   - `response()` 匹配响应，组合完整记录

2. **存储阶段**：
   - 写入日志文件（JSON，行格式）
   - 写入 SQLite（默认启用）
   - 可选：MySQL、Elasticsearch

3. **配置管理**：
   - `ConfigManager` 监控 `config.py` 文件变更
   - 变更时自动重载配置模块
   - 触发回调重新初始化数据库处理器

4. **证书管理**：
   - `SSLCertManager` 检查证书状态
   - 自动生成缺失/过期证书（OpenSSL）
   - 安装到系统信任存储（Windows/macOS/Linux）

## 核心模块说明

### flowproxy.py

**RecordHandler 类** - mitmproxy addon 核心

- `filter_flow(flow)` - 流量过滤逻辑
  - 排除静态资源（ico/css/js/png 等）
  - 域名白名单（Config.HOST）
  - URL 关键词过滤（hpp/hcc/ccf）
  - API 路径模糊匹配（相似度 > 0.6）

- `request(flow)` - 捕获请求
- `response(flow)` - 捕获响应，存储数据
- `_on_config_reload()` - 配置重载回调

**关键配置**：
```python
Config.HOST          # 抓包域名列表
Config.APIS          # 抓包API路径列表
Config.SQLITE_ENABLED  # SQLite开关
Config.SQL_ENABLED     # MySQL开关
Config.ES_ENABLED      # Elasticsearch开关
```

### config_manager.py

**ConfigManager 类** - 动态配置管理器

**主要特性**：
- 文件哈希监控（MD5）
- 自动重载后台线程
- 线程安全的配置访问
- 重载回调机制

**API**：
```python
manager = get_config_manager()
manager.get('KEY')                    # 获取配置
manager.set('KEY', value)              # 设置配置
manager.check_and_reload()             # 检查并重载
manager.start_auto_reload(interval=2)   # 启动自动监控
manager.register_reload_callback(cb)    # 注册回调
```

**配置变更流程**：
1. 检测到 config.py 修改（哈希变化）
2. 调用 `importlib.reload(config_module)`
3. 触发所有注册的回调函数
4. `RecordHandler` 重新初始化数据库连接

### ssl_cert_manager.py

**SSLCertManager 类** - SSL 证书管理器

**证书路径**：
```
~/.mitmproxy/
  ├── mitmproxy-ca.pem      # CA证书
  ├── mitmproxy-ca.crt      # CA证书（CRT格式）
  ├── mitmproxy-ca.key      # 私钥
  ├── mitmproxy-ca.srl      # 序列号
  └── mitmproxy-ca-cert.pem # 信任证书
```

**主要方法**：
```python
cert_mgr = get_cert_manager()
cert_mgr.check_cert_exists()              # 检查证书是否存在
cert_mgr.check_cert_validity()            # 检查有效期
cert_mgr.ensure_certificate()              # 确保证书有效
cert_mgr._generate_ssl_cert()              # 生成证书（OpenSSL）
cert_mgr.auto_install_certificate()        # 安装到系统信任存储
cert_mgr.get_cert_info()                   # 获取证书信息
```

**系统信任存储集成**：
- Windows：`certutil -addstore Root`
- macOS：`security add-trusted-cert`
- Linux：`update-ca-certificates`

### web_api.py

**FastAPI REST API 服务**

**端点概览**：

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/config` | 获取所有配置 |
| GET | `/config/{key}` | 获取配置项 |
| POST | `/config` | 更新配置项 |
| PUT | `/config/batch` | 批量更新 |
| POST | `/config/reload` | 重载配置 |
| GET | `/config/status` | 配置状态 |
| GET | `/ssl/cert` | 证书信息 |
| POST | `/ssl/cert/ensure` | 确保证书 |
| POST | `/ssl/cert/generate` | 生成证书 |
| POST | `/ssl/cert/install` | 安装证书 |
| GET | `/ssl/cert/check` | 检查证书 |
| POST | `/ssl/cert/cleanup` | 清理备份 |
| GET | `/health` | 健康检查 |

**请求模型**：
```python
class ConfigUpdateRequest(BaseModel):
    key: str
    value: Any
```

### db/SQLiteUtils.py

**SQLiteUtils 类** - SQLite 数据库操作

**表结构**：
```sql
CREATE TABLE mitmproxy_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT not null,
    url TEXT not null,
    method TEXT not null,
    headers TEXT not null,
    body text,
    response_code TEXT not null,
    response_body text,
    create_time datetime default current_timestamp
)
```

**API**：
```python
db = SQLiteUtils()
db.insert_data(table_name, data)    # 插入数据
db.query_data(sql)                   # 查询数据
db.close()                           # 关闭连接
```

## 开发工作流程

### 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 确保证书（首次运行）
python ssl_cert_manager.py  # 或通过API
```

### 运行流量捕获

```bash
# 方式1：直接运行
mitmproxy -s flowproxy.py

# 方式2：后台运行
mitmweb -s flowproxy.py
```

**浏览器配置**：
- HTTP代理：127.0.0.1:8080
- HTTPS代理：127.0.0.1:8080
- 安装证书：访问 http://mitm.it 下载并安装

### 运行 Web 界面

```bash
python webdisplay.py
# 访问 http://localhost:8000/record/no/response/all
```

### 运行管理 API

```bash
python web_api.py
# API文档：http://localhost:8000/docs
# 健康检查：http://localhost:8000/health
```

### 演示 API 使用

```bash
python demo_config_api.py
```

## 配置文件说明

### config.py

**核心配置项**：

```python
# 流量过滤
HOST = ["isgp.hik-partner.com"]  # 抓包域名
APIS = []                         # 抓包API路径

# 日志
LOG_LEVEL = 11                    # 日志级别（10=DEBUG, 11=INFO）

# 数据库开关
SQLITE_ENABLED = True
ES_ENABLED = False
SQL_ENABLED = False

# 动态配置
AUTO_CONFIG_RELOAD = True         # 自动重载
CONFIG_CHECK_INTERVAL = 2         # 检查间隔（秒）

# SSL证书
SSL_CERT_AUTO_MANAGE = True       # 自动管理
SSL_CERT_EXPIRY_THRESHOLD = 30    # 过期阈值（天）
```

### .env 文件

**数据库连接**：
```bash
# MySQL
SQL_HOSTS=127.0.0.1
SQL_PORT=3306
SQL_DATABASE=mitmproxy_records
SQL_USERNAME=root
SQL_PASSWORD=password

# Elasticsearch
ES_HOSTS=http://localhost:9200
ES_USERNAME=elastic
ES_PASSWORD=password
```

## 调试技巧

### 查看日志

```bash
# 实时查看日志
tail -f logs/mitmproxy_records.log

# 查看捕获记录
cat logs/records_*.txt | python -m json.tool
```

### 数据库查询

```python
from db.SQLiteUtils import SQLiteUtils
db = SQLiteUtils()

# 查询所有记录
result = db.query_data("SELECT * FROM mitmproxy_records ORDER BY create_time DESC LIMIT 10")

# 按record_id查询
result = db.query_data("SELECT * FROM mitmproxy_records WHERE record_id='xxx'")
```

### 配置调试

```python
from config_manager import get_config_manager

manager = get_config_manager()
print(manager.get_status())  # 查看状态
print(manager.get_all())     # 查看所有配置
```

### 证书调试

```python
from ssl_cert_manager import get_cert_manager

cert_mgr = get_cert_manager()
info = cert_mgr.get_cert_info()
print(info['is_valid'])       # 是否有效
print(info['days_remaining']) # 剩余天数
```

## 常见问题

### 证书问题

**Q：证书不受信任**
A：运行 `python ssl_cert_manager.py` 或通过 API 调用 `/ssl/cert/ensure`，确保证书已安装到系统信任存储。

**Q：证书生成失败**
A：检查是否安装 OpenSSL。Windows 用户可能需要手动安装或使用 Git Bash。

### 数据库问题

**Q：SQLite 数据库被锁定**
A：确保没有多个进程同时写入。SQLite 不支持高并发写入。

**Q：MySQL 连接失败**
A：检查 `.env` 文件中的数据库配置是否正确。

### 性能问题

**Q：mitmproxy 卡顿**
A：关闭不必要的数据库写入（设置 `SQLITE_ENABLED=False`），或减少过滤条件的复杂度。

## 扩展开发

### 添加新的数据库支持

1. 在 `db/` 目录下创建新的工具类（参考 `SQLiteUtils.py`）
2. 实现 `insert_data()` 和 `query_data()` 方法
3. 在 `config.py` 中添加开关配置
4. 在 `flowproxy.py` 的 `RecordHandler` 中初始化新处理器

### 添加新的过滤规则

在 `RecordHandler.filter_flow()` 中添加条件：

```python
@classmethod
def filter_flow(cls, flow: http.HTTPFlow):
    # ...现有规则...

    # 新规则示例：排除特定路径
    if '/api/health' in flow.request.path:
        return False

    return True
```

### 添加新的 API 端点

在 `web_api.py` 中添加路由：

```python
@app.get("/custom/endpoint", tags=["自定义"])
async def custom_endpoint():
    return {"status": "success"}
```

## 性能优化建议

1. **批量插入**：数据库写入时使用批量插入减少 IO
2. **异步写入**：考虑使用消息队列异步处理数据库写入
3. **连接池**：为 MySQL/ES 添加连接池
4. **内存缓存**：频繁查询的结果使用缓存

## 安全注意事项

⚠️ **重要**：
- 管理 API（web_api.py）**无认证**，不应暴露到公网
- 生产环境应添加认证中间件或绑定到 localhost
- SSL 私钥文件应设置权限为 0600
- 数据库凭据不应硬编码在代码中

## 代码规范

- 使用中文注释和文档字符串
- 遵循 PEP 8 命名规范（类名大驼峰，函数/变量小写下划线）
- 异常处理使用 try-except 并记录日志
- 日志使用 `utils.logger.Log`

## 参考文档

- mitmproxy addon 开发：https://docs.mitmproxy.org/stable/addons-overview/
- FastAPI：https://fastapi.tiangolo.com/
- OpenSSL：https://www.openssl.org/docs/
