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
class Iso19139Converter(BaseConverter):

    def __init__(self):
        iso_output_format = MetadataFormats().get_metadata_formats('iso19139')[0]
        BaseConverter.__init__(self, iso_output_format)

    def convert(self, record):
        if self.can_convert(record):
            dataset_dict = record.get_json_dict()
            converted_content = self._iso_convert_dataset(dataset_dict)
            converted_record = XMLRecord.from_record(Record(self.output_format, converted_content))
            # log.debug(" **** Validating record..." + str(converted_record.validate()) + ' ****')
            return converted_record
        else:
            raise TypeError(('Converter is not compatible with the record format {record_format}({record_version}). ' +
                             'Accepted format is CKAN {input_format}.').format(
                record_format=record.get_metadata_format().get_format_name(),
                record_version=record.get_metadata_format().get_version(),
                input_format=self.get_input_format().get_format_name()))

    def __unicode__(self):
        return super(Iso19139Converter, self).__unicode__() + u'ISO19139 Converter '

    def _iso_convert_dataset(self, dataset_dict):

        extras_dict = self._extras_as_dict(dataset_dict.get('extras', {}))

        md_metadata_dict = collections.OrderedDict()

        # Header
        md_metadata_dict['@xmlns:gmd'] = "http://www.isotc211.org/2005/gmd"
        md_metadata_dict['@xmlns:xsi'] = "http://www.w3.org/2001/XMLSchema-instance"
        md_metadata_dict['@xmlns:gml'] = "http://www.opengis.net/gml"
        md_metadata_dict['@xmlns:gts'] = "http://www.isotc211.org/2005/gts"
        md_metadata_dict['@xmlns:gco'] = "http://www.isotc211.org/2005/gco"
        md_metadata_dict['@xmlns:geonet'] = "http://www.fao.org/geonetwork"
        md_metadata_dict['@xmlns:csw'] = "http://www.opengis.net/cat/csw/2.0.2"
        md_metadata_dict['@xmlns:srv'] = "http://www.isotc211.org/2005/srv"
        md_metadata_dict['@xmlns:gmx'] = "http://www.isotc211.org/2005/gmx"

        md_metadata_dict['@xsi:schemaLocation'] = '{namespace} {schema}'.format(
            namespace=self.output_format.get_namespace(),
            schema=self.output_format.get_xsd_url())

        # File Identifier (O)
        identifier = dataset_dict.get('id', '')
        doi = dataset_dict.get('doi', '')
        if doi:
            identifier = 'doi:' + doi.strip()
        md_metadata_dict['gmd:fileIdentifier'] = {'gco:CharacterString': identifier}

        # Metadata language (C) 3-letter from ISO 639-2/B 
        iso_language = self._get_iso_language_code(dataset_dict.get('language', 'en'))
        md_metadata_dict['gmd:language'] = {'gco:CharacterString': iso_language}

        # Dataset character set (C) : Defaulting to UTF-8 
        md_metadata_dict['gmd:characterSet'] = {
            'gmd:MD_CharacterSetCode': {'@codeListValue': "MD_CharacterSetCode_utf8",
                                        '@codeList': "http://www.isotc211.org/2005/resources/Codelist/gmxCodelists.xml#MD_CharacterSetCode",
                                        '@codeSpace': 'ISOTC211/19115',
                                        '#text': 'MD_CharacterSetCode_utf8'}}

        # Hierarchy Level (O)
        md_metadata_dict['gmd:hierarchyLevel'] = {'gmd:MD_ScopeCode': {
            '@codeList': "http://www.isotc211.org/2005/resources/Codelist/gmxCodelists.xml#MD_ScopeCode",
            '@codeListValue': "dataset"}}

        # Point of Contact (M)
        maintainer = json.loads(dataset_dict.get('maintainer', '{}'))

        maintainer_name = ""
        if maintainer.get('given_name'):
            maintainer_name += maintainer['given_name'].strip() + ' '
        maintainer_name += maintainer['name']

        responsible_party_contact = collections.OrderedDict()

        responsible_party_contact['gmd:individualName'] = {'gco:CharacterString': maintainer_name}
        responsible_party_contact['gmd:organisationName'] = {'gco:CharacterString': maintainer.get('affiliation', '')}
        #        responsible_party_contact['gmd:positionName'] = {'gco:CharacterString':'', '@gco:nilReason':"missing"}

        rpc_ci_contact = collections.OrderedDict()
        #         rpc_ci_contact['gmd:phone'] = {'gmd:CI_Telephone':collections.OrderedDict()}
        #         rpc_ci_contact['gmd:phone']['gmd:CI_Telephone']['gmd:voice'] = {'gco:CharacterString':'', '@gco:nilReason':"missing"}
        #         rpc_ci_contact['gmd:phone']['gmd:CI_Telephone']['gmd:facsimile'] = {'gco:CharacterString':'', '@gco:nilReason':"missing"}

        rpc_ci_contact['gmd:address'] = {'gmd:CI_Address': collections.OrderedDict()}
        #         rpc_ci_contact['gmd:address']['gmd:CI_Address']['gmd:deliveryPoint'] = {'gco:CharacterString':'', '@gco:nilReason':"missing"}
        #         rpc_ci_contact['gmd:address']['gmd:CI_Address']['gmd:city'] = {'gco:CharacterString':'', '@gco:nilReason':"missing"}
        #         rpc_ci_contact['gmd:address']['gmd:CI_Address']['gmd:administrativeArea'] = {'gco:CharacterString':'', '@gco:nilReason':"missing"}
        #         rpc_ci_contact['gmd:address']['gmd:CI_Address']['gmd:postalCode'] = {'gco:CharacterString':'', '@gco:nilReason':"missing"}
        #         rpc_ci_contact['gmd:address']['gmd:CI_Address']['gmd:country'] = {'gco:CharacterString':'Switzerland'}
        rpc_ci_contact['gmd:address']['gmd:CI_Address']['gmd:electronicMailAddress'] = self._get_or_missing(maintainer,
                                                                                                            'email')

        responsible_party_contact['gmd:contactInfo'] = {'gmd:CI_Contact': rpc_ci_contact}

        responsible_party_contact['gmd:role'] = {'gmd:CI_RoleCode': {'@codeListValue': "pointOfContact",
                                                                     '@codeList': "http://www.isotc211.org/2005/resources/Codelist/gmxCodelists.xml#CI_RoleCode"}}

        md_metadata_dict['gmd:contact'] = {'gmd:CI_ResponsibleParty': responsible_party_contact}

        # Metadata Creation Date (M)
        metadata_created = parse(dataset_dict.get("metadata_created", '')).strftime("%Y-%m-%dT%H:%M:%S")
        md_metadata_dict['gmd:dateStamp'] = {'gco:DateTime': {'#text': metadata_created}}

        # Metadata Standard and Version (O)
        md_metadata_dict['gmd:metadataStandardName'] = {'gco:CharacterString': {'#text': 'ISO 19115:2003/19139'}}
        md_metadata_dict['gmd:metadataStandardVersion'] = {'gco:CharacterString': {'#text': '1.0'}}

        # Reference System Information (O)
        md_metadata_dict['gmd:referenceSystemInfo'] = {'gmd:MD_ReferenceSystem': {'gmd:referenceSystemIdentifier': {
            'gmd:RS_Identifier': {'gmd:code': {'gco:CharacterString': {'#text': 'EPSG:4326'}}}}}}

        # Identification Info (mandatory subelements)
        md_data_id = collections.OrderedDict()
        # citation
        citation_dict = collections.OrderedDict()
        citation_dict['gmd:title'] = {'gco:CharacterString': dataset_dict.get('title', '')}

        citation_dict['gmd:date'] = {'gmd:CI_Date': collections.OrderedDict()}
        citation_dict['gmd:date']['gmd:CI_Date']['gmd:date'] = {'gco:Date': self._get_publication_date(dataset_dict)}
        citation_dict['gmd:date']['gmd:CI_Date']['gmd:dateType'] = {'gmd:CI_DateTypeCode': {
            '@codeListValue': 'publication',
            '@codeList': 'http://www.isotc211.org/2005/resources/Codelist/gmxCodelists.xml#CI_DateTypeCode'
        }}
        presentation_form = self._cap_code(dataset_dict.get('resource_type', ''))
        if presentation_form:
            citation_dict['gmd:presentationForm'] = {'gmd:CI_PresentationFormCode': {
                '@codeListValue': presentation_form,
                '@codeList': 'http://www.isotc211.org/2005/resources/Codelist/gmxCodelists.xml#CI_PresentationFormCode'
            }}
        md_data_id['gmd:citation'] = {'gmd:CI_Citation': citation_dict}
        # abstract    
        md_data_id['gmd:abstract'] = {
            'gco:CharacterString': dataset_dict.get('notes', '').replace('\n', ' ').replace('\r', ' ')}

        # purpose (only in extras)
        purpose = self._get_ignore_case(extras_dict, 'purpose')
        if not purpose:
            purpose = self._get_ignore_case(extras_dict, 'CUSTOM_PURPOSE')
        if purpose:
            md_data_id['gmd:purpose'] = purpose
        # status (only in extras)
        status = self._get_ignore_case(extras_dict, 'status')
        if status:
            md_data_id['gmd:status'] = {'gmd:MD_ProgressCode': {
                '@codeListValue': self._cap_code(status),
                '@codeList': "http://www.isotc211.org/2005/resources/Codelist/gmxCodelists.xml#MD_ProgressCode"
            }}
        # Point of contact (copy)
        md_data_id['gmd:pointOfContact'] = {'gmd:CI_ResponsibleParty': copy.deepcopy(responsible_party_contact)}

        # Maintenance (only in extras)
        maintenance = self._get_ignore_case(extras_dict, 'maintenance')
        if maintenance:
            md_data_id['gmd:resourceMaintenance'] = {'gmd:MD_MaintenanceInformation': {
                'gmd:maintenanceAndUpdateFrequency': {
                    'gmd:MD_MaintenanceFrequencyCode': {
                        '@codeListValue': self._cap_code(maintenance),
                        '@codeList': "http://www.isotc211.org/2005/resources/Codelist/gmxCodelists.xml#MD_MaintenanceFrequencyCode"
                    }
                }
            }
            }
        # graphic overview (TODO)

        # keywords (type default to theme)
        keywords = self.get_keywords(dataset_dict)
        if keywords:
            keyword_type = {'gmd:MD_KeywordTypeCode': {'@codeListValue': 'theme',
                                                       '@codeList': 'http://www.isotc211.org/2005/resources/Codelist/gmxCodelists.xml#MD_KeywordTypeCode'}}
            md_data_id['gmd:descriptiveKeywords'] = {
                'gmd:MD_Keywords': {'gmd:keyword': keywords, 'gmd:type': keyword_type}}

        # resource constraints (DRAFT)
        md_legal_constraints = collections.OrderedDict()
        access_constraints = self._get_ignore_case(extras_dict, 'accessConstraints')
        if access_constraints:
            md_legal_constraints['gmd:accessConstraints'] = {
                'gmd:MD_RestrictionCode': {'@codeListValue': self._cap_code(access_constraints),
                                           '@codeList': 'http://www.isotc211.org/2005/resources/Codelist/gmxCodelists.xml#MD_RestrictionCode'}}
        use_constraints = self._get_ignore_case(extras_dict, 'useConstraints')
        if use_constraints:
            md_legal_constraints['gmd:useConstraints'] = {
                'gmd:MD_RestrictionCode': {'@codeListValue': self._cap_code(use_constraints),
                                           '@codeList': 'http://www.isotc211.org/2005/resources/Codelist/gmxCodelists.xml#MD_RestrictionCode'}}
        md_legal_constraints['gmd:otherConstraints'] = self._get_or_missing(dataset_dict, 'license_title')

        md_data_id['gmd:resourceConstraints'] = {'gmd:MD_LegalConstraints': md_legal_constraints}

        # spatialRepresentationType (TODO)
        # spatialResolution (TODO)

        # language (copy)
        md_data_id['gmd:language'] = copy.deepcopy(md_metadata_dict['gmd:language'])
        # character set (copy)
        md_data_id['gmd:characterSet'] = copy.deepcopy(md_metadata_dict['gmd:characterSet'])

        # Topic category (only in extras)
        category = self._get_ignore_case(extras_dict, 'category')
        if category:
            md_data_id['gmd:topicCategory'] = {'gmd:MD_TopicCategoryCode': self._cap_code(category)}

        # temporal extent
        dates = []
        try:
            dates = json.loads(dataset_dict.get('date', '[]'))
        except:
            dates = []
        gml_id_index = 0
        for date in dates:
            gml_id_index += 1
            date_id = 'D' + "%03d" % (gml_id_index,)
            date_description = date.get('date_type', '')
            time_element = {}
            time_sub_element = collections.OrderedDict()
            if date.get('end_date'):
                time_sub_element['@gml:id'] = date_id
                time_sub_element['gml:beginPosition'] = date.get('date', '')
                time_sub_element['gml:endPosition'] = date.get('end_date', '')
                time_element = {'gml:TimePeriod': time_sub_element}
            else:
                time_sub_element['@gml:id'] = date_id
                time_sub_element['gml:timePosition'] = date.get('date', '')
                time_element = {'gml:TimeInstant': time_sub_element}

            time_extent = {'gmd:extent': time_element}
            md_data_id['gmd:extent'] = {'gmd:EX_Extent': collections.OrderedDict()}
            md_data_id['gmd:extent']['gmd:EX_Extent']['gmd:description'] = {'gco:CharacterString': date_description}
            md_data_id['gmd:extent']['gmd:EX_Extent']['gmd:temporalElement'] = {'gmd:EX_TemporalExtent': time_extent}

        # geographic extent
        try:
            spatial = json.loads(dataset_dict.get('spatial', '{}'))
        except:
            spatial = {}
        if spatial:
            geographic_element = collections.OrderedDict()
            if spatial.get('type') == 'Point':
                gml_id_index += 1
                point_id = 'P' + "%03d" % (gml_id_index,)
                coordinates = []
                for coordinate in spatial.get('coordinates', []):
                    coordinates += [str(coordinate)]
                point_element = {'@gml:id': point_id, 'gml:pos': ' '.join(coordinates)}
                geographic_element = {'gmd:EX_BoundingPolygon': {'gmd:polygon': {'gml:Point': point_element}}}
            elif spatial.get('type') == 'MultiPoint':
                gml_id_index += 1
                multi_point_id = 'MP' + "%03d" % (gml_id_index,)
                multi_point_element = {'@gml:id': multi_point_id, 'gml:pointMember': []}
                for coordinate_pair in spatial.get('coordinates', []):
                    gml_id_index += 1
                    point_id = 'P' + "%03d" % (gml_id_index,)
                    coordinates = ' '.join([str(coordinate_pair[0]), str(coordinate_pair[1])])
                    point_element = {'gml:Point': {'@gml:id': point_id, 'gml:pos': coordinates}}
                    multi_point_element['gml:pointMember'] += [point_element]
                geographic_element = {
                    'gmd:EX_BoundingPolygon': {'gmd:polygon': {'gml:MultiPoint': multi_point_element}}}
            else:
                coordinates = spatial.get('coordinates', [])[0]
                if self.is_a_box(coordinates):
                    bounding_box = collections.OrderedDict()
                    bounding_box['gmd:westBoundLongitude'] = {
                        'gco:Decimal': str(min(coordinates[0][0], coordinates[2][0]))}
                    bounding_box['gmd:eastBoundLongitude'] = {
                        'gco:Decimal': str(max(coordinates[0][0], coordinates[2][0]))}
                    bounding_box['gmd:southBoundLatitude'] = {
                        'gco:Decimal': str(min(coordinates[0][1], coordinates[2][1]))}
                    bounding_box['gmd:northBoundLatitude'] = {
                        'gco:Decimal': str(max(coordinates[0][1], coordinates[2][1]))}
                    geographic_element = {'gmd:EX_GeographicBoundingBox': bounding_box}
                else:
                    gml_id_index += 1
                    polygon_id = 'PL' + "%03d" % (gml_id_index,)
                    pos_list = []
                    for coordinate_pair in coordinates:
                        coordinates = ' '.join([str(coordinate_pair[0]), str(coordinate_pair[1])])
                        pos_list += [coordinates]
                    polygon_element = {'@gml:id': polygon_id, 'gml:interior': {'gml:LinearRing': {'gml:pos': pos_list}}}
                    geographic_element = {'gmd:EX_BoundingPolygon': {'gmd:polygon': {'gml:Polygon': polygon_element}}}
                    # spatial.get(type) == 'Polygon':
            md_data_id['gmd:extent'] = {'gmd:EX_Extent': {'gmd:geographicElement': geographic_element}}

        # assign to parent
        md_metadata_dict['gmd:identificationInfo'] = {'gmd:MD_DataIdentification': md_data_id}

        # distribution info (O)
        md_data_dist = collections.OrderedDict()

        # distribution format
        resource_formats = []
        distribution_formats = []
        for resource in dataset_dict.get('resources', []):
            resource_format = resource.get('format', resource.get('mimetype', resource.get('mimetype_inner', '')))
            if resource_format:
                resource_format = resource_format.upper()
                if resource_format not in resource_formats:
                    resource_formats += [resource_format]
                    md_format = collections.OrderedDict()
                    md_format['gmd:name'] = {'gco:CharacterString': resource_format}
                    md_format['gmd:version'] = {'gco:CharacterString': ''}
                    distribution_formats += [{'gmd:MD_Format': md_format}]

        md_data_dist['gmd:distributionFormat'] = distribution_formats

        # assign to parent
        md_metadata_dict['gmd:distributionInfo'] = collections.OrderedDict()
        md_metadata_dict['gmd:distributionInfo']['gmd:MD_Distribution'] = md_data_dist

        # transfer options
        online_resources = []

        # dataset url as information
        protocol, host = helpers.get_site_protocol_and_host()
        package_url = protocol + '://' + host + toolkit.url_for(controller='dataset', action='read',
                                                                id=dataset_dict.get('name', ''))
        online_resource_dataset = self.get_online_resource(package_url, 'dataset metadata', 'information')
        online_resources += [online_resource_dataset]

        # loop through resources
        for resource in dataset_dict.get('resources', []):
            resource_name = resource.get('name', resource.get('id', 'DATASET RESOURCE'))
            resource_url = resource.get('url', toolkit.url_for(controller='resource', action='read',
                                                               id=dataset_dict.get('id', ''),
                                                               resource_id=resource.get('id', '')))
            # check if restricted
            if not helpers.is_url(resource_url):
                log.debug('resource is restricted: ' + resource_name)
                resource_url = package_url + '/resource/' + resource.get('id', '')

            log.debug([resource_url, resource_name])
            online_resource = self.get_online_resource(resource_url, resource_name)
            online_resources += [online_resource]

        # assign to parent
        md_metadata_dict['gmd:distributionInfo']['gmd:MD_Distribution']['gmd:transferOptions'] = {
            'gmd:MD_DigitalTransferOptions': {'gmd:onLine': online_resources}}

        # Root element
        iso_dict = collections.OrderedDict()
        iso_dict['gmd:MD_Metadata'] = md_metadata_dict

        # Convert to xml
        converted_package = unparse(iso_dict, pretty=True)

        return converted_package

    def _get_or_missing(self, data_dict, tag, ignore_case=False):
        if ignore_case:
            if self._get_ignore_case(data_dict, tag):
                return {'gco:CharacterString': self._get_ignore_case(data_dict, tag)}
        else:
            if (data_dict.get(tag)):
                return {'gco:CharacterString': data_dict.get(tag)}

        return {'gco:CharacterString': '', '@gco:nilReason': "missing"}

    def _get_ignore_case(self, data_dict, tag, ignore_blanks=True):
        tag_lower = tag.lower()
        if ignore_blanks:
            tag_lower = tag_lower.replace(' ', '')
        tag_key = ''
        for key in data_dict.keys():
            key_lower = key.lower()
            if ignore_blanks:
                key_lower = key_lower.replace(' ', '')
            if key_lower == tag_lower:
                tag_key = key
                break
        return data_dict.get(tag_key)

    # translate to 3-letter code http://www.loc.gov/standards/iso639-2/ISO-639-2_utf-8.txt
    def _get_iso_language_code(self, code):
        lookup_dict = {'en': 'eng', 'de': 'ger', 'it': 'ita', 'fr': 'fre', 'ro': 'roh'}
        return lookup_dict.get(code, 'eng').title()

    # Take date of type Available or the publication year
    def _get_publication_date(self, data_dict):
        publication_date = ''
        dates = []
        try:
            dates = json.loads(data_dict.get('date', '[]'))
        except:
            dates = []
        for date in dates:
            if date.get('date_type') == 'available':
                publication_date = parse(date.get('date')).strftime("%Y-%m-%d")
        if not publication_date:
            publication = json.loads(data_dict.get('publication', '{}'))
            publication_date = parse(publication["publication_year"] + '-12-31').strftime("%Y-%m-%d")
        return publication_date

    # make capcase code 
    def _cap_code(self, text):
        if text:
            text = text.strip()
            if text.find(' ') >= 0 and len(text) >= 3:
                first_word = (text.split(' ', 1)[0]).lower()
                cap_words = ''.join(string.capwords(text.split(' ', 1)[1]).split(' '))
                return first_word + cap_words
            else:
                text = text[0].lower() + text[1:]
        return text

    # extras as a simple dictionary
    def _extras_as_dict(self, extras):
        extras_dict = {}
        for extra in extras:
            extras_dict[extra.get('key')] = extra.get('value')
        return extras_dict

    # checks spatially if the polygon is a box
    def is_a_box(self, coordinates):
        if len(coordinates) == 5:
            if coordinates[0] == coordinates[4]:
                if ((coordinates[1] == [coordinates[0][0], coordinates[2][1]]) and
                        (coordinates[3] == [coordinates[2][0], coordinates[0][1]]) and
                        (coordinates[0][0] != coordinates[2][0]) and
                        (coordinates[0][1] != coordinates[2][1])):
                    return True
        return False

    # extract keywords from tags
    def get_keywords(self, data_dict):
        keywords = []
        for tag in data_dict.get('tags', []):
            name = tag.get('display_name', '').upper()
            keywords += [{'gco:CharacterString': name}]
        return keywords

    # Create a online resource digital transfer element
    def get_online_resource(self, url, name, function='download'):
        protocol = url.split(':')[0]

        online_resource_dataset = {'gmd:CI_OnlineResource': collections.OrderedDict()}

        online_resource_dataset['gmd:CI_OnlineResource']['gmd:linkage'] = {'gmd:URL': url}
        online_resource_dataset['gmd:CI_OnlineResource']['gmd:protocol'] = {'gco:CharacterString': protocol.upper()}
        online_resource_dataset['gmd:CI_OnlineResource']['gmd:name'] = {'gco:CharacterString': name.upper()}
        online_resource_dataset['gmd:CI_OnlineResource']['gmd:function'] = {'gmd:CI_OnLineFunctionCode':
            {
                '@codeList': "http://www.isotc211.org/2005/resources/Codelist/gmxCodelists.xml#CI_OnLineFunctionCode",
                '@codeListValue': function,
                '#text': function}}
        return online_resource_dataset
