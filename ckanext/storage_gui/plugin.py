import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import logging


log = logging.getLogger(__name__)
class StorageAdminGui(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.ITemplateHelpers, inherit=False)
    
    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        
    def before_map(self, map):
        map.connect('storage','/storage', action='list', controller='ckanext.storage_gui.storageGUI:StorageController')
        map.connect('storage_detail','/storage/detail', action='detail', controller='ckanext.storage_gui.storageGUI:StorageController')
        return map
    
    def get_helpers(self):
        return {}