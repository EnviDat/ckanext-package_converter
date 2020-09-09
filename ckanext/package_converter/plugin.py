import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import json
import ckanext.package_converter.logic

from ckanext.package_converter.model.converter import Converters

from logging import getLogger

import ckanext.package_converter.blueprints as blueprints

log = getLogger(__name__)

DEAFULT_BASE_CONVERTER = 'ckanext.package_converter.model.scheming_converter.Datacite43SchemingConverter'
DEAFULT_RESOURCE_BASE_CONVERTER = 'ckanext.package_converter.model.scheming_resource_converter.Datacite43SchemingResourceConverter'


class Package_ConverterPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    # plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.ITemplateHelpers, inherit=True)
    plugins.implements(plugins.IBlueprint, inherit=True)

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')


        # Add custom converters
        custom_converters = config_.get('package_converter.converters', DEAFULT_BASE_CONVERTER).split()
        custom_converters += config_.get('package_converter.resource_converters',
                                         DEAFULT_RESOURCE_BASE_CONVERTER).split()
        for custom_converter in custom_converters:
            Converters().add_converter_by_name(custom_converter)

    # # IRoutes
    # def before_map(self, map_):
    #     map_.connect(
    #         'package_export',
    #         '/dataset/{package_id}/export/{file_format}.{extension}',
    #         controller='ckanext.package_converter.controller:PackageExportController',
    #         action='package_export'
    #     )
    #     map_.connect(
    #         'resource_export',
    #         '/dataset/{package_id}/resource/{resource_id}/export/{file_format}.{extension}',
    #         controller='ckanext.package_converter.controller:PackageExportController',
    #         action='resource_export'
    #     )
    #     return map_

    # IActions
    def get_actions(self):
        return {
            'package_export':
                ckanext.package_converter.logic.package_export,
            'resource_export':
                ckanext.package_converter.logic.resource_export,
        }

    def get_helpers(self):
        return {'package_converter_readme_link': self.package_converter_readme_link,
                'package_converter_schemaorg_json': self.package_converter_schemaorg_json}

    def package_converter_readme_link(self, package_dict):
        for resource in package_dict.get('resources', []):
            if resource['name'] == 'README.txt':
                return resource.get('url', None)
        return None

    def package_converter_schemaorg_json(self, package_id):
        converted_package = {}
        if package_id:
            try:
                converted_package = toolkit.get_action(
                    'package_export')(
                    {'as_dict': True}, {'id': package_id, 'format': 'schemaorg'})
            except toolkit.ObjectNotFound:
                toolkit.abort(404, 'Dataset not found')
            return json.dumps(converted_package, indent=4, ensure_ascii=False)
        else:
            return ''

    # IBlueprint
    def get_blueprint(self):
        return blueprints.get_blueprints(self.name, self.__module__)
