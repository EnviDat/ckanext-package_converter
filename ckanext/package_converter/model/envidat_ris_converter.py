import json
from logging import getLogger

import ckan.lib.helpers as helpers
import ckan.plugins.toolkit as toolkit
from ckanext.package_converter.model.converter import BaseConverter
from ckanext.package_converter.model.metadata_format import MetadataFormats
from ckanext.package_converter.model.record import Record

log = getLogger(__name__)


# this converter is only valid for the metadata schema for EnviDat
# (search envidat/envidat_theme project in github)
class RisConverter(BaseConverter):

    def __init__(self):
        ris_output_format = MetadataFormats().get_metadata_formats('ris')[0]
        BaseConverter.__init__(self, ris_output_format)

    def convert(self, record):
        if self.can_convert(record):
            dataset_dict = record.get_json_dict()
            converted_content = self._ris_convert_dataset(dataset_dict)
            converted_record = Record(self.output_format, converted_content)
            return converted_record
        else:
            raise TypeError(('Converter is not compatible with the record format {record_format}({record_version}). ' +
                             'Accepted format is CKAN {input_format}.').format(
                record_format=record.get_metadata_format().get_format_name(),
                record_version=record.get_metadata_format().get_version(),
                input_format=self.get_input_format().get_format_name()))

    def __unicode__(self):
        return super(RisConverter, self).__unicode__() + u'RIS Converter '

    def _ris_convert_dataset(self, dataset_dict):

        ris_list = []

        #   TY  - DATA
        ris_list += [u"TY  - DATA"]

        #   T1  - Title
        title = dataset_dict['title']
        ris_list += [u"T1  - " + title]

        #   AU  - Authors
        authors = json.loads(dataset_dict.get('author', '[]'))
        author_names = []
        for author in authors:
            author_name = ""
            if author.get('given_name'):
                author_name += author['given_name'].strip() + ' '
            author_name += author['name'].strip()
            ris_list += [u"AU  - " + author_name]

            #   DO  - DOI
        doi = dataset_dict.get('doi', '').strip()
        if doi:
            ris_list += [u"DO  - " + doi]

            #   UR  - dataset url as information
        protocol, host = helpers.get_site_protocol_and_host()
        url = protocol + '://' + host + toolkit.url_for(controller='package', action='read',
                                                        id=dataset_dict.get('name', ''))
        ris_list += [u"UR  - " + url]

        #   KW  - keywords (type default to theme)
        keywords = self.get_keywords(dataset_dict)
        for keyword in keywords:
            ris_list += [u"KW  - " + keyword]

        #   PY  - publication year
        publication = json.loads(dataset_dict.get('publication', '{}'))
        publication_year = publication["publication_year"]
        ris_list += [u"PY  - " + publication_year]

        #   PB  - Publisher
        publisher = publication["publisher"]
        ris_list += [u"PB  - " + publisher]

        #   LA  - en
        language = dataset_dict.get('language', 'en').strip()
        if len(language) <= 0:
            language = 'en'

        ris_list += [u"LA  - " + language]

        #   ER  - 
        ris_list += [u"ER  - "]

        return "\n".join(ris_list)

    # extract keywords from tags
    def get_keywords(self, data_dict):
        keywords = []
        for tag in data_dict.get('tags', []):
            name = tag.get('display_name', '').upper()
            keywords += [name]
        return keywords
