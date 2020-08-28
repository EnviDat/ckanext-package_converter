import traceback
import ckan.plugins.toolkit as toolkit

from ckanext.package_converter.model.metadata_format import MetadataFormats, FormatType
from ckanext.package_converter.model.converter import Converters
from ckanext.package_converter.model.record import JSONRecord

from logging import getLogger

log = getLogger(__name__)


@toolkit.side_effect_free
def package_export(context, data_dict):
    """Return the given CKAN converted to a format.

    :param id: the ID of the dataset
    :type id: string
    :format id: string

    :param format: the output format name
    :type format: string
    :format format: string

    :returns: the package metadata
    :rtype: string
    """

    log.debug("Action package_export: Converting " + str(data_dict))
    result = _export(data_dict, context, type='package')
    return result


@toolkit.side_effect_free
def resource_export(context, data_dict):
    """Return the given CKAN converted to a format.

    :param id: the ID of the resource
    :type id: string
    :format id: string

    :param format: the output format name
    :type format: string
    :format format: string

    :returns: the package metadata
    :rtype: string
    """

    return _export(data_dict, context, type='resource')


def _export(data_dict, context, type='package'):
    try:
        id = data_dict['id']
    except KeyError:
        raise toolkit.ValidationError({'id': 'missing id'})

    try:
        output_format_name = data_dict['format'].lower()
    except KeyError:
        raise toolkit.ValidationError({'format': 'missing format'})

    # find output format object by name
    try:
        r = toolkit.response
        r.content_type = 'text/html'
    except:
        log.debug("No response object")
        r = False

    converted_record = export_as_record(id, output_format_name, context, type)
    try:
        if r and not context.get('as_dict', False):
            log.debug("there is a response object")
            r.content_type = converted_record.get_metadata_format().get_mimetype()
        else:
            # called as action
            if converted_record.get_metadata_format().get_format_type() == FormatType.JSON:
                log.debug("JSON format, returning dict")
                return converted_record.get_json_dict()
        converted_content = converted_record.get_content()
        log.debug("returning converted content")
        return converted_content
    except:
        log.error("Exception occurred at logic._export, returning str(record)")
        return str(converted_record)


def export_as_record(id, output_format_name, context={}, type='package'):
    # assuming type=package
    ckan_format_name = 'ckan'

    if type == 'resource':
        ckan_format_name = 'ckan_resource'
        dataset_dict = toolkit.get_action('resource_show')(context, {'id': id})
        # include package data to inherit
        package_id = dataset_dict.get('package_id')
        if package_id:
            package_dict = toolkit.get_action('package_show')(context, {'id': package_id})
            dataset_dict['package_dict'] = package_dict
    else:
        dataset_dict = toolkit.get_action('package_show')(context, {'id': id})

    matching_metadata_formats = MetadataFormats().get_metadata_formats(output_format_name)
    if not matching_metadata_formats:
        return 'Metadata format unknown {output_format_name}'.format(output_format_name=output_format_name)
    output_format = matching_metadata_formats[0]

    # get dataset as record
    try:
        ckan_format = MetadataFormats().get_metadata_formats(ckan_format_name)[0]
        dataset_record = JSONRecord(ckan_format, dataset_dict)
    except Exception as e:
        log.error('Cannot create record in format {0}, Exception: {1}, {2}'.format(ckan_format_name, e,
                                                                                   traceback.format_exc()))
        return 'Cannot create record in format {0}'.format(ckan_format_name)
    # convert
    try:
        converted_record = Converters().get_conversion(dataset_record, output_format)
        if converted_record:
            return converted_record
        else:
            raise Exception('Cannot convert')
    except:
        log.warning("Exception raised while converting: " + traceback.format_exc())
        return ('No converter available for format {0} \n\n (Exception: {1})'.format(output_format_name,
                                                                                     traceback.format_exc(limit=1)))
