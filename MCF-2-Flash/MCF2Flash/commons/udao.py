import datetime
import json
import time
import traceback
from typing import List, Optional

import pandas as pd
import polars as pl
import pymongo
from bson import ObjectId
from pymongo.collection import Collection as MongoCollection
from sqlalchemy import Table, MetaData
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session


class DBUrlFactory(object):
    def __init__(self):
        self.alchemy_driver = '+pymysql'

    def get_url_for_mysql(self, url_template: str, target_db: str, how: str = 'sqlalchemy') -> str:
        """
        根据模板返回构造好的sql连接url

        :param url_template: mysql<DRIVER>://USERNAME:PASSWORD@HOST:PORT/<DB>
        :param target_db: 目标数据库
        :param how: 默认为sqlalchemy，可以选择connectorx
        :return:
        """
        if how == 'sqlalchemy':
            return url_template.replace('<DRIVER>', self.alchemy_driver).replace('<DB>', target_db)
        elif how == 'connectorx':
            return url_template.replace('<DB>', target_db).replace('<DRIVER>', '')
        else:
            raise NotImplementedError("不支持sqlalchemy和connectorx以外的how参数")

    def transform_url_for_cx(self, sqlalchemy_url: str) -> str:
        """
        把sqlalchemy的url转换为connectorx能用的格式

        :param sqlalchemy_url: mysql+pymysql://USERNAME:PASSWORD@HOST:PORT/DB
        :return:
        """
        return sqlalchemy_url.replace(self.alchemy_driver, '')


class UniversalDAO(object):
    """
    适用于RDBMS的数据库工具类

    """

    def __init__(self, db_url: str, logger: any):
        """

        :param db_url: e.g. mysql+mysqldb://<USERNAME>:<PASSWORD>@<HOST>/<DATABASE>?charset=utf8mb4
        """
        self.db_url = db_url
        self.md = None
        self.engine = None
        self.session: Session = None
        self.table_object: Table = None
        self.auto_dispose: bool = True
        self.__table_caches = {}
        self.logger = logger

    # region Init
    def _connect(self, debug_sql: bool = False):
        try:
            self._disconnect()
        except Exception:
            pass
        if not self.md:
            self.md = MetaData()
        if self.engine:
            try:
                self.engine.connect()
            except OperationalError:
                self.engine = create_engine(self.db_url, connect_args={'connect_timeout': 120}, pool_pre_ping=True,
                                            pool_recycle=3600, echo=debug_sql)
        else:
            self.engine = create_engine(self.db_url, connect_args={'connect_timeout': 120}, pool_pre_ping=True,
                                        pool_recycle=3600, echo=debug_sql)

        self.session = Session(self.engine)

    def _disconnect(self):
        if self.session:
            self.session.close()
        self.__dispose()

    def connect(self, debug_sql=False):
        if debug_sql:
            self._connect(True)
        else:
            self._connect(False)

    def disconnect(self):
        self._disconnect()

    def __dispose(self):
        if self.engine:
            self.engine.dispose()

    # endregion

    # region Introspection
    def __new_table(self, name):
        return Table(name, self.md, autoload=True, autoload_with=self.engine)

    def __get_table_object(self, table_name: str):
        if table_name not in self.__table_caches.keys():
            # self.logger.info("建立新的表对象并缓存")
            table_object = self.__new_table(table_name)
            self.__table_caches[table_name] = table_object
            return table_object
        else:
            # self.logger.info("从已有的表对象列表获取实例")
            return self.__table_caches[table_name]

    def get_table_object(self, table_name):
        return self.__get_table_object(table_name)

    # endregion

    # region DML/Insert/Upsert
    def insert_multi_table_with_session(self, table_with_data: List[tuple]) -> bool:
        """
        使用同一个session来导入多个不同表的数据，如果一个报错，则全部回滚，只有全部不报错才提交

        :param table_with_data: [('table1', data1), ('table2', data2)]
        :return:
        """
        self._connect()
        done = 0
        em = ''
        try:
            for twd in table_with_data:
                print(f"导入数据到表: {twd[0]}")
                table_object = self.__get_table_object(twd[0])
                self.session.execute(table_object.insert(), twd[1])
            self.session.commit()
            done = 1
        except Exception as e:
            em = str(e)
            try:
                not_show = em.index("[SQL:")
            except ValueError:
                not_show = len(em) + 1
            em = em[:not_show]
            self.session.rollback()
            done = 0
        finally:
            self._disconnect()
            if done == 0:
                raise RuntimeError("导入报错: \n{}".format(em))
            else:
                return True

    def insert(self, table: str, data: List[dict]) -> bool:
        return self.__insert(data, table)

    def insert_throw_exception(self, table: str, data: List[dict]) -> bool:
        """
        会抛出RuntimeError异常的导入函数，方便实现原子操作

        :param table:
        :param data:
        :return:
        """
        em = None
        # self._connect()
        # self.table_object = Table(table, self.md, autoload=True, autoload_with=self.engine)

        max_try = 5
        while max_try > 0:
            max_try -= 1
            try:
                self._connect()
                self.table_object = self.__get_table_object(table)
                break
            except OperationalError:
                time.sleep(2)
                continue

        succeed = 0
        try:
            self.session.execute(self.table_object.insert(), data)
            self.session.commit()
            succeed = 1
        except Exception as e:
            em = str(e)
            try:
                not_show = em.index("[SQL:")
            except ValueError:
                not_show = len(em) + 1
            em = em[:not_show]
            self.session.rollback()
            succeed = 0
        finally:
            self._disconnect()
            if succeed == 1:
                return True
            else:
                raise RuntimeError("导入报错: \n{}".format(em))

    def upsert_df(self, table: str, df: pd.DataFrame):
        """
        使用cursor以executemany来实现upsert数据
        注意表必须有唯一索引或者主键，否则会变成insert
        警告！！另外要注意replace into会把没有处理到的字段重置为列的默认值，假如原表有10个字段，replace into只处理了其中5个字段，剩余的5个将会被重置为列默认值

        :param table:
        :param df:
        :return:
        """
        if df is None:
            return

        em = None
        succeed = 0

        max_try = 5
        while max_try > 0:
            max_try -= 1
            try:
                self._connect()
                break
            except OperationalError:
                time.sleep(2)
                continue

        conn = self.session.bind.raw_connection().connection
        cursor = conn.cursor()
        fixed_columns = df.columns
        SQL_TEMPLATE = f"REPLACE INTO {table}(" + ",".join(list(fixed_columns)) + ") values(" + ','.join(
            list(map(lambda x: '%s', fixed_columns))) + ")"

        try:
            cursor.executemany(SQL_TEMPLATE, df.values.tolist())
            conn.commit()
            succeed = 1
        except Exception as e:
            em = str(e)
            try:
                not_show = em.index("[SQL:")
            except ValueError:
                not_show = len(em) + 1
            em = em[:not_show]
            conn.rollback()
            succeed = 0
        finally:
            cursor.close()
            self.disconnect()
            if succeed == 1:
                return True
            else:
                raise RuntimeError("导入报错: \n{}".format(em))

    def upsert(self, table: str, data: List[dict]):
        """
        更新插入，如果table已有记录，则更新，table必须有主键或唯一索引，传入data中必须包含主键字段或者唯一键字段
        注意这里的upsert是mysql方言特有的，其他数据库执行upsert需要调整
        :param table:
        :param data:
        :return:
        """
        if not data:
            return

        em = None
        max_try = 5
        while max_try > 0:
            max_try -= 1
            try:
                self._connect()
                self.table_object = self.__get_table_object(table)
                break
            except OperationalError:
                time.sleep(2)
                continue

        succeed = 0
        try:
            for_update = []
            for k, v in data[0].items():
                for_update.append(k)
            # mysql dialect
            inserted_stmt = insert(self.table_object).values(data)
            dup = {k: getattr(inserted_stmt.inserted, k) for k in for_update}
            update_stmt = inserted_stmt.on_duplicate_key_update(**dup)
            self.session.execute(update_stmt)
            self.session.commit()
            succeed = 1
        except Exception as e:
            em = str(e)
            try:
                not_show = em.index("[SQL:")
            except ValueError:
                not_show = len(em) + 1
            em = em[:not_show]
            self.session.rollback()
            succeed = 0
        finally:
            self._disconnect()
            if succeed == 1:
                return True
            else:
                raise RuntimeError("导入报错: \n{}".format(em))

    def __insert(self, data, table_name):
        # self._connect()
        # self.table_object = Table(table_name, self.md, autoload=True, autoload_with=self.engine)
        max_try = 5
        while max_try > 0:
            max_try -= 1
            try:
                self._connect()
                self.table_object = self.__get_table_object(table_name)
                break
            except OperationalError:
                time.sleep(2)
                continue

        succeed = 0
        try:
            self.session.execute(self.table_object.insert(), data)
            self.session.commit()
            succeed = 1
        except Exception as e:
            em = str(e)
            # try:
            #     not_show = em.index("[SQL:")
            # except ValueError:
            #     not_show = len(em) + 1
            # em = em[:not_show]
            self.logger.warning("报错：{}".format(em))
            self.session.rollback()
            succeed = 0
        finally:
            self._disconnect()
            return succeed == 1

    # endregion

    # region Manual
    def execute_single_sql(self, sql: str):
        """
        简单执行SQL语句的工具for human

        :param sql:
        :return:
        """
        self._connect()
        try:
            self.session.execute(sql)
            self.session.commit()
        except Exception as e:
            em = str(e)
            try:
                not_show = em.index("[SQL:")
            except ValueError:
                not_show = len(em) + 1
            em = em[:not_show]
            self.logger.warning("报错：{}".format(em))
            self.session.rollback()
        finally:
            self._disconnect()

    def execute_sql_with_exists_session(self, sql: str):
        """
        简单执行SQL语句的工具for human

        :param sql:
        :return:
        """
        try:
            self.session.execute(sql)
            self.session.commit()
        except Exception as e:
            em = str(e)
            try:
                not_show = em.index("[SQL:")
            except ValueError:
                not_show = len(em) + 1
            em = em[:not_show]
            self.logger.warning("报错：{}".format(em))
            self.session.rollback()

    def view_table(self, sql: str) -> Optional[pd.DataFrame]:
        """
        使用pandas查看数据

        :param sql:
        :return:
        """
        self._connect()
        try:
            df = pd.read_sql(sql, self.session.bind)
            return df
        except Exception as e:
            em = str(e)
            try:
                not_show = em.index("[SQL:")
            except ValueError:
                not_show = len(em) + 1
            em = em[:not_show]
            self.logger.warning("报错：{}".format(em))
            self.session.rollback()
        finally:
            self._disconnect()
        return None

    # endregion

    # region Helper
    def split_dataframe_by_size(self, df: pd.DataFrame, chunk_size: int) -> List[pd.DataFrame]:
        """
        根据分块大小切分dataframe

        :param df:
        :param chunk_size:
        :return:
        """
        results = []
        total_batches = len(df) // chunk_size + (len(df) % chunk_size > 0)
        for chunk in range(total_batches):
            start_idx = chunk * chunk_size
            end_idx = min((chunk + 1) * chunk_size, len(df))
            part = df[start_idx: end_idx]
            results.append(part)

        return results
    # endregion


class MongoDAO(object):
    def __init__(self, url: str, logger: any):
        self.mongo_url = url
        self.client = pymongo.MongoClient(self.mongo_url)
        self.logger = logger

        # reset
        self.current_db_name = None
        self.mongo_conn = None
        self.db = None

    def connect(self, db_name: str):
        try:
            self.mongo_conn.close()
        except Exception:
            pass
        self.mongo_conn = None
        self.db = None
        # re connect
        self.mongo_conn = pymongo.MongoClient(self.mongo_url)
        self.db = self.mongo_conn[db_name]
        self.current_db_name = db_name

    def get_table_object(self, table_name: str, new_db_name: str = None):
        if new_db_name:
            self.connect(new_db_name)
        return self.db[table_name]

    def disconnect(self):
        self.mongo_conn.close()
        self.mongo_conn = None
        self.db = None
        self.current_db_name = None

    def get_documents_by_timestamp(self, db: str, collection: str, start_time: str, end_time: str,
                                   dump_json: bool = False) -> List[dict]:
        """
        根据ObjectID的时间戳范围获取数据

        :param db: mongo数据库
        :param collection: mongo集合
        :param start_time: yyyy-mm-dd HH:MM:SS
        :param end_time: yyyy-mm-dd HH:MM:SS
        :param dump_json: 是否把数据导出为本地的json文件
        :return:
        """
        stamp_st = int(round(datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").timestamp()))
        start_stamp_hex = hex(int(stamp_st))[2:]
        stamp_ed = int(round(datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S").timestamp()))
        end_stamp_hex = hex(int(stamp_ed))[2:]
        query = {"$and": [{"_id": {"$gte": ObjectId(start_stamp_hex + "0000000000000000")}},
                          {"_id": {"$lt": ObjectId(end_stamp_hex + "0000000000000000")}}]}

        self.connect(db)
        col = self.get_table_object(collection)
        docs = [i for i in col.find(query)]

        self.__prepare_output(docs, dump_json)

        return docs

    def __prepare_output(self, docs, dump_json):
        # 删除objectID
        for doc in docs:
            doc['_id'] = 'ObjectID:' + str(doc['_id'])
        if dump_json:
            with open(f'mongoDump_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json', 'w',
                      encoding='utf-8') as f:
                json.dump(docs, f, ensure_ascii=False, indent=4)

    def get_documents_by_simple_in_query(self, db: str, collection: str, in_column: str, optional_values: list,
                                         dump_json: bool = False) -> List[dict]:
        """
        根据简单的in条件查询数据

        :param db: mongo数据库
        :param collection: mongo集合
        :param in_column: 用于执行in查询的字段
        :param optional_values: in的可选值（注意类型匹配！！）
        :param dump_json: 是否把数据导出为本地的json文件
        :return:
        """

        self.connect(db)
        col = self.get_table_object(collection)
        docs = [i for i in col.find({in_column: {'$in': optional_values}})]

        self.__prepare_output(docs, dump_json)

        return docs

    def insert_df(self, collection: MongoCollection, df: pd.DataFrame):
        """
        直接将dataframe导入到mongo

        :param collection:
        :param df:
        :return:
        """
        logger = self.logger
        records = df.to_dict(orient='records')
        if records:
            ack = collection.insert_many(records)
            if ack.acknowledged:
                logger.info(f"MongoDAO -> Inserted {len(ack.inserted_ids)} records into {collection.name}")
                return True
            else:
                return False

    def upsert_df(self, collection: MongoCollection, df: pd.DataFrame, keys: list[str]):
        """
        把数据upsert到mongo

        :param collection:
        :param df:
        :param keys: 用于查询特定记录是否存在的键
        :return:
        """
        logger = self.logger
        if df.empty:
            return

        operations = []
        for record in df.to_dict(orient="records"):
            query = {key: record[key] for key in keys}
            operations.append(
                pymongo.UpdateOne(query, {"$set": record}, upsert=True)
            )

        if operations:
            ack = collection.bulk_write(operations, ordered=False)
            if ack.acknowledged:
                logger.info(f"MongoDAO -> Updated {ack.modified_count} records into {collection.name}")
                logger.info(f"MongoDAO -> Inserted {ack.upserted_count} records into {collection.name}")
                return True
            else:
                return False

    def truncate_collection(self, collection: MongoCollection):
        """
        清空集合

        :param collection:
        :return:
        """
        logger = self.logger
        ack = collection.delete_many({})
        if ack.acknowledged:
            logger.info(f"MongoDAO -> Truncated {collection.name}")
            return True
        else:
            return False


class ConnectorxEnhanced(object):
    def __init__(self, logger: any, sqlalchemy_url: str):
        self.logger = logger
        self.SQLA_url = sqlalchemy_url
        self.dao = UniversalDAO(self.SQLA_url, self.logger)

    def transform_url_for_cx(self, driver: str, sqlalchemy_url: str) -> str:
        """
        把sqlalchemy的url转换为connectorx能用的格式

        :param driver: +pymysql
        :param sqlalchemy_url: mysql+pymysql://USERNAME:PASSWORD@HOST:PORT/DB
        :return:
        """
        return sqlalchemy_url.replace(driver, '')

    def read_sql(self, table: str, sql: str, to_polars: bool = False, **kwargs) -> pd.DataFrame:
        """
        解决connectorx读取mysql的text字段时转换为了bytes的问题

        :param table:
        :param sql:
        :param to_polars: 是否转换为polars DF
        :param kwargs:
        :return:
        """
        import connectorx as cx
        cx_url = self.transform_url_for_cx('+pymysql', self.SQLA_url)

        text_columns = []

        # 先获取表结构
        try:
            self.dao.connect()
            table_obj = self.dao.get_table_object(table)
            table_columns = table_obj.columns
            for c in table_columns:
                if 'TEXT' in str(c.type).upper():
                    text_columns.append(c.name)
        except Exception:
            self.logger.warning(f"无法获取表:{table}的结构")
            self.logger.warning(traceback.format_exc())
        finally:
            self.dao.disconnect()

        # 先转arrow再转pandas避免表一直在更新导致转换pandas报错
        arrow_table = cx.read_sql(cx_url, sql, return_type='arrow2', **kwargs)
        df = arrow_table.to_pandas(split_blocks=False, date_as_object=False)

        if isinstance(df, pd.DataFrame):
            if len(text_columns) > 0:
                self.logger.info(f"如下字段为Text: {text_columns}, 将会进行decode处理")
                for c in text_columns:
                    if c in df.columns:
                        df[c] = df[c].str.decode('utf-8')

        if to_polars:
            self.logger.info("输出为Polars DF")
            return pl.from_pandas(df)
        return df
