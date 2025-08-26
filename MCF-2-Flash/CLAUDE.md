# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Overview

**MCF-2-Flash** is a modular web scraping framework built with Python that combines:
- **FastAPI** for REST API endpoints
- **Celery** for distributed task processing
- **SeleniumBase** for browser automation
- **Plugin architecture** using stevedore for extensibility
- **MySQL** for task persistence
- **Redis** for message brokering and configuration storage

## Architecture Components

### Core System (`MCF2Flash/`)
- **MCF2FlashCore** (`mcf_2f/mcf_2f_core.py`): Main orchestrator managing browser instances, plugin loading, and task execution
- **Extension System** (`mcf_2f/extension_mgr.py`): Plugin loader using stevedore entry points under namespace `mcf_v2`
- **Selenium Wrapper** (`mcf_2f/selenium_core.py`): Browser automation layer
- **Database Layer** (`commons/udao.py`): Universal DAO pattern for MySQL operations

### Task Processing
- **Celery Worker** (`celery_core.py`): Configured with Redis broker and MySQL result backend
- **Background Tasks** (`celery_misc/`):
  - `mcf_v2_tasks.py`: Browser lifecycle and task execution
  - `tasks.py`: Framework testing utilities
- **Task Model**: MySQL table `collector_rest.tasks_list_v2` with status codes:
  - 3: PENDING
  - 0: ONGOING
  - 1: DONE
  - 2: ERROR

### Web API (`rest_core.py`)
- **FastAPI** application with endpoints in `controllers/mcf_v2_view.py`
- **Routes**:
  - POST `/mcf/v2/tasks/single/`: Single task submission
  - POST `/mcf/v2/tasks/bulk/`: Bulk task submission
  - POST `/mcf/v2/tasks/run_not_done`: Execute pending tasks
  - GET endpoints for task queries and Celery result monitoring

## Development Commands

### Environment Setup
```bash
# Install dependencies (requirements not found - check setup.py or pyproject.toml)
pip install -e .

# Core runtime dependencies (inferred):
# fastapi, celery, redis, sqlalchemy, pymysql, seleniumbase, stevedore, loguru, pyyaml, pandas
```

### Running Services
```bash
# Start Celery worker (Windows)
celery -A MCF2Flash.celery_core worker --pool=solo --loglevel=info

# Start Celery worker (Linux)
celery -A MCF2Flash.celery_core worker --loglevel=info

# Start FastAPI server
uvicorn MCF2Flash.rest_core:app --host 0.0.0.0 --port 8081

# Interactive REPL mode
python MCF2Flash/mcf_2f_shell.py -c configs/main_config.yaml
```

### Configuration
- **Main Config**: YAML file with sections for Selenium, Common, Logging, Extensions
- **Environment Variables** (in `app_config.py`):
  - `MCF_CELERY_LOG_DIR`: Celery log directory (default: "total_logs")
  - `CELERY_BROKER_URL`: Redis broker (default: "redis://localhost:6379/0")
  - `CELERY_RESULT_BACKEND`: MySQL backend (default: "db+mysql+pymysql://user:password@localhost/celerydb")
  - `MCF2F_DB_URL`: Application database (default: "mysql+pymysql://user:password@localhost/collector_rest")
  - `MCF2F_CONFIG`: Path to YAML config file

### Plugin Development
- **Entry Point Namespace**: `mcf_v2`
- **Base Class**: `AbstractExtensionMCFV2` (`commons/v2_abstract_extension.py`)
- **Required Methods**: `prepare()`, `handle()`, `parse_extension_config()`, `parse_tasklist_to_redis()`, `get_name()`, `get_plugin_return()`
- **Plugin Config**: Defined in YAML under `Extensions.ByExtensions.{plugin_name}`

### Database Setup
```sql
-- Use the provided DDL file
source MCF2Flash/DDL/task_list.sql
```

### Testing
- **Celery Test Tasks**: Available in `celery_misc/tasks.py`
- **API Testing**: Use `/async_result/{task_id}` endpoint for Celery task monitoring
- **Browser Testing**: `/mcf/v2/init_browser` and `/mcf/v2/dispose_browser` endpoints

## Key Patterns

### Task Flow
1. Tasks submitted via API → MySQL `tasks_list_v2` table
2. Celery worker polls for PENDING tasks (status=3)
3. Plugin processes tasks via Redis configuration
4. Results update task status in database

### Extension Loading
- Uses stevedore for plugin discovery
- Plugins register via setuptools entry points under `mcf_v2` namespace
- Configuration templates loaded from Redis or YAML files

### Browser Management
- Singleton pattern via Celery worker process
- Lazy initialization in `MCF2FlashCore.init_browser()`
- Automatic cleanup via `@worker_process_shutdown` signal

## Response Language
**除非有特殊说明，请用中文回答。** (Unless otherwise specified, please respond in Chinese.)