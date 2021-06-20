import ckan.model as model
import ckan.plugins.toolkit as toolkit

from logging import getLogger

from flask import Blueprint, make_response

log = getLogger(__name__)


def get_blueprints(name, module):
    # Create Blueprint for plugin
    blueprint = Blueprint(name, module)

    blueprint.add_url_rule(
        u"/dataset/<package_id>/export/<file_format>.<extension>",
        u"package_export",
        package_export
    )

    blueprint.add_url_rule(
        u"/dataset/<package_id>/resource/<resource_id>/export/<file_format>.<extension>",
        u"resource_export",
        resource_export
    )

    return blueprint


# class PackageExportController(toolkit.BaseController):

def package_export(package_id, file_format='', extension='xml'):
    """Return the given dataset as a converted file.
    """
    converted_package = None

    context = {
        'model': model,
        'session': model.Session,
        'user': toolkit.g.user
    }

    content_type = 'text / plain'
    if extension == 'xml':
        content_type = 'application/xml'
    elif extension == 'json':
        content_type = 'application/json'

    headers = {u'Content-Disposition': 'attachment; filename=' + package_id + '_' + file_format + '.' + extension,
               u'Content-Type': content_type}

    try:
        converted_package = toolkit.get_action(
            'package_export')(
            context,
            {'id': package_id, 'format': file_format}
        )
    except toolkit.ObjectNotFound:
        toolkit.abort(404, 'Dataset not found')

    return make_response(converted_package, 200, headers)


def resource_export(resource_id, package_id='', file_format='', extension='xml'):
    """Return the given dataset as a converted file.
    """

    converted_resource = None

    context = {
        'model': model,
        'session': model.Session,
        'user': toolkit.g.user
    }

    content_type = 'text / plain'
    if extension == 'xml':
        content_type = 'application/xml'
    elif extension == 'json':
        content_type = 'application/json'

    headers = {u'Content-Disposition': 'attachment; filename=' + resource_id + '_' + file_format + '.' + extension,
               u'Content-Type': content_type}

    try:
        converted_resource = toolkit.get_action(
            'resource_export')(
            context,
            {'id': resource_id, 'format': file_format}
        )
    except toolkit.ObjectNotFound:
        toolkit.abort(404, 'Dataset/Resource not found')

    return make_response(converted_resource, 200, headers)
