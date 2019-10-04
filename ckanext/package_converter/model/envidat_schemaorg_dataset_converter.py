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
class SchemaOrgDadatasetConverter(BaseConverter):

    def __init__(self):
        schemaorg_output_format = MetadataFormats().get_metadata_formats('schemaorg')[0]
        BaseConverter.__init__(self, schemaorg_output_format)

    def convert(self, record):
        if self.can_convert(record):
            dataset_dict = record.get_json_dict()
            converted_dict = self._schemaorg_convert_dataset(dataset_dict)
            converted_record = JSONRecord(self.output_format, converted_dict)
            return converted_record
        else:
            raise TypeError(('Converter is not compatible with the record format {record_format}({record_version}). ' +
                             'Accepted format is CKAN {input_format}.').format(
                                 record_format=record.get_metadata_format().get_format_name(), record_version=record.get_metadata_format().get_version(),
                                 input_format=self.get_input_format().get_format_name()))

    def __unicode__(self):
        return super(SchemaOrgDadatasetConverter, self).__unicode__() + u'Schema.org Dataset Converter '


    def _schemaorg_convert_dataset(self, dataset_dict):
    
        converted_dict = collections.OrderedDict()
        
        converted_dict["@context"] = "http://schema.org"
        converted_dict["@type"] = "Dataset"

        # url id
        protocol, host = helpers.get_site_protocol_and_host()
        url_id = protocol + '://' + host + toolkit.url_for(controller='package', action='read', id=dataset_dict.get('id', ''))
        converted_dict["@id"] = url_id

        # identifier (DOI)
        doi = dataset_dict.get('doi','').strip()
        if doi:
            converted_dict["identifier"] = collections.OrderedDict()
            converted_dict["identifier"]["@type"] = "PropertyValue"
            converted_dict["identifier"]["propertyID"] = "DOI"
            converted_dict["identifier"]["value"] = 'https://doi.org/{0}'.format(doi)

        # url name
        protocol, host = helpers.get_site_protocol_and_host()
        url_name = protocol + '://' + host + toolkit.url_for(controller='package', action='read', id=dataset_dict.get('name', ''))
        converted_dict["@url"] = url_name

        # title
        title = dataset_dict['title']
        converted_dict["@name"] = title
        
        # author
        converted_dict["author"] = []
        
        authors = json.loads(dataset_dict.get('author', '[]')) 
        for author in authors:
              author_dict = collections.OrderedDict()
              if len(author.get("given_name",'').strip())>0:
                  author_dict["name"] = author['given_name'].strip() + ' ' + author['name'].strip()
                  author_dict["givenName"] = author['given_name'].strip()
                  author_dict["familyName"] = author['name'].strip()
              else:
                  author_dict["name"] = author['name']
                  if len(author['name'].split(' ')) > 1:
                      author_dict["givenName"] = author['name'].split(' ')[0]
                      author_dict["familyName"] = author['name'].split(' ')[1]
                  elif len(author['name'].split(',')) > 1:
                      author_dict["givenName"] = author['name'].split(',')[1].strip()
                      author_dict["familyName"] = author['name'].split(',')[0].strip()
                  elif len(author['name'].split('.')) > 1:
                      author_dict["givenName"] = author['name'].split('.')[0] + '.'
                      author_dict["familyName"] = author['name'].split('.')[1].strip()
              author_dict["@type"] = "Person"
              converted_dict["author"] += [author_dict]
        
        # keywords 
        converted_dict["keywords"] = self.get_keywords(dataset_dict) 

        # keywords 
        converted_dict["description"] = dataset_dict['notes'].replace('\r', '').replace('>', '-').replace('<', '-').replace('__', '').replace('#', '').replace('\n\n', '\n').replace('\n\n', '\n')

        # language
        converted_dict["inLanguage"] = dataset_dict.get('language', 'en')

        # publication date
        publication = json.loads(dataset_dict.get('publication', '{}')) 
        if publication:
            converted_dict["datePublished"] = publication.get("publication_year", "")
            converted_dict["publisher"] = {"name": publication.get("publisher", "EnviDat"), "@type": "Organization"}
 
        return converted_dict
                
    # extract keywords from tags
    def get_keywords(self, data_dict):
        keywords = []
        for tag in data_dict.get('tags',[]):
            name = tag.get('display_name', '').upper()
            keywords += [name]
        return keywords


