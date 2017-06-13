import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

import  ckanext.package_converter.logic

from ckanext.package_converter.model.converter import Converters

from logging import getLogger
log = getLogger(__name__)

DEAFULT_BASE_CONVERTER = 'ckanext.package_converter.model.scheming_converter.Datacite31SchemingConverter'
DEAFULT_RESOURCE_BASE_CONVERTER = 'ckanext.package_converter.model.scheming_resource_converter.Datacite31SchemingResourceConverter'

class Package_ConverterPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IRoutes, inherit=True)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'package_converter')
        # Add custom converters
        custom_converters = config_.get('package_converter.converters', DEAFULT_BASE_CONVERTER).split()
        custom_converters += config_.get('package_converter.resource_converters', DEAFULT_RESOURCE_BASE_CONVERTER).split()
        for custom_converter in custom_converters:
            Converters().add_converter_by_name(custom_converter)

    # IRoutes
    def before_map(self, map_):
        map_.connect(
            'package_export',
            '/dataset/{package_id}/export/{file_format}.{extension}',
            controller='ckanext.package_converter.controller:PackageExportController',
            action = 'package_export'
        )
        map_.connect(
            'resource_export',
            '/dataset/{package_id}/resource/{resource_id}/export/{file_format}.{extension}',
            controller='ckanext.package_converter.controller:PackageExportController',
            action = 'resource_export'
        )
        return map_


    # IActions
    def get_actions(self):
        return {
            'package_export':
                ckanext.package_converter.logic.package_export,
            'resource_export':
                ckanext.package_converter.logic.resource_export,
             }

