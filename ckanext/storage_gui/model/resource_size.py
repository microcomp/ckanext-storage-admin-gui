import logging
import uuid

from sqlalchemy.sql.expression import or_, and_
from sqlalchemy import types, Column, Table, ForeignKey, func, CheckConstraint, exc, UniqueConstraint
import vdm.sqlalchemy
from ckan.model import domain_object
from ckan.model.meta import metadata, Session, mapper
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

log = logging.getLogger(__name__)

def make_uuid():
    return unicode(uuid.uuid4())

organization_limit_table = Table('ckanext_storage_admin_gui_org_limits', metadata,
                        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
                        Column('organization_id', types.UnicodeText, nullable=False),
                        Column('storage_type', types.UnicodeText, default='filestore'),
                        Column('storage_limit', types.BigInteger, CheckConstraint('storage_limit>=0'), default=0),
                        UniqueConstraint('organization_id', 'storage_type', name='ui_org_type'),
                        CheckConstraint("storage_type IN ('filestore', 'database','triplestore')")
                        )

package_limit_table = Table('ckanext_storage_admin_gui_package_limits', metadata,
                        Column('package_id', types.UnicodeText, primary_key=True),
                        Column('storage_limit', types.BigInteger, CheckConstraint('storage_limit>=0'), default=0)
                        )

class OrganizationLimit(domain_object.DomainObject):
    def __init__(self, organization_id, storage_type='filestore', storage_limit=0):
        self.organization_id = organization_id
        self.storage_type = storage_type
        self.storage_limit = storage_limit
    @classmethod
    def get(cls, **kw):
        '''Finds a single entity in the register.'''
        query = Session.query(cls).autoflush(False)
        return query.filter_by(**kw).all()
    @classmethod
    def getLimit(cls, org_id, storage_type):
        '''Finds a single entity in the register.'''
        query = Session.query(cls).autoflush(False)
        return query.filter_by(organization_id=org_id).filter_by(storage_type=storage_type).first()
    @classmethod
    def getAll(cls, **kw):
        query = Session.query(cls).autoflush(False)
        query = query.order_by(cls.name).filter(cls.name != '')
        return query.all()
    @classmethod
    def delete(cls, **kw):
        query = Session.query(cls).autoflush(False).filter_by(**kw).all()
        log.info(len(query))
        for i in query:
            log.info(i)
            Session.delete(i)
        Session.commit()
        return
    
class PackageLimit(domain_object.DomainObject):
    def __init__(self, package_id, storage_limit=0):
        self.package_id = package_id
        self.storage_limit = storage_limit
        
    @classmethod
    def get(cls, **kw):
        '''Finds a single entity in the register.'''
        query = Session.query(cls).autoflush(False)
        return query.filter_by(**kw).all()
    
    @classmethod
    def getLimit(cls, pkg_id):
        '''Finds a single entity in the register.'''
        query = Session.query(cls).autoflush(False)
        return query.filter_by(package_id=pkg_id).first()
    
    @classmethod
    def getAll(cls, **kw):
        query = Session.query(cls).autoflush(False)
        query = query.order_by(cls.name).filter(cls.name != '')
        return query.all()
    
    @classmethod
    def getAllOrg(cls, org_id):
        query = Session.query(cls).autoflush(False)
        return query.filter_by(owner_org=org_id).all()
        
    @classmethod
    def delete(cls, **kw):
        query = Session.query(cls).autoflush(False).filter_by(**kw).all()
        for i in query:
            Session.delete(i)
        Session.commit()
        return

mapper(OrganizationLimit, organization_limit_table)
mapper(PackageLimit, package_limit_table)

def db_operation_decorator(fun):

    def create_organization_limit_table():
        if not organization_limit_table.exists():
            organization_limit_table.create()

    def create_package_limit_table():
        if not package_limit_table.exists():
            package_limit_table.create()

    def func_wrapper(*args, **kwargs):
        create_organization_limit_table()
        create_package_limit_table()
        return fun(*args, **kwargs)
    
    return func_wrapper

@db_operation_decorator
def organization_insert_limit(org_id, storage_type, limit):
    search = {'organization_id' : org_id, 'storage_type' : storage_type}
    result = OrganizationLimit.get(**search)
    if result:
        result[0].storage_limit = limit
        result[0].save()
    else:
        newEntry = OrganizationLimit(org_id, storage_type, limit)
        newEntry.save()

@db_operation_decorator
def package_insert_limit(pkg_id, limit):
    search = {'package_id' : pkg_id}
    result = PackageLimit.get(**search)
    if result:
        result[0].storage_limit = limit
        result[0].save()
    else:
        newEntry = PackageLimit(pkg_id, limit)
        newEntry.save()

@db_operation_decorator
def organization_delete_limit(org_id, storage_type):
    search = {'organization_id' : org_id, 'storage_type' : storage_type}
    OrganizationLimit.delete(**search)
    
@db_operation_decorator
def organization_reset_limit(org_id):
    search = {'organization_id' : org_id}
    OrganizationLimit.delete(**search)

@db_operation_decorator
def organization_get_limit(org_id, storage_type = 'filestore'):
    result = OrganizationLimit.getLimit(org_id, storage_type)
    if result:
        return result.storage_limit
    return -1

@db_operation_decorator
def package_get_limit(pkg_id):
    result = PackageLimit.getLimit(pkg_id)
    if result:
        return result.storage_limit
    return -1

@db_operation_decorator
def package_delete_limit(pkg_id):
    search = {'package_id' : pkg_id}
    PackageLimit.delete(**search)

@db_operation_decorator
def organization_get_package_limits(owner_org):
    result = PackageLimit.getAllOrg(owner_org)
    return result

