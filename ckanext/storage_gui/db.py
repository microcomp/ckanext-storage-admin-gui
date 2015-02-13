import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import class_mapper
from sqlalchemy import create_engine
import logging

log = logging.getLogger(__name__)



storage_stat_table = None
StorageStat = None


def make_uuid():
    return unicode(uuid.uuid4())

def retrieve_actual_usage(model):
    sql = '''
    select t.subject_id, t.time, t.filestore_usage, t.database_usage, t.triplestore_usage from ckanext_storage_stat t
        inner join (
            select subject_id, max(time) as MaxTime
            from ckanext_storage_stat
            group by subject_id
        ) tm on t.subject_id = tm.subject_id and t.time = tm.MaxTime;   
    '''
    res = None
    conn = model.Session.connection()
    try:
        res= conn.execute(sql)
    except sa.exc.ProgrammingError as e:
        model.Session.rollback()
        log.exception(e)
        return None
    model.Session.commit()
    return res
    
def table_exists(name, model):
    sql = '''
        SELECT EXISTS (
            SELECT 1 
            FROM   pg_catalog.pg_class c
            JOIN   pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE  n.nspname = 'public'
            AND    c.relname = '{0}'
            AND    c.relkind = 'r'    -- only tables(?)
        );
    '''.format(name)
    log.info(sql)
    res = None
    conn = model.Session.connection()
    try:
        res= conn.execute(sql)
    except sa.exc.ProgrammingError as e:
        model.Session.rollback()
        log.exception(e)
        return None
    model.Session.commit()
    return res

def init_db(model):
    class _StorageStat(model.DomainObject):

        @classmethod
        def get(cls, **kw):
            '''Finds a single entity in the register.'''
            query = model.Session.query(cls).autoflush(False)
            return query.filter_by(**kw).all()
        @classmethod
        def delete(cls, **kw):
            query = model.Session.query(cls).autoflush(False).filter_by(**kw).all()
            for i in query:
                model.Session.delete(i)
            return


        @classmethod
        def storage_stat(cls, **kw):
            '''Finds a single entity in the register.'''
            order = kw.pop('order', False)

            query = model.Session.query(cls).autoflush(False)
            query = query.filter_by(**kw)
            if order:
                query = query.order_by(cls.order).filter(cls.order != '')
            return query.all()

    global StorageStat
    StorageStat = _StorageStat
    # We will just try to create the table.  If it already exists we get an
    # error but we can just skip it and carry on.
    sql = '''
                CREATE TABLE ckanext_storage_stat (
                    id text NOT NULL,
                    subject_id text NOT NULL,
                    filestore_usage bigint,
                    database_usage bigint,
                    triplestore_usage bigint,
                    time timestamp
                );
    '''
    conn = model.Session.connection()
    try:
        conn.execute(sql)
    except sa.exc.ProgrammingError:
        model.Session.rollback()
    model.Session.commit()

    types = sa.types
    global storage_stat_table
    storage_stat_table = sa.Table('ckanext_storage_stat', model.meta.metadata,
        sa.Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        sa.Column('subject_id', types.UnicodeText, default=u''),
        sa.Column('filestore_usage', types.BigInteger, default=0),
        sa.Column('database_usage', types.BigInteger, default=0),
        sa.Column('triplestore_usage', types.BigInteger, default=0),
        sa.Column('time', types.DateTime, default=datetime.datetime.utcnow)
    )

    model.meta.mapper(
        StorageStat,
        storage_stat_table,
    )


def table_dictize(obj, context, **kw):
    '''Get any model object and represent it as a dict'''
    result_dict = {}

    if isinstance(obj, sa.engine.base.RowProxy):
        fields = obj.keys()
    else:
        ModelClass = obj.__class__
        table = class_mapper(ModelClass).mapped_table
        fields = [field.name for field in table.c]

    for field in fields:
        name = field
        if name in ('current', 'expired_timestamp', 'expired_id'):
            continue
        if name == 'continuity_id':
            continue
        value = getattr(obj, name)
        if value is None:
            result_dict[name] = value
        elif isinstance(value, dict):
            result_dict[name] = value
        elif isinstance(value, int):
            result_dict[name] = value
        elif isinstance(value, datetime.datetime):
            result_dict[name] = value.isoformat()
        elif isinstance(value, list):
            result_dict[name] = value
        else:
            result_dict[name] = unicode(value)

    result_dict.update(kw)

    ##HACK For optimisation to get metadata_modified created faster.

    context['metadata_modified'] = max(result_dict.get('revision_timestamp', ''),
                                       context.get('metadata_modified', ''))

    return result_dict

