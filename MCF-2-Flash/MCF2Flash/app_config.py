import os
from dotenv import load_dotenv
load_dotenv()
# Redis Broker URL
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
# SQLAlchemy Result Backend
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "db+mysql+pymysql://user:password@localhost/celerydb")