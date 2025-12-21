import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Index, TIMESTAMP
from sqlalchemy.sql import text
from MCF2Flash.fastapi_depends import Dec_Base


# db entity可以用于数据库操作，或者用于view函数的返回，但不能作为view函数的输入
# region 定义了所有entities
class BaseMixin:
    """model的基类,所有model都必须继承"""
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now,
                        index=True)
    deleted_at = Column(DateTime)

    __table_args__ = {'mysql_engine': 'InnoDB'}


class TasksListV2(BaseMixin, Dec_Base):
    """
    MCFv2批量模式-任务表
    """
    __tablename__ = 'tasks_list_v2'
    # 覆盖 BaseMixin 中的 updated_at，改为 TIMESTAMP 并由数据库触发器维护
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
        comment='数据更新时间，由触发器更新'
    )
    task_uid      = Column(String(100), nullable=True, comment='任务唯一标识')
    task_content  = Column(String(200), nullable=True, comment='任务内容')
    task_status   = Column(Integer,     nullable=True, comment='任务状态, PENDING -> 3 / ONGOING -> 0 / DONE -> 1 / ERROR -> 2')
    driver_info   = Column(String(50),  nullable=True, comment='驱动信息')
    download_dir  = Column(String(100), nullable=True, comment='下载目录')
    extra_content = Column(Text,        nullable=True, comment='额外内容')
    # 表级配置：字符集、排序规则、存储引擎、注释、索引
    __table_args__ = (
        Index('idx_task_content', 'task_content'),
        Index('idx_task_status',  'task_status'),
        Index('idx_task_uid',     'task_uid'),
        {
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_general_ci',
            'mysql_engine': 'InnoDB',
            'comment': 'MCFv2批量模式-任务表'
        }
    )

    def to_dict(self):
        return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}
# endregion
