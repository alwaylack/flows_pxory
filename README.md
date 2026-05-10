# 基于 mitmproxy 的流量录制工具

> 基于 mitmproxy 的流量录制工具，能够捕获 HTTP/HTTPS 网络请求和响应数据，并存储到 SQLite/MySQL/Elasticsearch 数据库中，同时提供 Web 界面进行查看和管理。

---

## 📋 目录

- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [环境准备](#环境准备)
- [配置说明](#配置说明)
- [使用指南](#使用指南)
- [API 接口文档](#api-接口文档)
- [开发工作流程](#开发工作流程)
- [调试技巧](#调试技巧)
- [常见问题](#常见问题)
- [扩展开发](#扩展开发)

---

## 功能特性

- **流量捕获**：基于 mitmproxy 拦截和录制 HTTP/HTTPS 请求/响应数据
- **智能过滤**：支持域名白名单、URL 关键词过滤、API 路径模糊匹配
- **多数据库支持**：SQLite（默认）、MySQL、Elasticsearch
- **动态配置**：配置文件热重载，无需重启 mitmproxy 即可生效
- **SSL 证书管理**：自动检测、生成和安装受信任的 SSL 证书
- **Web 界面**：通过 FastAPI 提供 REST API 和数据查询界面
- **日志记录**：完整的操作日志和错误追踪

---

## 系统架构

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
   - `RecordHandler.filter_flow()` 执行过滤逻辑
   - `request()` 保存请求数据到内存映射表
   - `response()` 匹配响应，组合完整记录

2. **存储阶段**：
   - 写入日志文件（JSON 格式）
   - 写入 SQLite 数据库（默认启用）
   - 可选写入 MySQL、Elasticsearch

3. **配置管理**：
   - `ConfigManager` 监控 `config.py` 文件变更（MD5 哈希检测）
   - 变更时自动重载配置模块
   - 触发回调重新初始化数据库处理器

4. **证书管理**：
   - `SSLCertManager` 检查证书状态
   - 自动生成缺失/过期证书（OpenSSL）
   - 安装到系统信任存储（Windows/macOS/Linux）

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 确保证书（首次运行）

```bash
# 方式一：通过 API
python web_api.py  # 访问 http://localhost:8000/docs，调用 /ssl/cert/ensure

# 方式二：直接运行
python ssl_cert_manager.py
```

### 3. 启动流量捕获

```bash
# 方式1：mitmproxy（交互式）
mitmproxy -s flowproxy.py

# 方式2：mitmweb（带 Web 界面）
mitmweb -s flowproxy.py

# 方式3：指定端口
mitmproxy -s flowproxy.py -p 8081
```

### 4. 配置浏览器代理

- HTTP 代理：`127.0.0.1:8080`
- HTTPS 代理：`127.0.0.1:8080`
- 安装证书：访问 http://mitm.it 下载并安装对应系统的证书

### 5. 启动 Web 界面（可选）

```bash
python webdisplay.py
# 访问 http://localhost:8000/record/no/response/all
```

---

## 环境准备

### 系统要求

- **Python**: 3.6+
- **mitmproxy**: 11.0.2+
- **数据库**（任选）: MySQL 5.7+ / SQLite 3+ / Elasticsearch 7.x

### 依赖清单

```
pymysql~=1.1.1
elasticsearch~=7.13.3
python-dotenv~=1.0.1
mitmproxy~=11.0.2
uvicorn~=0.30.6
fastapi~=0.115.6
requests~=2.32.3
logbook~=1.8.0
```

---

## 配置说明

### 核心配置文件

#### `config.py`

```python
class Config(object):
    # 流量过滤配置
    HOST = ["isgp.hik-partner.com"]  # 需要抓取的域名列表
    APIS = []                         # 需要抓取的API路径列表
    
    # 日志配置
    LOG_LEVEL = 11                    # 日志级别 (10=DEBUG, 11=INFO)
    FILE_HANDLER_ENABLED = True       # 文件日志开关
    STREAM_HANDLER_ENABLED = False    # 控制台日志开关
    
    # 数据库配置
    SQLITE_ENABLED = True             # SQLite 开关
    ES_ENABLED = False                # Elasticsearch 开关
    SQL_ENABLED = False               # MySQL 开关
    
    # 动态配置管理
    AUTO_CONFIG_RELOAD = True         # 自动重载配置
    CONFIG_CHECK_INTERVAL = 2         # 配置检查间隔（秒）
    
    # SSL 证书管理
    SSL_CERT_AUTO_MANAGE = True       # 自动管理SSL证书
    SSL_CERT_CHECK_INTERVAL = 3600    # 证书检查间隔（秒）
    SSL_CERT_EXPIRY_THRESHOLD = 30    # 过期阈值（天）
```

#### `.env`（数据库连接）

```bash
# MySQL
SQL_HOSTS=127.0.0.1
SQL_PORT=3306
SQL_DATABASE=mitmproxy_records
SQL_USERNAME=root
SQL_PASSWORD=your_password

# Elasticsearch
ES_HOSTS=http://localhost:9200
ES_USERNAME=elastic
ES_PASSWORD=your_password
```

---

## 使用指南

### 流量过滤规则

`RecordHandler.filter_flow()` 执行以下过滤：

1. **排除静态资源**：`.ico, .css, .js, .png, .jpg, .gif, .svg, .ttf, .woff, .woff2, .eot, .otf`
2. **域名白名单**：仅捕获 `Config.HOST` 列表中的域名
3. **URL 关键词过滤**：必须包含 `hpp` 或 `hcc` 或 `ccf`
4. **API 路径模糊匹配**：与 `Config.APIS` 中的路径相似度 > 0.6

### 数据库表结构

```sql
CREATE TABLE mitmproxy_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT not null,          -- 记录唯一ID
    url TEXT not null,                -- 请求URL
    method TEXT not null,             -- 请求方法
    headers TEXT not null,            -- 请求头
    body text,                        -- 请求体
    response_code TEXT not null,      -- 响应码
    response_body text,               -- 响应体
    create_time datetime default current_timestamp  -- 创建时间
)
```

### 限制策略

- **请求体大小**：最大 10MB，超出部分截断
- **响应体大小**：最大 10MB，超出部分截断
- **URL 路径**：自动将长路径（>30字符）替换为 `/*`

---

## API 接口文档

### 配置管理

| 方法 | 路径 | 功能 | 标签 |
|------|------|------|------|
| GET | `/config` | 获取所有配置（过滤敏感信息） | 配置管理 |
| GET | `/config/{key}` | 获取指定配置项 | 配置管理 |
| POST | `/config` | 更新单个配置项 | 配置管理 |
| PUT | `/config/batch` | 批量更新配置项 | 配置管理 |
| POST | `/config/reload` | 手动触发配置重载 | 配置管理 |
| GET | `/config/status` | 获取配置管理器状态 | 配置管理 |

**请求示例**：

```bash
# 更新配置
curl -X POST http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{"key": "LOG_LEVEL", "value": 10}'

# 批量更新
curl -X PUT http://localhost:8000/config/batch \
  -H "Content-Type: application/json" \
  -d '{"updates": {"SQLITE_ENABLED": false, "ES_ENABLED": true}}'
```

### SSL 证书管理

| 方法 | 路径 | 功能 | 标签 |
|------|------|------|------|
| GET | `/ssl/cert` | 获取证书信息 | SSL证书管理 |
| POST | `/ssl/cert/ensure` | 确保证书状态 | SSL证书管理 |
| POST | `/ssl/cert/generate` | 强制重新生成证书 | SSL证书管理 |
| POST | `/ssl/cert/install` | 安装证书到系统信任存储 | SSL证书管理 |
| GET | `/ssl/cert/check` | 检查证书有效性 | SSL证书管理 |
| POST | `/ssl/cert/cleanup` | 清理旧证书备份 | SSL证书管理 |

**请求示例**：

```bash
# 检查证书
curl http://localhost:8000/ssl/cert/check

# 生成新证书
curl -X POST http://localhost:8000/ssl/cert/generate
```

### 系统健康检查

| 方法 | 路径 | 功能 | 标签 |
|------|------|------|------|
| GET | `/health` | 健康检查 | 系统 |

**响应示例**：

```json
{
  "status": "healthy",
  "timestamp": "2026-05-10T14:50:00",
  "services": {
    "config_manager": { "status": "running", "auto_reload": true },
    "ssl_cert_manager": { "status": "active", "cert_valid": true }
  },
  "cert_info": { "valid": true, "days_remaining": 365 }
}
```

---

## 开发工作流程

### 项目结构

```
.
├── curd/
│   └── dataquery.py          # 数据库查询 CRUD 操作
├── data/
│   └── mitmproxy_records.db  # SQLite 数据库文件
├── db/
│   ├── DBUtils.py            # MySQL 数据库工具类
│   ├── Elastics.py           # Elasticsearch 工具类
│   └── SQLiteUtils.py        # SQLite 工具类
├── logs/                     # 日志目录
├── templates/                # Web 模板目录
│   ├── record.html           # 无响应体记录页面
│   └── record_with_response.html  # 带响应体记录页面
├── utils/
│   ├── utils.py              # 通用工具类
│   └── logger.py             # 日志工具类
├── .env                      # 数据库连接配置
├── config.py                 # 核心配置
├── flowproxy.py              # mitmproxy 启动文件
├── web_api.py                # 配置管理 API
├── webdisplay.py             # Web 界面
├── README.md                 # 项目文档
└── requirements.txt          # 项目依赖
```

### 本地开发

1. **克隆项目**

```bash
git clone <repository-url>
cd flows_proxy
```

2. **安装依赖**

```bash
pip install -r requirements.txt
```

3. **配置环境**

```bash
# 编辑 .env 文件，配置数据库连接
vim .env
```

4. **修改配置**

```bash
vim config.py
# 根据需要调整 HOST、APIS、数据库开关等
```

5. **运行测试**

```bash
# 启动 API 服务
python web_api.py

# 启动 Web 界面
python webdisplay.py

# 启动 mitmproxy
mitmproxy -s flowproxy.py
```

---

## 调试技巧

### 查看日志

```bash
# 实时查看日志
tail -f logs/mitmproxy_records.log

# 查看最新记录
cat logs/records_*.txt | python -m json.tool | tail -50
```

### 数据库查询

```python
from db.SQLiteUtils import SQLiteUtils

db = SQLiteUtils()

# 查询所有记录（最近10条）
result = db.query_data(
    "SELECT * FROM mitmproxy_records ORDER BY create_time DESC LIMIT 10"
)

# 按 record_id 查询
result = db.query_data(
    "SELECT * FROM mitmproxy_records WHERE record_id='xxx'"
)

# 统计记录数
result = db.query_data(
    "SELECT COUNT(*) as total FROM mitmproxy_records"
)

db.close()
```

### 配置调试

```python
from config_manager import get_config_manager

manager = get_config_manager()
print(manager.get_status())      # 查看状态
print(manager.get_all())         # 查看所有配置
print(manager.get("HOST"))       # 获取特定配置
```

### 证书调试

```python
from ssl_cert_manager import get_cert_manager

cert_mgr = get_cert_manager()
info = cert_mgr.get_cert_info()
print(f"证书有效: {info['is_valid']}")
print(f"剩余天数: {info['days_remaining']}")
print(f"过期时间: {info['expiry_date']}")
```

### mitmproxy 调试

```bash
# 调试模式运行
mitmproxy -s flowproxy.py --set console_eventlog_verbosity=debug

# 查看 mitmproxy 日志
mitmweb --set console_eventlog_verbosity=info -s flowproxy.py
```

---

## 常见问题

### 证书问题

**Q：证书不受信任，浏览器提示不安全**

A：运行以下命令确保证书已安装到系统信任存储：

```bash
python ssl_cert_manager.py
```

或通过 API：

```bash
curl -X POST http://localhost:8000/ssl/cert/ensure
```

如果仍有问题，请检查：

1. 证书是否已安装到正确的存储位置
2. 浏览器是否已重启（某些浏览器需要重启才能识别新证书）
3. 系统日期和时间是否正确

**Q：证书生成失败**

A：检查是否安装了 OpenSSL：

```bash
openssl version
```

如果没有安装：

- **Windows**：安装 Git for Windows（包含 OpenSSL）
- **macOS**：`brew install openssl`
- **Linux**：`sudo apt-get install openssl`

### 数据库问题

**Q：SQLite 数据库被锁定**

A：SQLite 不支持高并发写入。确保：

1. 没有多个进程同时写入同一个数据库文件
2. 数据库连接已正确关闭
3. 尝试删除 `data/mitmproxy_records.db` 并重启（会丢失数据）

**Q：MySQL 连接失败**

A：检查 `.env` 文件中的数据库配置是否正确：

```bash
# 测试连接
mysql -h 127.0.0.1 -P 3306 -u root -p
```

确保：

1. MySQL 服务正在运行
2. 用户名和密码正确
3. 数据库已创建
4. 防火墙允许连接

**Q：Elasticsearch 连接失败**

A：检查 Elasticsearch 是否运行：

```bash
curl http://localhost:9200
```

确保：

1. Elasticsearch 服务正在运行
2. 版本兼容（7.x）
3. 认证信息正确（如果启用了安全认证）

### 性能问题

**Q：mitmproxy 卡顿或响应缓慢**

A：尝试以下优化：

1. 关闭不必要的数据库写入：
   ```python
   # 在 config.py 中
   SQLITE_ENABLED = False
   ES_ENABLED = False
   SQL_ENABLED = False
   ```

2. 减少过滤条件的复杂度
3. 增加系统资源（内存、CPU）
4. 使用更高效的过滤器

**Q：日志文件过大**

A：定期清理旧日志：

```bash
# 保留最近7天的日志
find logs/ -name "*.log" -mtime +7 -delete
find logs/ -name "records_*.txt" -mtime +7 -delete
```

### 代理配置问题

**Q：浏览器无法通过代理访问网站**

A：检查以下内容：

1. mitmproxy 是否正在运行（端口 8080）
2. 浏览器代理设置是否正确（127.0.0.1:8080）
3. 证书是否已安装并信任
4. 防火墙是否阻止了连接

**Q：HTTPS 网站无法访问**

A：确保：

1. 证书已正确安装
2. 浏览器信任 mitmproxy 证书
3. mitmproxy 正在运行且未报错
4. 尝试清除浏览器缓存

### 配置重载问题

**Q：修改 config.py 后配置未生效**

A：检查以下内容：

1. `AUTO_CONFIG_RELOAD` 是否设置为 `True`
2. 配置文件是否已保存
3. 查看日志确认是否检测到文件变更
4. 手动触发重载：
   ```bash
   curl -X POST http://localhost:8000/config/reload
   ```

**Q：配置重载后数据库连接失败**

A：配置重载会重新初始化数据库处理器。如果失败，请检查：

1. 数据库连接信息是否正确
2. 数据库服务是否运行
3. 查看日志中的错误信息

---

## 扩展开发

### 添加新的数据库支持

1. 在 `db/` 目录下创建新的工具类（参考 `SQLiteUtils.py`）：

```python
class PostgreSQLUtils:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self._connect()
    
    def _connect(self):
        # 连接 PostgreSQL
        pass
    
    def insert_data(self, table_name, data):
        pass
    
    def query_data(self, sql):
        pass
    
    def close(self):
        pass
```

2. 在 `config.py` 中添加开关配置
3. 在 `flowproxy.py` 中初始化新处理器

### 添加新的过滤规则

在 `RecordHandler.filter_flow()` 中添加条件：

```python
@classmethod
def filter_flow(cls, flow: http.HTTPFlow):
    # ... 现有规则
    
    # 新规则：排除特定路径
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

---

## 性能优化建议

1. **批量插入**：数据库写入时使用批量插入减少 IO
2. **异步写入**：使用消息队列异步处理数据库写入
3. **连接池**：为 MySQL/Elasticsearch 添加连接池
4. **内存缓存**：频繁查询的结果使用缓存
5. **索引优化**：为常用查询字段添加数据库索引
6. **日志轮转**：配置日志轮转策略
7. **流量采样**：高流量场景下配置采样率

---

## 安全注意事项

⚠️ **重要**：

1. **管理 API 无认证**：`web_api.py` 无认证机制，不应暴露到公网
2. **SSL 私钥安全**：私钥文件权限应设置为 `0600`
3. **数据库凭据**：不应硬编码在代码中，使用环境变量
4. **敏感数据过滤**：API 返回配置时自动过滤敏感信息
5. **证书管理**：定期检查和更新证书

---

## 代码规范

- 使用中文注释和文档字符串
- 遵循 PEP 8 命名规范
- 异常处理使用 try-except 并记录日志
- 日志使用 `utils.logger.Log`

---

## 参考文档

- [mitmproxy addon 开发文档](https://docs.mitmproxy.org/stable/addons-overview/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [OpenSSL 文档](https://www.openssl.org/docs/)

---

## 许可证

MIT License

---

## 贡献

欢迎提交 Issue 和 Pull Request。

## 更新日志

### v1.0.0 (2026-05-10)
- ✅ 完整的流量录制功能
- ✅ 多数据库支持（SQLite/MySQL/Elasticsearch）
- ✅ 动态配置热重载
- ✅ SSL 证书自动管理
- ✅ Web API 和数据查询界面
- ✅ 完整的文档和示例