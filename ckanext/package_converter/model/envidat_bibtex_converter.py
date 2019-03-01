import ckanext

import ckan.lib.helpers as helpers
import ckan.plugins.toolkit as toolkit

from ckanext.package_converter.model.metadata_format import MetadataFormats
from ckanext.package_converter.model.converter import BaseConverter
from ckanext.package_converter.model.record import Record, JSONRecord

import collections
import json

from dateutil.parser import parse
import string
import copy 

from logging import getLogger
log = getLogger(__name__)

# this converter is only valid for the metadata schema for EnviDat 
# (search envidat/envidat_theme project in github)
class BibtexConverter(BaseConverter):

    def __init__(self):
        iso_output_format = MetadataFormats().get_metadata_formats('bibtex')[0]
        BaseConverter.__init__(self, iso_output_format)

    def convert(self, record):
        if self.can_convert(record):
            dataset_dict = record.get_json_dict()
            converted_content = self._bibtex_convert_dataset(dataset_dict)
            converted_record = Record(self.output_format, converted_content)
            return converted_record
        else:
            raise TypeError(('Converter is not compatible with the record format {record_format}({record_version}). ' +
                             'Accepted format is CKAN {input_format}.').format(
                                 record_format=record.get_metadata_format().get_format_name(), record_version=record.get_metadata_format().get_version(),
                                 input_format=self.get_input_format().get_format_name()))

    def __unicode__(self):
        return super(BibtexConverter, self).__unicode__() + u'BibTex Converter '


    def _bibtex_convert_dataset(self, dataset_dict):
    
        # name as identifier (plus year later)
        name = dataset_dict['name']
        converted_package = u"@misc { " + name
    
        # year (add to name) and journal
        publication = json.loads(dataset_dict.get('publication', '{}')) 
        publication_year = publication["publication_year"]
        
        converted_package += u'-{0}'.format(publication_year)
        converted_package += u',\n\t year = "{0}"'.format(publication_year)
        publisher = publication["publisher"]
        converted_package += u',\n\t publisher = "{0}"'.format(publisher)

        # title
        title = dataset_dict['title']
        converted_package += u',\n\t title = "' + title + u'"'

        # author
        authors = json.loads(dataset_dict.get('author', '[]')) 
        author_names = []
        for author in authors:
            author_names += [author['name']]
        bibtex_author = u' and '.join(author_names)
        converted_package += u',\n\t author = "{0}"'.format(bibtex_author)

        # DOI
        doi = dataset_dict.get('doi','').strip()
        if doi:
            converted_package += u',\n\t DOI = "http://dx.doi.org/{0}"'.format(doi)
        
        # keywords (type default to theme)
        #keywords = self.get_keywords(dataset_dict)

        # close bracket
        converted_package += "\n\t}"
        
        return converted_package
            
    # extract keywords from tags
    def get_keywords(self, data_dict):
        keywords = []
        for tag in data_dict.get('tags',[]):
            name = tag.get('display_name', '').upper()
            keywords += [{'gco:CharacterString':name}]
        return keywords



