import ckan.model as model
import ckan.plugins.toolkit as toolkit

from logging import getLogger

log = getLogger(__name__)

class PackageExportController(toolkit.BaseController):

    def package_export(self, package_id, format='', extension='xml'):
        '''Return the given dataset as a converted file.
        '''
        log.debug('****************** PackageExportController *********')
        log.debug(package_id)
        log.debug(format)
        log.debug(extension)
        
        context = {
            'model': model,
            'session': model.Session,
            'user': toolkit.c.user,
        }
        r = toolkit.response
        r.content_disposition = 'attachment; filename=' + package_id + '_' + format + '.' + extension
        r.content_type = 'application/xml'

        try:
            converted_package = toolkit.get_action(
                'package_export')(
                context,
                {'id': package_id, 'format':format}
            )
        except toolkit.ObjectNotFound:
            toolkit.abort(404, 'Dataset not found')

        return converted_package

