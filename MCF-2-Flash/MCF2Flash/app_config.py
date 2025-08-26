import os
from dotenv import load_dotenv
load_dotenv()
MCF_CELERY_LOG_DIR = os.getenv("MCF_CELERY_LOG_DIR", "total_logs")
# Redis Broker URL
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
# SQLAlchemy Result Backend
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "db+mysql+pymysql://user:password@localhost/celerydb")
# MCFv2 Config
# MCF2F_CONFIG = os.getenv("MCF_2F_CONFIG", "config.yaml")
MCF2F_CONFIG = os.getenv("MCF2F_CONFIG", "")
MCF2F_DB_URL = os.getenv("MCF2F_DB_URL", "mysql+pymysql://user:password@localhost/collector_rest")
SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", True)