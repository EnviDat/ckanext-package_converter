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

    # find output format object by name
    r = toolkit.response
    r.content_type = 'text/html'

    output_format_name = data_dict.get('format', '').lower()

    converted_record = package_export_as_record(package_id, output_format_name, context)
    try:
        r.content_type = converted_record.get_metadata_format().get_mimetype()
        converted_package_content = converted_record.get_content()
        return(converted_package_content)
    except:
        return(str(converted_record))

def package_export_as_record(package_id, output_format_name, context = {}):

    dataset_dict = toolkit.get_action('package_show')(context,
                                                      {'id': package_id})
    matching_metadata_formats = MetadataFormats().get_metadata_formats(output_format_name)
    if not matching_metadata_formats:
        return ('Metadata format unknown {output_format_name}'.format(output_format_name=output_format_name))
    output_format = matching_metadata_formats[0]

    # get dataset as record
    ckan_format = MetadataFormats().get_metadata_formats('ckan')[0]
    dataset_record = JSONRecord(ckan_format, dataset_dict)

    # convert
    try:
        converted_record = Converters().get_conversion(dataset_record, output_format)
        if converted_record:
            return(converted_record)
        else:
            raise #Exception('Cannot convert')
    except:
        return ('No converter available for format {0}'.format( output_format_name))

