import ckanext

import ckan.lib.helpers as helpers
import ckan.plugins.toolkit as toolkit

from ckanext.package_converter.model.metadata_format import MetadataFormats
from ckanext.package_converter.model.converter import BaseConverter
from ckanext.package_converter.model.record import Record, JSONRecord, XMLRecord

import collections
from xmltodict import unparse
import json

from dateutil.parser import parse
import string
import copy

from logging import getLogger

log = getLogger(__name__)


# this converter is only valid for the metadata schema for EnviDat
# (search envidat/envidat_theme project in github)
class DcatApChConverter(BaseConverter):

    def __init__(self):
        dcat_output_format = MetadataFormats().get_metadata_formats('dcat-ap-ch')[0]
        BaseConverter.__init__(self, dcat_output_format)

    def convert(self, record):
        if self.can_convert(record):
            dataset_dict = record.get_json_dict()
            converted_content = self._dcat_ap_ch_convert_dataset(dataset_dict)
            converted_record = XMLRecord.from_record(Record(self.output_format, converted_content))
            return converted_record
        else:
            raise TypeError(('Converter is not compatible with the record format {record_format}({record_version}). ' +
                             'Accepted format is CKAN {input_format}.').format(
                record_format=record.get_metadata_format().get_format_name(),
                record_version=record.get_metadata_format().get_version(),
                input_format=self.get_input_format().get_format_name()))

    def __unicode__(self):
        return super(DcatApChConverter, self).__unicode__() + u'DCAT_AP_CH Converter '

    def _dcat_ap_ch_convert_dataset(self, dataset_dict):

        extras_dict = self._extras_as_dict(dataset_dict.get('extras', {}))

        md_metadata_dict = collections.OrderedDict()

        # header
        md_metadata_dict['@xmlns:dct'] = "http://purl.org/dc/terms/"
        md_metadata_dict['@xmlns:dc'] = "http://purl.org/dc/elements/1.1/"
        md_metadata_dict['@xmlns:dcat'] = "http://www.w3.org/ns/dcat#"
        md_metadata_dict['@xmlns:foaf'] = "http://xmlns.com/foaf/0.1/"
        md_metadata_dict['@xmlns:xsd'] = "http://www.w3.org/2001/XMLSchema#"
        md_metadata_dict['@xmlns:rdfs'] = "http://www.w3.org/2000/01/rdf-schema#"
        md_metadata_dict['@xmlns:rdf'] = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        md_metadata_dict['@xmlns:vcard'] = "http://www.w3.org/2006/vcard/ns#"
        md_metadata_dict['@xmlns:odrs'] = "http://schema.theodi.org/odrs#"
        md_metadata_dict['@xmlns:schema'] = "http://schema.org/"

        # get the dataset url
        protocol, host = helpers.get_site_protocol_and_host()
        package_url = protocol + '://' + host + toolkit.url_for(controller='dataset', action='read',
                                                                id=dataset_dict.get('name', ''))
        md_metadata_dict['dcat:Dataset'] = {'@rdf:about': package_url}

        # identifier
        identifier = dataset_dict['id'] + '@envidat'
        md_metadata_dict['dcat:Dataset']['dct:identifier'] = identifier

        # title
        title = dataset_dict['title']
        md_metadata_dict['dcat:Dataset']['dct:title'] = {'@xml:lang': "en",
                                                         '#text': title}
        # description
        description = dataset_dict.get('notes', '').replace('\n', ' ').replace('\r', ' ').replace('__', '')
        md_metadata_dict['dcat:Dataset']['dct:description'] = { '@xml:lang': "en",
                                                                '#text': description}

        # publication
        publisher_name = json.loads(dataset_dict.get('publication', '{}')).get('publisher', '')
        publisher = {'rdf:Description': {'rdfs:label': publisher_name}}
        md_metadata_dict['dcat:Dataset']['dct:publisher'] = publisher

        # contact point
        maintainer = json.loads(dataset_dict.get('maintainer', '{}'))
        maintainer_name = ""
        if maintainer.get('given_name'):
            maintainer_name += maintainer['given_name'].strip() + ' '
        maintainer_name += maintainer['name']
        maintainer_email = "mailto:" + maintainer['email']
        individual_contact_point = {'vcard:Individual': {'vcard:fn': maintainer_name,
                                                         'vcard:hasEmail': {'@rdf:resource': maintainer_email}}}

        if maintainer_email == 'mailto:envidat@wsl.ch':
            md_metadata_dict['dcat:Dataset']['dcat:contactPoint'] = [individual_contact_point]
        else:
            organization_contact_point = {'vcard:Organization': {'vcard:fn': 'EnviDat Support',
                                                                 'vcard:hasEmail': {
                                                                     '@rdf:resource': 'mailto:envidat@wsl.ch'}}}
            md_metadata_dict['dcat:Dataset']['dcat:contactPoint'] = [individual_contact_point,
                                                                     organization_contact_point]

        # theme
        md_metadata_dict['dcat:Dataset']['dcat:theme'] = {'@rdf:resource': "http://opendata.swiss/themes/education"}

        # root element
        dcat_metadata_dict = collections.OrderedDict()
        dcat_metadata_dict['rdf:RDF'] = md_metadata_dict

        # Convert to xml
        converted_package = unparse(dcat_metadata_dict, short_empty_elements=True, pretty=True)

        return converted_package

    # extras as a simple dictionary
    def _extras_as_dict(self, extras):
        extras_dict = {}
        for extra in extras:
            extras_dict[extra.get('key')] = extra.get('value')
        return extras_dict

