import ckan.model as model
import ckan.plugins.toolkit as toolkit

from logging import getLogger

log = getLogger(__name__)

class PackageExportController(toolkit.BaseController):

    def package_export(self, package_id, format=None, extension=None):
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
        r.content_disposition = 'attachment; filename=package_export.xml'.format(
            package_id)
        r.content_type = 'application/xml'
        converted_package = '<?xml version="1.0" encoding="utf-8"?> <resource><identifier identifierType="DOI">' + package_id  + '</identifier></resource>'

#        try:
#            datapackage_dict = toolkit.get_action(
#                'package_show_as_datapackage')(
#                context,
#                {'id': package_id}
#            )
#        except toolkit.ObjectNotFound:
#            toolkit.abort(404, 'Dataset not found')

        return converted_package

