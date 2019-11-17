import ckanext

from ckanext.package_converter.model.metadata_format import MetadataFormats
from ckanext.package_converter.model.converter import BaseConverter
from ckanext.package_converter.model.record import Record, JSONRecord, XMLRecord
from ckanext.package_converter.model.scheming_converter import Datacite43SchemingConverter

from ckanext.scheming import helpers
import ckan.model as model
import ckan.plugins.toolkit as toolkit

import collections
from pylons import config
from xmltodict import unparse, parse
import sys
import json

from logging import getLogger
log = getLogger(__name__)

class Datacite43SchemingResourceConverter(Datacite43SchemingConverter):

    def __init__(self):
        Datacite43SchemingConverter.__init__(self)
        ckan_resource_base_format = MetadataFormats().get_metadata_formats('ckan_resource')[0]
        self.input_format = ckan_resource_base_format

    def _datacite_converter_schema(self, resource_dict):
        try:
            schema_map = self._get_schema_map(self.output_format.get_format_name())
            metadata_resource_map = schema_map['metadata_resource']
            datacite_dict = collections.OrderedDict()
            # Header
            datacite_dict['resource']=collections.OrderedDict()
            datacite_dict['resource']['@xsi:schemaLocation'] = '{namespace} {schema}'.format(namespace=self.output_format.get_namespace(),
                                                                                             schema=self.output_format.get_xsd_url())
            datacite_dict['resource']['@xmlns']='{namespace}'.format(namespace=self.output_format.get_namespace())
            datacite_dict['resource']['@xmlns:xsi']='http://www.w3.org/2001/XMLSchema-instance'

            # Identifier*
            datacite_identifier_tag = 'identifier'
            datacite_dict['resource'][datacite_identifier_tag] = {'#text': self._get_single_mapped_value(datacite_identifier_tag, resource_dict, metadata_resource_map), '@identifierType':'DOI'}

            # Titles*
            datacite_titles_tag = 'titles'
            datacite_title_tag = 'title'
            datacite_xml_lang_tag = 'xml:lang'
            datacite_dict['resource'][datacite_titles_tag] = { datacite_title_tag: [ ] }
            datacite_title_type_tag = 'titleType'
            ckan_titles = self._get_complex_mapped_value(datacite_titles_tag, datacite_title_tag, ['', datacite_title_type_tag, datacite_xml_lang_tag], resource_dict, metadata_resource_map)
            for ckan_title in ckan_titles:
                datacite_title = {'#text': ckan_title.get( datacite_title_tag, ''),
                                  '@' + datacite_xml_lang_tag: ckan_title.get( self._joinTags([datacite_title_tag, datacite_xml_lang_tag]) , 'en-us')}
                if ckan_title.get( self._joinTags([datacite_title_tag, datacite_title_type_tag]) ,''):
                    ckan_title_type =  ckan_title.get( self._joinTags([datacite_title_tag, datacite_title_type_tag]) , 'other')
                    datacite_title['@' + datacite_title_type_tag] =  self._valueToDataciteCV (ckan_title_type, datacite_title_type_tag)
                datacite_dict['resource'][datacite_titles_tag][datacite_title_tag] += [ datacite_title ]

            # Alternate Identifier (CKAN URL) Decide which is landing page, resource or package
            ckan_resource_url = config.get('ckan.site_url','') + toolkit.url_for(controller='package', action='resource_read',
                                                                             id = resource_dict.get('package_id', ''),
                                                                             resource_id = resource_dict.get('id', ''))
            datacite_dict['resource']['alternateIdentifiers']={'alternateIdentifier':[{'#text':ckan_resource_url, '@alternateIdentifierType':'URL'}]}

            # Sizes (not defined in scheming, taken from default CKAN resource)
            datacite_size_group_tag = 'sizes'
            datacite_size_tag = 'size'
            datacite_sizes = []
            
            log.debug('** SIZE *** ' + resource_dict.get('resource_size', ''))
            if resource_dict.get('size', ''):
                datacite_sizes += [{'#text': str(resource_dict.get('size', ' ')) + ' bytes'}]
            elif resource_dict.get('resource_size', ''):
                resource_size = resource_dict.get('resource_size', '')
                try:
                    resource_size_obj = json.loads(resource_size)
                    datacite_sizes += [{'#text': resource_size_obj.get('size_value' , '0') + ' ' + resource_size_obj.get('size_unit' , 'KB').upper()}]
                except:
                    log.error('unparseable value at resource_size:' + str(resource_size))

            if datacite_sizes:
                datacite_dict['resource'][datacite_size_group_tag] = {datacite_size_tag: datacite_sizes}

            # Formats (get from resources)
            datacite_format_group_tag = 'formats'
            datacite_format_tag = 'format'
            datacite_formats = []

            resource_format = self._get_single_mapped_value( self._joinTags([datacite_format_group_tag, datacite_format_tag]),
                                                           resource_dict, metadata_resource_map, 
                                                           default=resource_dict.get('mimetype', resource_dict.get('mimetype_inner', '')))
            if resource_format:
                datacite_formats += [{'#text': resource_format}]
            if datacite_formats:
                datacite_dict['resource'][datacite_format_group_tag] = {datacite_format_tag: datacite_formats}

            # Version
            datacite_version_tag = 'version'
            datacite_version = self._get_single_mapped_value(datacite_version_tag, resource_dict, metadata_resource_map, '')
            if datacite_version:
                datacite_dict['resource'][datacite_version_tag] = {'#text': datacite_version }

            # Description
            datacite_descriptions_tag = 'descriptions'
            datacite_description_tag = 'description'
            datacite_description_type_tag = 'descriptionType'
            datacite_descriptions = []
            ckan_descriptions = self._get_complex_mapped_value(datacite_descriptions_tag, datacite_description_tag, [ '', datacite_xml_lang_tag, datacite_description_type_tag], resource_dict, metadata_resource_map)
            for ckan_description in ckan_descriptions:
                datacite_description = {'#text': ckan_description.get( datacite_description_tag, ''),
                                  '@' + datacite_description_type_tag: ckan_description.get( self._joinTags([datacite_description_tag, datacite_description_type_tag]) , 'Abstract'),
                                  '@' + datacite_xml_lang_tag: ckan_description.get( self._joinTags([datacite_description_tag, datacite_xml_lang_tag]) , 'en-us')}
                datacite_descriptions += [ datacite_description ]
            if datacite_descriptions:
                datacite_dict['resource'][datacite_descriptions_tag] = { datacite_description_tag: datacite_descriptions }

            # inherit from package
            package_dict = resource_dict.get('package_dict')
            if package_dict:
                datacite_package_dict = parse(super(Datacite43SchemingResourceConverter, self)._datacite_converter_schema(package_dict))
                datacite_dict['resource'] = self._inherit_from_package(datacite_dict['resource'], datacite_package_dict['resource'])

            # Convert to xml
            converted_package = unparse(datacite_dict, pretty=True)
        except Exception as e:
            log.exception(e)
            return None
        return converted_package

    def _inherit_from_package(self, datacite_dict, datacite_package_dict):
        def merge_dict_lists(dict1, dict2):
            for key in dict1.keys():
                if type(dict1[key]) is list:
                    list1 = dict1[key]
                    list2 = dict2.get(key, [])
                    if type(dict2.get(key, [])) is not list:
                        list2 = [list2]
                    for item in list2:
                        if item not in list1:
                            dict1[key] += [item]
            return dict1

        try:
            # values from the resource are added or replace the package
            replace = ['identifier', 'sizes', 'version', 'formats', 'resourceType', 'alternateIdentifiers']
            for key in datacite_dict.keys():
                if (key in replace) or (type(datacite_dict[key]) is not dict):
                        datacite_package_dict[key] = datacite_dict[key]
                else:
                    datacite_package_dict[key] = merge_dict_lists(datacite_dict[key], datacite_package_dict.get(key,{}))
            return (datacite_package_dict)
        except Exception as e:
            log.exception(e)
            return datacite_dict
