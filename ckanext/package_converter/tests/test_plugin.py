"""Tests for plugin.py."""
import ckanext.package_converter.plugin as plugin
from ckanext.package_converter.model.metadata_format import MetadataFormats, MetadataFormat, FormatType
from ckanext.package_converter.model.converter import Converters
from ckanext.package_converter.model.record import JSONRecord

import ckan.plugins
import ckan.model as model

import ckan.tests.factories as factories

from nose.tools import assert_raises
from nose.tools import assert_equal, assert_true

import pylons.config as config
import webtest
from routes import url_for as url_for

from logging import getLogger
log = getLogger(__name__)


class TestPackageConverter(object):
    '''Tests for the ckanext.package_converter.plugin module.

    Specifically tests the conversion of datasets.
    '''
    def _get_test_app(self):

        # Return a test app with the custom config.
        app = ckan.config.middleware.make_app(config['global_conf'], **config)
        app = webtest.TestApp(app)

        ckan.plugins.load('package_converter')
        return app

    @classmethod
    def setup_class(cls):
        '''Nose runs this method once to setup our test class.'''
        # Test code should use CKAN's plugins.load() function to load plugins
        # to be tested.
        ckan.plugins.load('package_converter')

    def teardown(self):
        '''Nose runs this method after each test method in our test class.'''
        # Rebuild CKAN's database after each test method, so that each test
        # method runs with a clean slate.
        model.repo.rebuild_db()

    @classmethod
    def teardown_class(cls):
        '''Nose runs this method once after all the test methods in our class
        have been run.

        '''
        # We have to unload the plugin we loaded, so it doesn't affect any
        # tests that run after ours.
        ckan.plugins.unload('package_converter')

    def test_add_metadata_format(self):
        test_format = MetadataFormat('test', '1.0', format_type=FormatType.TEXT,
                                     description='format for testing purposes')
        MetadataFormats().add_metadata_format(test_format, replace=True)
        assert_true(MetadataFormats().get_metadata_formats('test')[0] == test_format)

    def test_get_metadata_formats(self):
        formats_dict = MetadataFormats().get_metadata_formats_dict()
        assert_true(len(formats_dict)>0)

    def test_add_converter_by_name(self):
        custom_converter_name = 'ckanext.package_converter.custom.custom_converter.CustomConverter'
        Converters().add_converter_by_name(custom_converter_name)

    def test_get_converter(self):
        custom_converter_list = Converters().get_all_converters()
        assert_true(len(custom_converter_list)>=1)

    def test_convert(self):
        package_dict = factories.Dataset(name='dataset_test_convert')
        ckan_metadata_format = MetadataFormats().get_metadata_formats('ckan')[0]
        record = JSONRecord(ckan_metadata_format,package_dict)
        custom_metadata_format = MetadataFormats().get_metadata_formats('custom')[0]
        coverted_record = Converters().get_conversion(record, custom_metadata_format)
        log.debug(coverted_record)
        assert_true(coverted_record.get_metadata_format() == custom_metadata_format)

    def test_api_export(self):
        app = self._get_test_app()
        dataset = factories.Dataset(name='dataset_test_api_export')
        response = app.get(
            url=url_for(controller='package', action='package_export', id=dataset['name'], file_format='custom', extension='txt')
        )
