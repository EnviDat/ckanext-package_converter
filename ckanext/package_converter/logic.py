import sys
import ckan.plugins.toolkit as toolkit
from xmltodict import unparse
from pylons import config
import xml.dom.minidom as minidom

import json

from ckanext.scheming import helpers
import ckan.model as model

from ckanext.package_converter.model.metadata_format import MetadataFormats
from ckanext.package_converter.model.converter import Converters
from ckanext.package_converter.model.record import JSONRecord

from logging import getLogger

log = getLogger(__name__)


# CONSTANT TAGS (TODO: put in separate file)
FIELD_NAME = 'field_name'


@toolkit.side_effect_free
def package_export(context, data_dict):
    '''Return the given CKAN converted to a format.

    :param id: the ID of the dataset
    :type id: string
    :format id: string

    :param format: the output format name
    :type format: string
    :format format: string

    :returns: the package metadata
    :rtype: string
    '''

    try:
        package_id = data_dict['id']
    except KeyError:
        raise toolkit.ValidationError({'id': 'missing id'})

    dataset_dict = toolkit.get_action('package_show')(context,
                                                      {'id': package_id})
        
    # find output format object by name
    output_format_name = data_dict.get('format', '').lower()
    matching_metadata_formats = MetadataFormats().get_metadata_formats(output_format_name)
    log.debug('FORMATS matching "' + output_format_name + '": '+ repr(matching_metadata_formats))
    if not matching_metadata_formats:
        return ('Metadata format unknown {output_format_name}'.format(output_format_name=output_format_name))
    output_format = matching_metadata_formats[0]

    # get dataset as record
    ckan_format = MetadataFormats().get_metadata_formats('ckan')[0]
    dataset_record = JSONRecord(ckan_format, dataset_dict)
    # convert
    #try:
    converted_package_record = Converters().get_conversion(dataset_record, output_format)
    converted_package_content = converted_package_record.get_content()
    #except:
    #     converted_package_content = 'No converter available for format ' + output_format_name

    return converted_package_content


