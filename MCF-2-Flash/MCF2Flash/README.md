# MCF-2-Flash 项目文档

## 项目概述

MCF-2-Flash 是一个基于 Python 的自动化浏览器任务执行框架，主要用于执行各种网页自动化任务。它结合了 FastAPI、Celery、SeleniumBase 等技术，提供了一个可扩展的插件化架构，支持通过 REST API 或异步任务方式执行浏览器自动化操作。

该框架支持批量任务处理，通过数据库管理任务状态，并利用 Redis 进行任务队列和插件间通信。通过插件化架构，可以轻松扩展支持不同网站的自动化操作。

## 核心组件

### 1. 架构设计

```
MCF-2-Flash/
├── MCF2Flash/              # 主应用目录
│   ├── commons/            # 通用工具模块
│   ├── controllers/        # API 控制器
│   ├── domains/            # 数据模型定义
│   ├── entities/           # 数据库实体
│   ├── repository/         # 数据访问层
│   ├── mcf_2f/             # 核心功能模块
│   ├── celery_misc/        # Celery 任务定义
│   ├── DDL/                # 数据库脚本
│   └── configs_example/    # 配置文件示例
└── TMP/                    # 临时文件目录
```

### 2. 技术栈

- **FastAPI**: 提供 RESTful API 接口
- **Celery**: 异步任务队列处理
- **SeleniumBase**: 浏览器自动化
- **Redis**: 任务队列和数据缓存
- **MySQL**: 持久化数据存储
- **Stevedore**: 插件管理

## 核心模块详解

### 数据访问层 (commons/udao.py)

项目提供了统一的数据访问对象 [UniversalDAO](file:///C:/Users/ckhoi/PycharmProjects/atelier-medusa/MCF-2-Flash/MCF2Flash/commons/udao.py#L32-L364)，用于处理关系型数据库操作：

1. 支持 MySQL 等关系型数据库操作
2. 提供连接管理、表对象缓存等功能
3. 支持批量插入、更新插入（upsert）等操作
4. 集成 SQLAlchemy ORM 进行数据库操作

### 网络工具 (commons/net_io.py)

提供 [SimpleRedis](file:///C:/Users/ckhoi/PycharmProjects/atelier-medusa/MCF-2-Flash/MCF2Flash/commons/net_io.py#L6-L44) 类用于简化 Redis 操作：

1. 支持 Redis 连接管理
2. 提供 get/set/delete/exists 等基本操作
3. 自动处理连接 URL 解析

### MCF2Flash Core (mcf_2f_core.py)

这是系统的核心模块，负责：

1. 加载和管理配置文件
2. 初始化浏览器实例
3. 管理插件系统
4. 执行任务队列

主要功能包括：
- 浏览器生命周期管理
- 插件加载和调用
- 数据库任务执行
- 目录结构初始化

该模块使用 [SBOmniWrapper](file:///C:/Users/ckhoi/PycharmProjects/atelier-medusa/MCF-2-Flash/MCF2Flash/mcf_2f/selenium_core.py#L76-L174) 来管理浏览器实例，支持 Chrome 等浏览器，并可配置代理、用户数据目录、扩展等参数。

### 插件系统 (extension_mgr.py)

采用 Stevedore 实现插件化架构：

1. 支持动态加载插件
2. 提供统一的插件接口调用方式
3. 支持插件热插拔

插件需继承 [AbstractExtensionMCFV2](file:///C:/Users/ckhoi/PycharmProjects/atelier-medusa/MCF-2-Flash/MCF2Flash/commons/v2_abstract_extension.py#L100-L175) 抽象类并实现以下方法：
- `prepare()`: 初始化阶段
- `handle()`: 实际执行阶段
- `parse_extension_config()`: 解析插件配置
- `parse_tasklist_to_redis()`: 解析任务列表到 Redis
- `get_name()`: 获取插件名称
- `get_plugin_return()`: 获取插件返回值

插件通过 Python 的 entry-points 机制进行注册，配置中指定的 namespace 决定了哪些插件会被加载。

### 数据库设计 (entities/defined_entities.py)

使用 SQLAlchemy ORM 定义数据实体：

- [TasksListV2](file:///C:/Users/ckhoi/PycharmProjects/atelier-medusa/MCF-2-Flash/MCF2Flash/entities/defined_entities.py#L24-L49): 任务列表实体
  - `task_uid`: 任务唯一标识
  - `task_content`: 任务内容
  - `task_status`: 任务状态 (3=PENDING, 0=ONGOING, 1=DONE, 2=ERROR)
  - `driver_info`: 驱动信息
  - `download_dir`: 下载目录
  - `extra_content`: 额外内容

### API 接口 (controllers/mcf_v2_view.py)

提供 RESTful API 接口：

1. 浏览器控制接口
   - `/mcf/v2/init_browser`: 初始化浏览器
   - `/mcf/v2/dispose_browser`: 关闭浏览器

2. 任务管理接口
   - `/mcf/v2/tasks/single/`: 接收单个任务
   - `/mcf/v2/tasks/bulk/`: 接收批量任务
   - `/mcf/v2/tasks/{uid}`: 获取单个任务
   - `/mcf/v2/tasks/status/`: 按状态获取任务
   - `/mcf/v2/tasks/run_not_done`: 执行未完成任务

### 异步任务 (celery_misc/mcf_v2_tasks.py)

通过 Celery 实现异步任务处理：

- `init_browser`: 初始化浏览器
- `dispose_browser`: 关闭浏览器
- `run_tasks_not_done`: 执行数据库中未完成的任务

这些任务通过 [celery_core.py](file:///C:/Users/ckhoi/PycharmProjects/atelier-medusa/MCF-2-Flash/MCF2Flash/celery_core.py) 中定义的 Celery 应用进行管理，支持 Redis 作为消息代理和 MySQL 作为结果后端。

## 配置文件

### 主配置文件 (main_config.yaml)

包含以下主要配置项：

1. **Selenium 配置**
   - `binary_location`: 浏览器可执行文件路径
   - `proxy`: 代理设置
   - `user_data_dir`: 用户数据目录
   - `user_agent`: 用户代理
   - `uc`: 是否启用无头模式

2. **通用配置**
   - `max_timeout`: 最大超时时间
   - `max_workers`: 最大工作线程数
   - `target_save_dir`: 目标保存目录

3. **日志配置**
   - `logfile_dir`: 日志文件目录
   - `screenshots`: 截图保存目录

4. **插件配置**
   - `namespace`: 插件命名空间
   - `plugin_logs_dir`: 插件日志目录
   - `ByExtensions`: 各插件特定配置

## 使用方法

### 1. 环境准备

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

2. 配置数据库并执行 DDL 脚本：
   ```sql
   CREATE TABLE collector_rest.tasks_list_v2 (...);
   ```

3. 配置 Redis 服务

4. 配置环境变量或修改 [app_config.py](file:///C:/Users/ckhoi/PycharmProjects/atelier-medusa/MCF-2-Flash/MCF2Flash/app_config.py)

5. 根据 [configs_example](file:///C:/Users/ckhoi/PycharmProjects/atelier-medusa/MCF-2-Flash/configs_example) 目录中的示例创建主配置文件，配置浏览器路径、代理、用户数据目录等参数

### 2. 启动服务

#### 启动 Celery Worker

Windows 系统：
```powershell
celery -A MCF2Flash.celery_core worker --pool=solo --loglevel=info
```

Linux 系统：
```bash
celery -A MCF2Flash.celery_core worker --loglevel=info
```

#### 启动 FastAPI 服务

```powershell
uvicorn MCF2Flash.rest_core:app --host 0.0.0.0 --port 8081
```

### 3. 使用 API

1. 添加任务：
   ```bash
   curl -X POST "http://localhost:8081/mcf/v2/tasks/single/" -H "Content-Type: application/json" -d '{"url": "https://example.com"}'
   ```

2. 执行任务：
   ```bash
   curl -X POST "http://localhost:8081/mcf/v2/tasks/run_not_done"
   ```

3. 查询任务状态：
   ```bash
   curl "http://localhost:8081/mcf/v2/tasks/status/?code=1"
   ```

### 4. 开发插件

1. 继承 [AbstractExtensionMCFV2](file:///C:/Users/ckhoi/PycharmProjects/atelier-medusa/MCF-2-Flash/MCF2Flash/commons/v2_abstract_extension.py#L100-L175) 类
2. 实现所有抽象方法
3. 在 `setup.py` 中注册 entry-point
4. 在配置文件中添加插件配置

## 任务处理流程

1. 通过 API 接口添加任务到数据库
2. 调用执行接口触发任务处理
3. 系统从数据库读取未完成任务
4. 根据 [driver_info](file:///C:/Users/ckhoi/PycharmProjects/atelier-medusa/MCF-2-Flash/MCF2Flash/entities/defined_entities.py#L42-L42) 字段匹配插件
5. 将任务数据转换为插件可识别格式并存入 Redis
6. 调用对应插件执行任务
7. 更新任务状态到数据库

## 日志和监控

- 系统使用 Loguru 进行日志记录
- 提供 `/async_result/{task_id}` 接口查询异步任务结果
- 支持截图保存用于调试

## 注意事项

1. 确保浏览器驱动与浏览器版本匹配
2. 注意插件命名空间配置正确
3. Redis 连接配置需要与插件配置一致
4. 数据库连接信息需要正确配置
5. 日志目录、下载目录等需要有相应权限
6. 浏览器用户数据目录需要正确配置以保持会话状态