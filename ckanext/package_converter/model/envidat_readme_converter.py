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
class ReadmeConverter(BaseConverter):

    def __init__(self):
        iso_output_format = MetadataFormats().get_metadata_formats('plain-text')[0]
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
        return super(BibtexConverter, self).__unicode__() + u'Readme Converter '


    def _bibtex_convert_dataset(self, dataset_dict):
    
    	converted_package = u'\n\n'
        
        tag = u" DATASET IDENTIFICATION "
        converted_package += tag + '\n' + self.get_underline(tag, '-') + '\n'
         
        # DOI
        doi = dataset_dict.get('doi','').strip()
        if doi:
            converted_package += u' - DOI: http://dx.doi.org/{0}\n'.format(doi)
        
        # url
        protocol, host = helpers.get_site_protocol_and_host()
        url = protocol + '://' + host + toolkit.url_for(controller='package', action='read', id=dataset_dict.get('name', ''))
        converted_package += u' - URL: ' + url + '\n\n'
 
        # name  
        #name = dataset_dict['name']
        #tag = u" NAME "
        #converted_package += tag + '\n' + self.get_underline(tag, '-') + '\n' + name + '\n\n'

        # title
        title = dataset_dict['title']
        tag = u" TITLE "
        converted_package += tag + '\n' + self.get_underline(tag, '-') + '\n' + title + '\n\n'

        # year (add to name) and journal
        publication = json.loads(dataset_dict.get('publication', '{}')) 
        publication_year = publication["publication_year"]
        publisher = publication["publisher"]
        
        tag = u" PUBLICATION "
        converted_package += tag + '\n' + self.get_underline(tag, '-') + '\n' 
        converted_package += u'{0}, {1}\n\n'.format(publisher, publication_year)

        # author
        tag = u" AUTHORS "
        converted_package += tag + '\n' + self.get_underline(tag, '-') + '\n' 
        authors = json.loads(dataset_dict.get('author', '[]')) 
        for author in authors:
            author_name = ""
            if author.get('given_name'):
                author_name += author['given_name'].strip() + ' '
            author_name += author['name'].strip() 
            author_affiliation = author ['affiliation']
            converted_package += u' - {0} ({1})\n'.format(author_name, author_affiliation)
        converted_package += u'\n'
                                                
        # keywords 
        tag = u" KEYWORDS "
        converted_package += tag + '\n' + self.get_underline(tag, '-') + '\n' 
        keywords = self.get_keywords(dataset_dict)
        converted_package += ' - ' + '\n - '.join(keywords) + '\n\n' 
        
        # abstract
        tag = u" ABSTRACT "
        converted_package += tag + '\n' + self.get_underline(tag, '-') + '\n' 
        abstract = dataset_dict['notes'].strip()
        converted_package += abstract + '\n\n' 
        
       # dates
        tag = u" DATES "
        converted_package += tag + '\n' + self.get_underline(tag, '-') + '\n' 
        dates = json.loads(dataset_dict.get('date', '[]')) 
        for date in dates:
              date_text = date['date']
              date_type = date['date_type'].title()
              converted_package += u' - {0}: {1}\n'.format(date_type, date_text)
        converted_package += u'\n'
 
         # other information
        tag = u" ADDITIONAL INFORMATION "
        converted_package += tag + '\n' + self.get_underline(tag, '-') + '\n' 
        converted_package += u' - Version: ' + dataset_dict.get('version', 'undefined') + '\n'
        converted_package += u' - Type: ' + dataset_dict.get('type', 'undefined')
        converted_package += u' (' + dataset_dict.get('resource_type_general', 'undefined') + ')\n'
        converted_package += u' - Language: ' + dataset_dict.get('language', 'English') + '\n'
        converted_package += u' - License: ' + dataset_dict.get('license_id', 'undefined') + '\n'
        converted_package += u' - Location: ' + dataset_dict.get('location', 'undefined') + '\n\n'
        
        # resources
        tag = u" DATA RESOURCES "
        converted_package += tag + '\n' + self.get_underline(tag, '-') + '\n' 
        resources = dataset_dict.get('resources', '[]')
        for resource in resources:
              resource_name = resource ['name']
              resource_description = resource ['description'].strip()
              resource_type = resource ['mimetype']
              converted_package += u' - {0} ({1}): {2}\n\n'.format(resource_name, resource_type, resource_description)

        # maintainer
        tag = u" CONTACT PERSON "
        converted_package += tag + '\n' + self.get_underline(tag, '-') + '\n' 
        maintainer = json.loads(dataset_dict.get('maintainer', '')) 
        if maintainer:
              maintainer_name = ""
              if maintainer.get('given_name'):
                  maintainer_name += maintainer['given_name'].strip() + ' '
              maintainer_name += maintainer['name'].strip()
              maintainer_affiliation = maintainer['affiliation'].strip()
              maintainer_mail = maintainer['email'].strip()
              converted_package += u'{0} ({1}), mail: {2}\n\n'.format(maintainer_name, maintainer_affiliation, maintainer_mail)

        return converted_package
            
    # extract keywords from tags
    def get_keywords(self, data_dict):
        keywords = []
        for tag in data_dict.get('tags',[]):
            name = tag.get('display_name', '').upper()
            keywords += [name]
        return keywords

    # extract keywords from tags
    def get_underline(self, text, symbol = '='):
        underline = ''
        for letter in text:
            underline += symbol
        return underline



