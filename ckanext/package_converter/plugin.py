import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


class Package_ConverterPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IRoutes, inherit=True)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'package_converter')

    # IRoutes

    def before_map(self, map_):
        map_.connect(
            'package_export',
            '/dataset/{package_id}/export/{format}.{extension}',
            controller='ckanext.package_converter.controller:PackageExportController',
            action = 'package_export'
        )
        return map_

    # IActions

    def get_actions(self):
        return {
            #'package_create_from_datapackage':
            #    ckanext.datapackager.logic.action.create.package_create_from_datapackage,
             }
