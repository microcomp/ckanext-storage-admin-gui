import logging

from pylons import config
import sqlalchemy
import ckan.logic as logic
import ckan.model as model
import ckan.lib.uploader as uploader
from ckanext.storage_gui.storageGUI import org_free_space_filestore
from ckanext.storage_gui.model.resource_size import package_get_limit

_or_ = sqlalchemy.or_
log = logging.getLogger(__name__)
NotFound = logic.NotFound
ValidationError = logic.ValidationError
_get_or_bust = logic.get_or_bust

mb = 1048576

@logic.side_effect_free
def package_autocomplete(context, data_dict):
    '''Return a list of datasets (packages) that match a string.

    Datasets with names or titles that contain the query string will be
    returned.

    :param q: the string to search for
    :type q: string
    :param limit: the maximum number of resource formats to return (optional,
        default: 10)
    :type limit: int

    :rtype: list of dictionaries

    '''
    model = context['model']
    
    log.info('package_autocomplete call')
    logic.check_access('package_autocomplete', context, data_dict)

    limit = data_dict.get('limit', 10)
    q = data_dict['q']
    owner_org = data_dict.get('owner_org')

    like_q = u"%s%%" % q

    query = model.Session.query(model.PackageRevision)
    query = query.filter(model.PackageRevision.state == 'active')
    #query = query.filter(model.PackageRevision.private == False)
    query = query.filter(model.PackageRevision.current == True)
    if owner_org:
        logging.info('got owner org:"%s', owner_org)
        query = query.filter(model.PackageRevision.owner_org == owner_org)
    query = query.filter(_or_(model.PackageRevision.name.ilike(like_q),
                                model.PackageRevision.title.ilike(like_q)))
    query = query.limit(limit)

    q_lower = q.lower()
    pkg_list = []
    for package in query:
        if package.name.startswith(q_lower):
            match_field = 'name'
            match_displayed = package.name
        else:
            match_field = 'title'
            match_displayed = '%s (%s)' % (package.title, package.name)
        result_dict = {'name':package.name, 'title':package.title,
                       'match_field':match_field, 'match_displayed':match_displayed}
        pkg_list.append(result_dict)
    
    log.info('custom autocomplete result: %s', pkg_list)
    resultSet = {'ResultSet': {'Result': pkg_list}}
    log.info(resultSet)
    return pkg_list

def organization_available_space(context, data_dict):
    id = _get_or_bust(data_dict, 'id')
    group = model.Group.get(id)
    context["group"] = group
    if group is None:
        raise NotFound('Group was not found.')
    free_space = org_free_space_filestore(id)
    log.debug('org free space: %s', free_space)
    if free_space > 0:
        return True
    return False

def package_resource_size_limit(context, data_dict):
    id = _get_or_bust(data_dict, 'id')
    pkg = model.Package.get(id)
    if pkg is None:
        raise NotFound('Package was not found.')
    limit = package_get_limit(pkg.id)
    limit = limit/mb if limit > 0 else uploader.get_max_resource_size()
    log.info('limit in MiB: %s', limit)
    return limit
    
    
