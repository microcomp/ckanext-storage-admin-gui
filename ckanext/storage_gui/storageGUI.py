import logging
import db
import ckan.lib.base as base
import ckan.plugins.toolkit as tk
import ckan.model as model
from hurry.filesize import size

log = logging.getLogger(__name__)

def create_storage_stat_table():
    if db.storage_stat_table is None:
        log.info("table ckanext_storage_stat init")
        db.init_db(model)

def insert_storage_stat(subject_id, filestore, database, triplestore):
    create_storage_stat_table()
    entry = db.StorageStat()
    entry.subject_id = subject_id
    entry.filestore_usage = filestore
    entry.database_usage = database
    entry.triplestore_usage = triplestore
    entry.save()
    session = model.Session
    session.add(entry)
    session.commit()

class StorageController(base.BaseController):
    def _retrieve_data_to_db(self):
        stats = tk.get_action('used_space')()
        stats_org = tk.get_action('used_space_per_org')()
        insert_storage_stat('total', stats['filesystem'], stats['database'], stats['triplestore'])
        for key, org in stats_org.iteritems():
            insert_storage_stat(key, org['filesystem'], org['database'], org['triplestore'])
            
    def detail(self, org_id):
        org_info = tk.get_action('organization_show')(data_dict = {'id' : org_id})
        organization_name = org_info['display_name']
        
        list_org_history = []
        create_storage_stat_table()
        data_dict = {'subject_id' : org_id}
        org_history = db.StorageStat.get(**data_dict)
        for item in org_history:
            list_org_history.append({'filesystem' : item.filestore_usage,
                                     'database' : item.database_usage,
                                     'triplestore' : item.triplestore_usage,
                                     'time' : item.time})
        
        
        
    def list(self):
        check = db.table_exists('ckanext_storage_stat', model).first()
        if not check['exists']:
            log.info('creating ckanext_storage_stat table and filling in')
            #db.init_db(model)
            #stats = tk.get_action('used_space')()
            #stats_org = tk.get_action('used_space_per_org')()
            #insert_storage_stat('total', stats['filesystem'], stats['database'], stats['triplestore'])
            #for key, org in stats_org.iteritems():
            #    insert_storage_stat(key, org['filesystem'], org['database'], org['triplestore'])
            self._retrieve_data_to_db()
        
        update = base.request.params.get('refresh', None)
        log.info('refresh value: %s', update)
        log.info('refresh value type: %s', type(update))
        if update and update==u'1':
            log.info('storage stat data will be updated')
            self._retrieve_data_to_db()
        
        if db.storage_stat_table is None:
            db.init_db(model)    
        
        filtered_content = []
        total_filestore_usage = None
        total_database_usage = None
        total_triplestore_usage = None
        last_update_time = None
        
        result = db.retrieve_actual_usage(model)
        for res in result:
            if res['subject_id']=='total':
                total_filestore_usage = size(res['filestore_usage'])
                total_database_usage = size(res['database_usage'])
                total_triplestore_usage = size(res['triplestore_usage'])
                last_update_time = res['time']
            else:
                org_info = tk.get_action('organization_show')(data_dict = {'id':res['subject_id']})
                filtered_content.append({'title' : org_info['display_name'],
                                         'filesystem' : size(res['filestore_usage']),
                                         'database' : size(res['database_usage']),
                                         'triplestore' : size(res['triplestore_usage'])})
        #results = db.StorageStat.get()
        #for result in results:
        #    if result.subject_id=='total':
        #        total_filestore_usage = size(result.filestore_usage)
        #        total_database_usage = size(result.database_usage)
        #        total_triplestore_usage = size(result.triplestore_usage)
        #        last_update_time = result.time
        #    else:
        #        org_info = tk.get_action('organization_show')(data_dict = {'id':result.subject_id})
        #        filtered_content.append({'title' : org_info['display_name'],
        #                                 'filesystem' : size(result.filestore_usage),
        #                                 'database' : size(result.database_usage),
        #                                 'triplestore' : size(result.triplestore_usage)})
                
        org = base.request.params.get('org', None)
        if org:
            log.info('org filter: %s', org)
        
        return base.render('storage/index.html',extra_vars={'org_selected' : org,
                                                            'update_time' : last_update_time,
                                                            'stats_org' : filtered_content,
                                                            'filesystem' : total_filestore_usage,
                                                            'database' : total_database_usage,
                                                            'triplestore' : total_triplestore_usage})
        
        