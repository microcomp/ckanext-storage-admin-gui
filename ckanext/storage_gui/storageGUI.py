import logging

from pylons import config
import ckan.lib.base as base
import ckan.plugins.toolkit as tk
import ckan.model as model
import ckan.logic as logic
from ckan.common import _, c, request
import ckan.lib.helpers as h

from ckanext.storage_gui.model import db, resource_size

log = logging.getLogger(__name__)
NotFound = logic.NotFound
tb = 1099511627776
gb = 1073741824
mb = 1048576
kb = 1024
size_endings = [{'text' : 'KiB', 'value' : 'KiB'}, {'text' : 'MiB', 'value' : 'MiB'}, {'text' : 'GiB', 'value' : 'GiB'}, {'text' : 'TiB', 'value' : 'TiB'}]


def org_free_space_filestore(org_id):
    create_storage_stat_table()
    org_limit = resource_size.organization_get_limit(org_id, 'filestore')
    if org_limit < 0:
        org_limit = mb * config.get('ckanext-storage-gui.organization_filestore_limit', 2)
    data_dict = {'subject_id' : org_id}
    org_history = db.StorageStat.get(**data_dict)
    if org_history:
        org_current_usage = org_history[-1].filestore_usage
        if org_current_usage < org_limit:
            return org_limit - org_current_usage
    else:
        #nemame spocitany aktualny stav, vrat 1 aby islo pridat resource
        return 1

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
    def _check_access(self, user):
        context = {'user' : user}
        try:
            logic.check_access('storage_usage', context)
        except tk.NotAuthorized, e:
            log.info(e.extra_msg)
            tk.abort(401, e.extra_msg)

    def _retrieve_data_to_db(self):
        stats = tk.get_action('used_space')()
        stats_org = tk.get_action('used_space_per_org')()
        insert_storage_stat('total', stats['filesystem'], stats['database'], stats['triplestore'])
        for key, org in stats_org.iteritems():
            insert_storage_stat(key, org['filesystem'], org['database'], org['triplestore'])

    def _retrieve_config_attr(self):
        try:
            getattr(self, 'organization_filestore_limit')
        except AttributeError:
            self.organization_filestore_limit = config.get('ckanext-storage-gui.organization_filestore_limit', 2)
            self.organization_database_limit = config.get('ckanext-storage-gui.organization_database_limit', 2)
            self.organization_triplestore_limit = config.get('ckanext-storage-gui.organization_triplestore_limit', 2)
            self.max_resource_size = config.get('ckan.max_resource_size', 2)
        
    def _retrieve_org_storage_limit(self, org_id, storage_type):
        org_limit = resource_size.organization_get_limit(org_id, storage_type)
        if org_limit < 0:
            try:
                org_limit = mb * getattr(self, 'organization_' + storage_type + '_limit')
            except AttributeError:
                org_limit = 0
        return org_limit       
    
    def _get_percentage_usage(self, limit, current):
        return int(float(current)/limit*100)
    
    def _verify_config_storage_option_vs_new(self, storage_type, new_storage_size, new_storage_unit):
        if new_storage_unit == 'MiB':
            try:
                storage_size = getattr(self, 'organization_' + storage_type + '_limit')
                if storage_size == float(new_storage_size):
                    return False
                return True
            except AttributeError, e:
                log.exception(e)
        return False
    
    def _convert_to_bytes(self, size, unit):
        if unit == 'KiB':
            return size*kb
        if unit == 'MiB':
            return size*mb
        if unit == 'GiB':
            return size*gb
        if unit == 'TiB':
            return size*tb
    
    def dataset_storage_edit(self, id, pkg_id):
        self._check_access(c.user)
        self._retrieve_config_attr()
        c.endings = size_endings
        try:
            c.group_dict = tk.get_action('organization_show')(data_dict = {'id' : id})
            if request.method == 'POST':
                if request.params.get('submit', None):
                    log.info('POST request params: %s', request.params)
                    dataset = request.params.get('dataset')
                    max_resource_size = request.params.get('max_resource_size')
                    resource_unit = request.params.get('size_unit')
                    resource_size_bytes = self._convert_to_bytes(float(max_resource_size), resource_unit)
                    context = {'session' : model.Session, 'user' : c.user}
                    dataset_id = tk.get_converter('convert_package_name_or_id_to_id')(dataset, context)
                    log.info('dataset id: %s', dataset_id)
                    resource_size.package_insert_limit(dataset_id, resource_size_bytes)
                    h.flash_success(_('Configuration of dataset limit was successfull.'))
                    return tk.redirect_to('organization_storage', id=id)
            else:
                c.dataset = pkg_id if pkg_id else None
                if pkg_id:
                    dataset_id = tk.get_converter('convert_package_name_or_id_to_id')(pkg_id, {'session' : model.Session})
                    size = resource_size.package_get_limit(dataset_id)
                    if size > 0:
                        c.size, c.unit = h.localised_filesize(size).split()
                    else:
                        c.size = self.max_resource_size 
                        c.unit = 'MiB'
                
        except NotFound:
            base.abort(404, _('Organization not found'))
            
        return base.render('organization/storage_dataset_edit.html')
    
    def dataset_storage_reset(self, id, pkg_id):
        self._check_access(c.user)
        try:
            context = {'session' : model.Session, 'user' : c.user}
            dataset_id = tk.get_converter('convert_package_name_or_id_to_id')(pkg_id, context) 
            resource_size.package_delete_limit(dataset_id)
            c.group_dict = tk.get_action('organization_show')(data_dict = {'id' : id})
            h.flash_success(_("Dataset's max. resource size is set to default value."))
            return tk.redirect_to('organization_storage', id=id)
        except NotFound:
            base.abort(404, _('Organization not found'))
          
    def org_storage_reset(self, id):
        self._check_access(c.user)
        resource_size.organization_reset_limit(id)
        h.flash_success(_('Configuration reset was successfull.'))
        return tk.redirect_to('organization_storage', id=id)
    
    def org_storage_edit(self, id):
        self._check_access(c.user)
        self._retrieve_config_attr()
        c.endings = size_endings
        
        try:
            c.group_dict = tk.get_action('organization_show')(data_dict = {'id' : id})
            org_filestore_limit, org_filestore_limit_unit = h.localised_filesize(self._retrieve_org_storage_limit(id, 'filestore')).split()
            org_db_limit, org_db_limit_unit = h.localised_filesize(self._retrieve_org_storage_limit(id, 'database')).split()
            org_triplestore_limit, org_triplestore_limit_unit = h.localised_filesize(self._retrieve_org_storage_limit(id, 'triplestore')).split()
            log.info('request method: %s', request.method)
            log.info('params: %s', request.params)
            if request.method == 'POST':
                if request.params.get('submit', None):
                    log.info('POST request params: %s', request.params)
                    database_size = request.params.get('database_size')
                    database_unit = request.params.get('database_unit')
                    filestore_size = request.params.get('filestore_size')
                    filestore_unit = request.params.get('filestore_unit')
                    triplestore_size = request.params.get('triplestore_size')
                    triplestore_unit = request.params.get('triplestore_unit')
                    database_insert = self._verify_config_storage_option_vs_new('database',database_size, database_unit)
                    filestore_insert = self._verify_config_storage_option_vs_new('filestore',filestore_size, filestore_unit)
                    triplestore_insert = self._verify_config_storage_option_vs_new('triplestore',triplestore_size, triplestore_unit)
                    if database_insert:
                        resource_size.organization_insert_limit(id, 'database', self._convert_to_bytes(float(database_size), database_unit))
                    else:
                        resource_size.organization_delete_limit(id, 'database')
                    if filestore_insert:
                        resource_size.organization_insert_limit(id, 'filestore', self._convert_to_bytes(float(filestore_size), filestore_unit))
                    else:
                        log.debug('deleting organization filestore limit')
                        resource_size.organization_delete_limit(id, 'filestore')
                    if triplestore_insert:
                        resource_size.organization_insert_limit(id, 'triplestore', self._convert_to_bytes(float(triplestore_size), triplestore_unit))
                    else:
                        resource_size.organization_delete_limit(id, 'triplestore')
                    
                    log.info('before redirect')
                    h.flash_success(_('Configuration updated.'))
                    return tk.redirect_to('organization_storage', id=id)
                elif request.params.get('reset', None):
                    resource_size.organization_reset_limit(id)
                    h.flash_success(_('Configuration reset was successfull.'))
                    return tk.redirect_to('organization_storage', id=id)
                else:
                    pass
                    
                    
                
        except NotFound:
            base.abort(404, _('Organization not found'))
        return base.render('organization/storage_edit.html', extra_vars={'filestore_limit': org_filestore_limit,
                                                                         'filestore_limit_unit': org_filestore_limit_unit,
                                                                         'database_limit': org_db_limit,
                                                                         'database_limit_unit': org_db_limit_unit,
                                                                         'triplestore_limit': org_triplestore_limit,
                                                                         'triplestore_limit_unit': org_triplestore_limit_unit})
    
    def org_storage(self, id):
        self._check_access(c.user)
        self._retrieve_config_attr()
        list_org_history = []
        create_storage_stat_table()
        data_dict = {'subject_id' : id}
        org_history = db.StorageStat.get(**data_dict)
        for item in org_history:
            list_org_history.append({'filesystem' : item.filestore_usage,
                                     'database' : item.database_usage,
                                     'triplestore' : item.triplestore_usage,
                                     'time' : item.time.strftime("%H:%M:%S %d.%m.%Y")})
        
        org_filestore_limit = self._retrieve_org_storage_limit(id, 'filestore')
        org_filestore_current_usage = list_org_history[-1]['filesystem'] if list_org_history else 0
        org_filestore_percentage_usage = self._get_percentage_usage(org_filestore_limit, org_filestore_current_usage)
        org_db_limit = self._retrieve_org_storage_limit(id, 'database')
        org_db_current_usage = list_org_history[-1]['database'] if list_org_history else 0
        org_db_percentage_usage = self._get_percentage_usage(org_db_limit, org_db_current_usage)
        org_triplestore_limit = self._retrieve_org_storage_limit(id, 'triplestore')
        org_triplestore_current_usage = list_org_history[-1]['triplestore'] if list_org_history else 0
        org_triplestore_percentage_usage = self._get_percentage_usage(org_triplestore_limit, org_triplestore_current_usage)
        
        
        try:
            package_list = []
            c.group_dict = tk.get_action('organization_show')(data_dict = {'id' : id})
            log.info(c.group_dict)
            for package in c.group_dict['packages']:
                result = resource_size.package_get_limit(package['id'])
                limit = h.localised_filesize(result) if result>0 else self.max_resource_size + ' MiB'
                package_list.append((package['name'], package['title'], limit))
            c.package_list = package_list
        except NotFound:
            base.abort(404, _('Organization not found'))
        return base.render('organization/storage.html',extra_vars={'org_filestore_usage' : org_filestore_current_usage,
                                                                   'org_db_usage' : org_db_current_usage,
                                                                   'org_triplestore_usage' : org_triplestore_current_usage,
                                                                   'org_filestore_limit' : org_filestore_limit,
                                                                   'org_db_limit' : org_db_limit,
                                                                   'org_triplestore_limit' : org_triplestore_limit,
                                                                   'org_filestore_percentage_usage' : org_filestore_percentage_usage,
                                                                   'org_db_percentage_usage' : org_db_percentage_usage,
                                                                   'org_triplestore_percentage_usage' : org_triplestore_percentage_usage})

    def detail(self):
        self._check_access(c.user)
        self._retrieve_config_attr()
        org_id = base.request.params.get('org', None)
        log.info("selected org: %s", org_id)
        try:
            org_info = tk.get_action('organization_show')(data_dict = {'id' : org_id})
        except tk.ObjectNotFound: 
            log.info('organization not found')
            base.abort(404, tk._('Organization not found'))
        organization_name = org_info['display_name']
        list_org_history = []
        create_storage_stat_table()
        data_dict = {'subject_id' : org_id}
        list_of_orgs = tk.get_action('organization_list')(data_dict = {'all_fields': True})
        orgs = [(item['display_name'], item['id'])for item in list_of_orgs]
        org_history = db.StorageStat.get(**data_dict)
        for item in org_history:
            list_org_history.append({'filesystem' : item.filestore_usage,
                                     'database' : item.database_usage,
                                     'triplestore' : item.triplestore_usage,
                                     'time' : item.time.strftime("%H:%M:%S %d.%m.%Y")})
        
        org_filestore_limit = self._retrieve_org_storage_limit(org_id, 'filestore')
        org_filestore_percentage_usage = self._get_percentage_usage(org_filestore_limit, list_org_history[-1]['filesystem'])
        org_db_limit = self._retrieve_org_storage_limit(org_id, 'database')
        org_db_percentage_usage = self._get_percentage_usage(org_db_limit, list_org_history[-1]['database'])
        org_triplestore_limit = self._retrieve_org_storage_limit(org_id, 'triplestore')
        org_triplestore_percentage_usage = self._get_percentage_usage(org_triplestore_limit, list_org_history[-1]['triplestore'])

        return base.render('storage/detail.html',extra_vars={'org_name' : organization_name,
                                                             'org_history' : list_org_history,
                                                             'org_selected' : org_id,
                                                             'org_filestore_limit' : org_filestore_limit,
                                                             'org_db_limit' : org_db_limit,
                                                             'org_triplestore_limit' : org_triplestore_limit,
                                                             'org_filestore_percentage_usage' : org_filestore_percentage_usage,
                                                             'org_db_percentage_usage' : org_db_percentage_usage,
                                                             'org_triplestore_percentage_usage' : org_triplestore_percentage_usage,
                                                             'orgs' : orgs})

    def list(self):
        self._check_access(c.user)
        self._retrieve_config_attr()
        context = {'user' : c.user}
        try:
            logic.check_access('storage_usage', context)
        except tk.NotAuthorized, e:
            log.info(e.extra_msg)
            tk.abort(401, e.extra_msg)
            
        list_of_orgs = tk.get_action('organization_list')(data_dict = {'all_fields': True})
        orgs = [(item['display_name'], item['id'])for item in list_of_orgs]

        org = base.request.params.get('org', None)
        if org:
            log.info('org filter: %s', org)
            
        update = base.request.params.get('refresh', None)
        log.info('refresh value: %s', update)
        log.info('refresh value type: %s', type(update))
        if update and update==u'1':
            log.info('storage stat data will be updated')
            self._retrieve_data_to_db()

        check = db.table_exists('ckanext_storage_stat', model).first()
        if not check['exists']:
            log.info('ckanext_storage_stat table does not exist.')
            return base.render('storage/index.html',extra_vars={'org_selected' : org,
                                                            'stats_org' : [],
                                                            'orgs' : orgs})
        
        if db.storage_stat_table is None:
            db.init_db(model)    
        
        filtered_content = []
        total_filestore_usage = None
        total_database_usage = None
        total_triplestore_usage = None
        last_update_time = None
        
        list_of_orgs = tk.get_action('organization_list')(data_dict = {'all_fields': True})
        orgs = [(item['display_name'], item['id'])for item in list_of_orgs]
        
        result = db.retrieve_actual_usage(model)
        for res in result:
            if res['subject_id']=='total':
                total_filestore_usage = res['filestore_usage']
                total_database_usage = res['database_usage']
                total_triplestore_usage = res['triplestore_usage']
                last_update_time = res['time'].strftime("%H:%M:%S %d.%m.%Y")
            else:
                org_id = res['subject_id']
                org_url = tk.url_for(controller='ckanext.storage_gui.storageGUI:StorageController', action='org_storage',
                    id=org_id)
                try:
                    org_info = tk.get_action('organization_show')(data_dict = {'id': org_id,
                                                                               'include_datasets': False})

                    org_filestore_limit = self._retrieve_org_storage_limit(org_id, 'filestore')
                    org_filestore_percentage_usage = self._get_percentage_usage(org_filestore_limit, res['filestore_usage'])
                    org_db_limit = self._retrieve_org_storage_limit(org_id, 'database')
                    org_db_percentage_usage = self._get_percentage_usage(org_db_limit, res['database_usage'])
                    org_triplestore_limit = self._retrieve_org_storage_limit(org_id, 'triplestore')
                    org_triplestore_percentage_usage = self._get_percentage_usage(org_triplestore_limit, res['triplestore_usage'])

                    filtered_content.append({'title' : org_info['display_name'],
                                             'url' : org_url,
                                             'filesystem' : res['filestore_usage'],
                                             'filesystem_perc' : org_filestore_percentage_usage,
                                             'database' : res['database_usage'],
                                             'database_perc' : org_db_percentage_usage,
                                             'triplestore' : res['triplestore_usage'],
                                             'triplestore_perc' : org_triplestore_percentage_usage})
                except logic.NotFound as e:
                    log.exception(e)
        
        return base.render('storage/index.html',extra_vars={'org_selected' : org,
                                                            'update_time' : last_update_time,
                                                            'stats_org' : filtered_content,
                                                            'filesystem' : total_filestore_usage,
                                                            'database' : total_database_usage,
                                                            'triplestore' : total_triplestore_usage,
                                                            'orgs' : orgs})
        
        