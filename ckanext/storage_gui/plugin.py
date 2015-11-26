import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import logic.action as action

log = logging.getLogger(__name__)

class StorageAdminGui(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.ITemplateHelpers, inherit=False)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IActions)
    
    def configure(self, config):
        self.max_resource_size = config.get('ckan.max_resource_size', 10)
        self.max_organization_sice = config.get('ckanext-storage-gui.organization_filestore_limit', 2)
        self.max_organization_sice = config.get('ckanext-storage-gui.organization_db_limit', 2)
        self.max_organization_sice = config.get('ckanext-storage-gui.organization_triplestore_limit', 2)

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')

    def before_map(self, map):
        map.connect('storage','/admin/storage', action='list', controller='ckanext.storage_gui.storageGUI:StorageController')
        map.connect('storage_detail','/admin/storage/detail', action='detail', controller='ckanext.storage_gui.storageGUI:StorageController')
        map.connect('organization_storage','/organization/storage/{id}', action='org_storage', controller='ckanext.storage_gui.storageGUI:StorageController')
        map.connect('organization_storage_edit','/organization/storage/edit/{id}', action='org_storage_edit', controller='ckanext.storage_gui.storageGUI:StorageController')
        map.connect('organization_storage_reset','/organization/storage/reset/{id}', action='org_storage_reset', controller='ckanext.storage_gui.storageGUI:StorageController')
        map.connect('organization_storage_dataset_reset','/organization/storage/{id}/dataset/reset/{pkg_id}', action='dataset_storage_reset', controller='ckanext.storage_gui.storageGUI:StorageController')
        map.connect('organization_storage_dataset_edit','/organization/storage/{id}/dataset/edit/{pkg_id}', action='dataset_storage_edit', controller='ckanext.storage_gui.storageGUI:StorageController')
        
        return map

    def get_helpers(self):
        return {}
    
    def get_actions(self):
        return {'package_autocomplete' : action.package_autocomplete,
                'organization_available_space' : action.organization_available_space,
                'package_resource_size_limit' : action.package_resource_size_limit}
