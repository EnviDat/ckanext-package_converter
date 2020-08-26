import json
import unicodedata
from logging import getLogger

from ckanext.package_converter.model.converter import BaseConverter
from ckanext.package_converter.model.metadata_format import MetadataFormats
from ckanext.package_converter.model.record import Record

log = getLogger(__name__)


# this converter is only valid for the metadata schema for EnviDat
# (search envidat/envidat_theme project in github)
class CsvConverter(BaseConverter):

    def __init__(self):
        csv_output_format = MetadataFormats().get_metadata_formats('csv')[0]
        BaseConverter.__init__(self, csv_output_format)

    def convert(self, record):
        if self.can_convert(record):
            dataset_dict = record.get_json_dict()
            converted_content = self._csv_convert_dataset(dataset_dict)
            converted_record = Record(self.output_format, converted_content)
            return converted_record
        else:
            raise TypeError(('Converter is not compatible with the record format {record_format}({record_version}). ' +
                             'Accepted format is CKAN {input_format}.').format(
                record_format=record.get_metadata_format().get_format_name(),
                record_version=record.get_metadata_format().get_version(),
                input_format=self.get_input_format().get_format_name()))

    def __unicode__(self):
        return super(CsvConverter, self).__unicode__() + u'CSV Converter '

    def _csv_convert_dataset(self, dataset_dict):

        csv_header_list = []
        csv_values_list = []

        for key, value in dataset_dict.items():
            if value:
                if type(value) is not list and type(value) is not dict:
                    # check if it is a json
                    try:
                        value_json = json.loads(value)
                        if type(value_json) is dict:
                            value_dict = value_json
                            for subfield_key, subfield_value in value_dict.items():
                                if subfield_value:
                                    csv_values_list += ['"' + self._format_value(subfield_value) + '"']
                                    csv_header_list += ['"' + str(key).upper() + '_' + str(subfield_key).upper() + '"']
                        else:
                            index = 0
                            for value_dict in value_json:
                                index += 1
                                for subfield_key, subfield_value in value_dict.items():
                                    if subfield_value:
                                        csv_values_list += ['"' + self._format_value(subfield_value) + '"']
                                        csv_header_list += ['"' + str(key).upper() + '_' + str(index) + '_' + str(
                                            subfield_key).upper() + '"']
                    except:
                        # text
                        csv_header_list += ['"' + str(key).upper() + '"']
                        csv_values_list += ['"' + self._format_value(value) + '"']
                else:
                    if type(value) is dict:
                        value_dict = value
                        for subfield_key, subfield_value in value_dict.items():
                            if subfield_value:
                                csv_values_list += ['"' + self._format_value(subfield_value) + '"']
                                csv_header_list += ['"' + str(key).upper() + '_' + str(subfield_key).upper() + '"']
                    else:
                        index = 0
                        for value_dict in value:
                            index += 1
                            for subfield_key, subfield_value in value_dict.items():
                                if subfield_value:
                                    csv_values_list += ['"' + self._format_value(subfield_value) + '"']
                                    csv_header_list += ['"' + str(key).upper() + '_' + str(index) + '_' + str(
                                        subfield_key).upper() + '"']

        log.debug(" header length " + str(len(csv_header_list)))
        log.debug(" values length " + str(len(csv_values_list)))
        return (",".join(csv_header_list) + "\n" + ",".join(csv_values_list))

    def _format_value(self, value):
        try:
            text_value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
        except:
            text_value = str(value)
        return text_value.replace('"', '').replace("'", "").replace('\n', ' ').replace('\r', ' ')

    # extract keywords from tags
    def get_keywords(self, data_dict):
        keywords = []
        for tag in data_dict.get('tags', []):
            name = tag.get('display_name', '').upper()
            keywords += [name]
        return keywords
