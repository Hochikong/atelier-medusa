from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from MCF2Flash.commons.v2_abstract_extension import AbstractExtensionNameSpaceCommon
from MCF2Flash.mcf_2f.mcf_2f_core import DriverMgmt
from MCF2Flash.app_config import MCF2F_DB_URL, SQLALCHEMY_ECHO, MCF2F_CONFIG

# SQLite
# engine = create_engine(
#     SQLALCHEMY_DATABASE_URI,  # SQLAlchemy 数据库连接串，格式见下面
#     echo=bool(SQLALCHEMY_ECHO),  # 是不是要把所执行的SQL打印出来，一般用于调试
#     connect_args={"check_same_thread": False}
# )

# Mysql
engine = create_engine(
    MCF2F_DB_URL,  # SQLAlchemy 数据库连接串，格式见下面
    echo=bool(SQLALCHEMY_ECHO),  # 是不是要把所执行的SQL打印出来，一般用于调试
    pool_recycle=3600
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Dec_Base = declarative_base()
driver_mgmt_instance = DriverMgmt(MCF2F_CONFIG)


def get_driver_mgmt() -> DriverMgmt:
    return driver_mgmt_instance


def get_namespace_common() -> AbstractExtensionNameSpaceCommon:
    # NSCommon是固定名称，所有插件namespace都需要提供他
    plugin: AbstractExtensionNameSpaceCommon = driver_mgmt_instance.extension_loader['NSCommon']
    return plugin
