from ckanext.package_converter.model.record import Record, JSONRecord
from ckanext.package_converter.model.metadata_format import MetadataFormats, MetadataFormat, FormatType
from ckanext.package_converter.model.converter import BaseConverter

from logging import getLogger
log = getLogger(__name__)

class CustomMetadataFormat(MetadataFormat):
    def __init__(self, custom_parameter):
        MetadataFormat.__init__(self, 'custom', '1.0', format_type=FormatType.TEXT,
                                description='my custom format for testing purposes')
        self.custom_parameter = custom_parameter

class CustomConverter(BaseConverter):

    def __init__(self):
        custom_output_format = MetadataFormats().get_metadata_formats('custom')[0]
        BaseConverter.__init__(self, custom_output_format)

    def convert(self, record):
        if self.can_convert(record):
            dataset_dict = record.get_json_dict()
            converted_content = ('Custom converted metadata for package {name}').format(name=dataset_dict.get('name', ''))
            converted_record = Record(self.output_format, converted_content)
            return converted_record
        else:
            raise TypeError(('Converter is not compatible with the record format {record_format}({record_version}). ' +
                             'Accepted format is CKAN {input_format}.').format(
                                 record_format=record.get_metadata_format().get_format_name(), record_version=record.get_metadata_format().get_version(),
                                 input_format=self.get_input_format().get_format_name()))

    def __unicode__(self):
        return super(CustomConverter, self).__unicode__() + u' Custom Converter. '

