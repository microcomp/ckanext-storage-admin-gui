import logging
import ckan.lib.base as base
import ckan.plugins.toolkit as tk
from hurry.filesize import size

log = logging.getLogger(__name__)

class StorageController(base.BaseController):
    def list(self):
        stats = tk.get_action('used_space')()
        stats_org = tk.get_action('used_space_per_org')()
        filtered_content = []
        log.info('type: %s',type(stats_org))
        log.info('keys: %s',stats_org.keys())
        for key, org in stats_org.iteritems():
            log.info(key)
            log.info(org['filesystem'])
            log.info(org['database'])
        org = base.request.params.get('org', None)
        if org:
            log.info('org filter: %s', org)
        return base.render('storage/index.html',extra_vars={'org_selected' : org,
                                                            'stats_org' : filtered_content,
                                                             'filesystem' : size(stats['filesystem']),
                                                              'database' : size(stats['database'])})