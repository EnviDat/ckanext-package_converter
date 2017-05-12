import ckanext

from ckanext.package_converter.model.metadata_format import MetadataFormats
from ckanext.package_converter.model.converter import BaseConverter
from ckanext.package_converter.model.record import Record, JSONRecord, XMLRecord

from ckanext.scheming import helpers
import ckan.model as model
import ckan.plugins.toolkit as toolkit

import collections
from pylons import config
from xmltodict import unparse
import sys
import json

from logging import getLogger
log = getLogger(__name__)


FIELD_NAME = 'field_name'

class SchemingConverter(BaseConverter):

    def __init__(self, output_format):
        BaseConverter.__init__(self, output_format)

    def can_convert(self, record, check_version=False):
        return (super(SchemingConverter, self).can_convert(record, check_version) and issubclass(type(record), JSONRecord))

    def _get_schema_map(self, format_name):

        def _map_fields(schema, format_name):
            map_dict = {}
            for field in schema:
                format_field = ''
                if field.get(format_name, False):
                    format_field = field[format_name]
                    map_dict[format_field] = {FIELD_NAME:field[FIELD_NAME], 'subfields':{}}
                for subfield in field.get('subfields',[]):
                    if subfield.get(format_name, False):
                        format_subfield = subfield[format_name]
                        if format_field:
                            map_dict[format_field]['subfields'][format_subfield]= {FIELD_NAME:subfield[FIELD_NAME]}
                        else:
                            map_dict[format_subfield] = {FIELD_NAME:field[FIELD_NAME] + '.' + subfield[FIELD_NAME]}
            return map_dict

        schema = helpers.scheming_get_schema('dataset','dataset')
        schema_map = {'format_name':format_name,
                      'metadata':_map_fields(schema['dataset_fields'], format_name),
                      'metadata_resource': _map_fields(schema['resource_fields'], format_name)}
        return schema_map

    def _get_single_mapped_value(self, format_tag, dataset_dict, metadata_map, default=''):

        # standard field
        ckan_tag = metadata_map.get(format_tag, {FIELD_NAME:''})[FIELD_NAME]
        value = dataset_dict.get(ckan_tag, '')

        # repeating (get first)
        if value:
            try:
                repeating_field = json.loads(value)
                if type(repeating_field) is list:
                    value = repeating_field[0]
            except Exception:
                sys.exc_clear()

        # composite (if repeating, get first)
        if not value and (len(ckan_tag.split('.')) > 1) :
            field = ckan_tag.split('.', 1)[0]
            subfield = ckan_tag.split('.', 1)[1]
            try:
                json_field = dataset_dict[field]
                if type(json_field) not in [list, dict]:
                    json_field = json.loads(json_field)
                if type(json_field) is list:
                    json_field = json_field[0]
                value = json_field[subfield]
            except:
                log.error("Unexpected error:", sys.exc_info()[0])
                sys.exc_clear()

        if not value:
            value = default
            log.debug ('Cannot map single value for ' + format_tag)

        return (value)

    def _joinTags(self, tag_list, sep='.'):
        return (sep.join([tag for tag in tag_list if tag]))

    def _get_complex_mapped_value(self, group_tag, element_tag, field_tags, dataset_dict, metadata_map):
        values_list = []

        # Simple fields
        simple_fields_object = collections.OrderedDict()
        for field in field_tags:
            simple_field_tag = self._joinTags([element_tag, field])
            group_field_tag = self._joinTags([group_tag, simple_field_tag])

            ckan_tag = metadata_map.get(group_field_tag, {FIELD_NAME:''})[ FIELD_NAME ]
            value = dataset_dict.get(ckan_tag, '')
            if value:
                simple_fields_object[simple_field_tag] = value
        if simple_fields_object:
            values_list += [simple_fields_object]

        # TODO: Repeating (?)

        # Composite ( repeating )
        ckan_tag = metadata_map.get(group_tag, {FIELD_NAME:''})[FIELD_NAME]
        ckan_subfields =  metadata_map.get(group_tag, {'subfields':[]})['subfields']

        if dataset_dict.get(ckan_tag, ''):
            try:
                json_field = dataset_dict[ckan_tag]
                if type(json_field) not in [list, dict]:
                    json_field = json.loads(json_field)
                if type(json_field) is not list:
                    json_field = [json_field]
                for ckan_element in json_field:
                    composite_object = collections.OrderedDict()
                    for field in field_tags:
                        field_tag = self._joinTags([element_tag, field])
                        ckan_subfield_tag = ckan_subfields.get(field_tag, {FIELD_NAME:''})[FIELD_NAME]
                        subfield_value = ckan_element.get(ckan_subfield_tag, '')
                        if subfield_value:
                            composite_object[field_tag] = subfield_value
                    if composite_object:
                        values_list += [composite_object]
            except:
                log.debug('Cannot get composite value: (' + ', '.join([group_tag, element_tag] + field_tags )+ '): '+ ckan_tag)

        return values_list

class Datacite31SchemingConverter(SchemingConverter):

    def __init__(self):
        self.output_format = MetadataFormats().get_metadata_formats('datacite', '3.1')[0]
        SchemingConverter.__init__(self, self.output_format)

    def convert(self, record):
        if self.can_convert(record):
            dataset_dict = record.get_json_dict()
            #log.debug('dataset_dict = ' + repr(dataset_dict))
            converted_content = self._datacite_converter_schema(dataset_dict)
            converted_record = Record(self.output_format, converted_content)
            return XMLRecord.from_record(converted_record)
        else:
            raise TypeError(('Converter is not compatible with the record format {record_format}({record_version}). ' +
                             'Accepted format is {input_format}({input_version}).').format(
                                 record_format=record.get_metadata_format().get_format_name(), record_version=record.get_metadata_format().get_version(),
                                 input_format=self.get_input_format().get_format_name(), input_version=self.input_format.get_version()))

    def _valueToDataciteCV (self, value, datacite_tag, default=''):
        # Constant definitions
        datacite_cv = {}
        datacite_cv ['titleType'] = { 'alternativetitle':'AlternativeTitle', 'subtitle':'Subtitle', 'translatedtitle':'TranslatedTitle', 'other':'Other' }
        datacite_cv ['resourceTypeGeneral'] = { 'audiovisual': 'Audiovisual', 'collection': 'Collection', 'dataset': 'Dataset', 'event': 'Event', 'image': 'Image',
                                     'interactiveresource': 'InteractiveResource', 'model': 'Model', 'physicalobject': 'PhysicalObject',
                                     'service': 'Service', 'software': 'Software', 'sound': 'Sound', 'text': 'Text', 'workflow': 'Workflow', 'other': 'Other' }
        datacite_cv ['descriptionType'] = { 'abstract':'Abstract', 'methods':'Methods', 'seriesinformation':'SeriesInformation', 'tableofcontents': 'TableOfContents', 'other':'Other' }
        datacite_cv ['contributorType'] = { 'contactperson': 'ContactPerson', 'datacollector': 'DataCollector', 'datacurator': 'DataCurator', 'datamanager': 'DataManager',
                                              'distributor': 'Distributor', 'editor': 'Editor', 'funder': 'Funder', 'hostinginstitution': 'HostingInstitution', 'other': 'Other',
                                              'producer': 'Producer', 'projectleader': 'ProjectLeader', 'projectmanager': 'ProjectManager', 'projectmember': 'ProjectMember',
                                              'registrationagency': 'RegistrationAgency', 'registrationauthority': 'RegistrationAuthority', 'relatedperson': 'RelatedPerson',
                                              'researchgroup': 'ResearchGroup', 'rightsholder': 'RightsHolder', 'researcher': 'Researcher',
                                              'sponsor': 'Sponsor', 'supervisor': 'Supervisor', 'workpackageleader': 'WorkPackageLeader' }
        # Matching ignoring blanks, case, symbols
        value_to_match = value.lower().replace(' ', '').replace('_', '')
        match_cv = datacite_cv.get(datacite_tag, {}).get(value_to_match, default)

        return (match_cv)

    def _datacite_converter_schema(self, dataset_dict):
        schema_map = self._get_schema_map(self.output_format.get_format_name())
        metadata_map = schema_map['metadata']
        metadata_resource_map = schema_map['metadata_resource']
        datacite_dict = collections.OrderedDict()

        # Header
        datacite_dict['resource']=collections.OrderedDict()
        datacite_dict['resource']['@xsi:schemaLocation'] = '{namespace} {schema}'.format(namespace=self.output_format.get_namespace(), 
                                                                                         schema=self.output_format.get_xsd_url())
        datacite_dict['resource']['@xmlns']='{namespace}'.format(namespace=self.output_format.get_namespace())
        datacite_dict['resource']['@xmlns:xsi']='http://www.w3.org/2001/XMLSchema-instance'

        # Identifier*
        datacite_identifier_tag = 'identifier'
        datacite_dict['resource'][datacite_identifier_tag] = {'#text': self._get_single_mapped_value(datacite_identifier_tag, dataset_dict, metadata_map), '@identifierType':'DOI'}

        # Creators
        datacite_creators_tag = 'creators'
        datacite_creator_tag = 'creator'
        datacite_creator_subfields = ['creatorName', 'affiliation', 'nameIdentifier', 'nameIdentifier.nameIdentifierScheme']

        datacite_dict['resource'][datacite_creators_tag] = { datacite_creator_tag: [ ] }
        ckan_creators = self._get_complex_mapped_value(datacite_creators_tag, datacite_creator_tag, datacite_creator_subfields, dataset_dict, metadata_map)
        for ckan_creator in ckan_creators:
            datacite_creator = collections.OrderedDict()
            datacite_creator['creatorName'] = ckan_creator.get(self._joinTags([datacite_creator_tag, 'creatorName']), '')
            if ckan_creator.get(self._joinTags([datacite_creator_tag, 'nameIdentifier']), False):
                datacite_creator['nameIdentifier'] = { '#text': ckan_creator.get(self._joinTags([datacite_creator_tag, 'nameIdentifier']), ''),
                                                       '@nameIdentifierScheme':  ckan_creator.get(self._joinTags([datacite_creator_tag, 'nameIdentifier', 'nameIdentifierScheme']), '').upper() }
            datacite_creator['affiliation'] = ckan_creator.get(self._joinTags([datacite_creator_tag, 'affiliation']), '')
            datacite_dict['resource'][datacite_creators_tag][datacite_creator_tag] += [ datacite_creator ]

        # Titles*
        datacite_titles_tag = 'titles'
        datacite_title_tag = 'title'
        datacite_xml_lang_tag = 'xml:lang'
        datacite_dict['resource'][datacite_titles_tag] = { datacite_title_tag: [ ] }
        datacite_title_type_tag = 'titleType'
        ckan_titles = self._get_complex_mapped_value(datacite_titles_tag, datacite_title_tag, ['', datacite_title_type_tag, datacite_xml_lang_tag], dataset_dict, metadata_map)
        for ckan_title in ckan_titles:
            datacite_title = {'#text': ckan_title.get( datacite_title_tag, ''),
                              '@' + datacite_xml_lang_tag: ckan_title.get( self._joinTags([datacite_title_tag, datacite_xml_lang_tag]) , 'en-us')}
            if ckan_title.get( self._joinTags([datacite_title_tag, datacite_title_type_tag]) ,''):
                ckan_title_type =  ckan_title.get( self._joinTags([datacite_title_tag, datacite_title_type_tag]) , 'other')
                datacite_title['@' + datacite_title_type_tag] =  self._valueToDataciteCV (ckan_title_type, datacite_title_type_tag)
            datacite_dict['resource'][datacite_titles_tag][datacite_title_tag] += [ datacite_title ]

        # Publication year*
        datacite_publication_year_tag = 'publicationYear'
        datacite_dict['resource'][datacite_publication_year_tag] = {'#text': self._get_single_mapped_value(datacite_publication_year_tag, dataset_dict, metadata_map) }

        # Publisher
        datacite_publisher_tag = 'publisher'
        publisher_value = self._get_single_mapped_value(datacite_publisher_tag, dataset_dict, metadata_map)
        if (publisher_value):
            datacite_dict['resource'][datacite_publisher_tag] = {'#text': publisher_value }

        # Subjects
        datacite_subjects_tag = 'subjects'
        datacite_subject_tag = 'subject'
        datacite_subjects = []
        # Defined by usual field
        ckan_subjects = self._get_complex_mapped_value(datacite_subjects_tag, datacite_subject_tag, [ '', datacite_xml_lang_tag ], dataset_dict, metadata_map)
        for ckan_subject in ckan_subjects:
            datacite_subject = {'#text': ckan_subject.get( datacite_subject_tag, ''),
                              '@' + datacite_xml_lang_tag: ckan_subject.get( self._joinTags([datacite_subject_tag, datacite_xml_lang_tag]) , 'en-us')}
            datacite_subjects += [ datacite_subject ]
        # Defined by autocomplete tags
        if metadata_map.get(self._joinTags([datacite_subjects_tag, datacite_subject_tag]),{FIELD_NAME:''})[FIELD_NAME].find('tag')>=0:
            for tag in dataset_dict.get('tags', []):
                tag_name = tag.get('display_name', tag.get('name',''))
                datacite_subjects += [{ '@' + datacite_xml_lang_tag:'en-us', '#text':tag_name}]
        if datacite_subjects:
            datacite_dict['resource'][datacite_subjects_tag] = { datacite_subject_tag: datacite_subjects }

        # Contributor (contact person)
        datacite_contributors_tag = 'contributors'
        datacite_contributor_tag = 'contributor'
        datacite_contributor_subfields = ['contributorName', 'affiliation', 'contributorType', 'nameIdentifier', 'nameIdentifier.nameIdentifierScheme']
        datacite_contributors = []
        ckan_contributors = self._get_complex_mapped_value(datacite_contributors_tag, datacite_contributor_tag, datacite_contributor_subfields, dataset_dict, metadata_map)
        for ckan_contributor in ckan_contributors:
            datacite_contributor = collections.OrderedDict()
            datacite_contributor['contributorName'] = ckan_contributor.get(self._joinTags([datacite_contributor_tag, 'contributorName']), '')
            datacite_contributor['affiliation'] = ckan_contributor.get(self._joinTags([datacite_contributor_tag, 'affiliation']), '')
            if ckan_contributor.get(datacite_contributor_tag + '.' + 'nameIdentifier', False):
                datacite_contributor['nameIdentifier'] = { '#text': ckan_contributor.get(self._joinTags([datacite_contributor_tag, 'nameIdentifier']), ''),
                                                           '@nameIdentifierScheme':  ckan_contributor.get(self._joinTags([datacite_contributor_tag, 'nameIdentifier', 'nameIdentifierScheme']) , '').upper() }
            ckan_contributor_type = ckan_contributor.get(self._joinTags([datacite_contributor_tag, 'contributorType']), 'ContactPerson')
            datacite_contributor['@contributorType'] = self._valueToDataciteCV (ckan_contributor_type, 'contributorType')
            datacite_contributors += [ datacite_contributor ]

        if datacite_contributors:
            datacite_dict['resource'][datacite_contributors_tag] = { datacite_contributor_tag: datacite_contributors }

        # Dates
        datacite_dates_tag = 'dates'
        datacite_date_tag = 'date'
        datacite_date_type_tag = 'dateType'
        datacite_dates = []
        ckan_dates = self._get_complex_mapped_value(datacite_dates_tag, datacite_date_tag, [ '', datacite_date_type_tag ], dataset_dict, metadata_map)
        for ckan_date in ckan_dates:
            datacite_date =  {'#text': ckan_date.get(datacite_date_tag, ''),
                              '@' + datacite_date_type_tag: ckan_date.get(self._joinTags([datacite_date_tag, datacite_date_type_tag]), 'Valid').title()}
            datacite_dates += [ datacite_date ]
        if datacite_dates:
            datacite_dict['resource'][datacite_dates_tag] = { datacite_date_tag: datacite_dates }

        # Language
        datacite_language_tag = 'language'
        datacite_dict['resource'][datacite_language_tag] = {'#text': self._get_single_mapped_value(datacite_language_tag, dataset_dict, metadata_map, 'en') }

        # ResourceType
        datacite_resource_type_tag = 'resourceType'
        datacite_resource_type_general_tag = 'resourceTypeGeneral'
        ckan_resource_type = self._get_complex_mapped_value('', datacite_resource_type_tag, [ '', datacite_resource_type_general_tag ], dataset_dict, metadata_map)
        if ckan_resource_type:
             ckan_resource_type_general = ckan_resource_type[0].get(self._joinTags([datacite_resource_type_tag, datacite_resource_type_general_tag]))
             datacite_resource_type_general = self._valueToDataciteCV(ckan_resource_type_general, datacite_resource_type_general_tag, default = 'Dataset')
             datacite_dict['resource'][datacite_resource_type_tag] = { '#text': ckan_resource_type[0].get(datacite_resource_type_tag, ''),
                                                                       '@' + datacite_resource_type_general_tag: datacite_resource_type_general }

        # Alternate Identifier (CKAN URL)
        ckan_package_url = config.get('ckan.site_url','') + toolkit.url_for(controller='package', action='read', id=dataset_dict.get('name', ''))
        datacite_dict['resource']['alternateIdentifiers']={'alternateIdentifier':[{'#text':ckan_package_url, '@alternateIdentifierType':'URL'}]}
        # legacy
        if dataset_dict.get('url', ''):
            datacite_dict['resource']['alternateIdentifiers']['alternateIdentifier'] += [{'#text': dataset_dict.get('url', ''), '@alternateIdentifierType':'URL'}]

        # Sizes (not defined in scheming, taken from default CKAN resource)
        datacite_size_group_tag = 'sizes'
        datacite_size_tag = 'size'
        datacite_sizes = []
        for resource in dataset_dict.get('resources', []):
            if resource.get('size', ''):
                datacite_sizes += [{'#text': resource.get('size', ' ') + ' bytes'}]
        if datacite_sizes:
             datacite_dict['resource'][datacite_size_group_tag] = {datacite_size_tag: datacite_sizes}

        # Formats (get from resources)
        datacite_format_group_tag = 'formats'
        datacite_format_tag = 'format'
        datacite_formats = []

        for resource in dataset_dict.get('resources', []):
          resource_format = self._get_single_mapped_value( self._joinTags([datacite_format_group_tag, datacite_format_tag]), 
                                                           resource, metadata_resource_map, 
                                                           default=resource.get('mimetype', resource.get('mimetype_inner', '')))
          if resource_format:
              datacite_format = {'#text': resource_format}
              if datacite_format not in datacite_formats:
                  datacite_formats += [datacite_format]
        if datacite_formats:
            datacite_dict['resource'][datacite_format_group_tag] = {datacite_format_tag: datacite_formats}

        # Version
        datacite_version_tag = 'version'
        datacite_version = self._get_single_mapped_value(datacite_version_tag, dataset_dict, metadata_map, '')
        if datacite_version:
            datacite_dict['resource'][datacite_version_tag] = {'#text': datacite_version }

        # Rights
        datacite_rights_group_tag = 'rightsList'
        datacite_rights_tag = 'rights'
        datacite_rights_uri_tag = 'rightsURI'

        datacite_rights = self._get_complex_mapped_value(datacite_rights_group_tag, datacite_rights_tag, ['', datacite_rights_uri_tag], dataset_dict, metadata_map)

        # Get details form License object
        if datacite_rights:
            register = model.Package.get_license_register()
            rights_list = []
            for rights_item in datacite_rights:
                rights_id = rights_item.get(datacite_rights_tag)
                if rights_id:
                     rights_title = rights_id
                     rights_uri = rights_item.get( self._joinTags([datacite_rights_tag, datacite_rights_uri_tag]), '')
                     try:
                         license = register.get(rights_id)
                         rights_title = license.title
                         rights_uri =  license.url
                     except Exception:
                         log.debug('Exception when trying to get license attributes')
                         pass
                     datacite_rights_item = { '#text': rights_title }
                     if rights_uri:
                         datacite_rights_item['@'+ datacite_rights_uri_tag] = rights_uri
                     rights_list += [datacite_rights_item]
            if rights_list:
                 datacite_dict['resource'][datacite_rights_group_tag] = {datacite_rights_tag: rights_list }

        # Description
        datacite_descriptions_tag = 'descriptions'
        datacite_description_tag = 'description'
        datacite_description_type_tag = 'descriptionType'
        datacite_descriptions = []
        ckan_descriptions = self._get_complex_mapped_value(datacite_descriptions_tag, datacite_description_tag, [ '', datacite_xml_lang_tag, datacite_description_type_tag], dataset_dict, metadata_map)
        for ckan_description in ckan_descriptions:
            datacite_description = {'#text': ckan_description.get( datacite_description_tag, ''),
                              '@' + datacite_description_type_tag: ckan_description.get( self._joinTags([datacite_description_tag, datacite_description_type_tag]) , 'Abstract'),
                              '@' + datacite_xml_lang_tag: ckan_description.get( self._joinTags([datacite_description_tag, datacite_xml_lang_tag]) , 'en-us')}
            datacite_descriptions += [ datacite_description ]
        if datacite_descriptions:
            datacite_dict['resource'][datacite_descriptions_tag] = { datacite_description_tag: datacite_descriptions }

        # GeoLocation
        datacite_geolocations_tag = 'geoLocations'
        datacite_geolocation_tag = 'geoLocation'
        datacite_geolocation_place_tag = 'geoLocationPlace'
        datacite_geolocation_point_tag = 'geoLocationPoint'
        datacite_geolocation_box_tag = 'geoLocationBox'

        ckan_geolocations = self._get_complex_mapped_value(datacite_geolocations_tag, datacite_geolocation_tag, [ datacite_geolocation_place_tag, datacite_geolocation_point_tag, datacite_geolocation_box_tag ], dataset_dict, metadata_map)

        datacite_geolocations = []
        try:
            # Spatial extension
            pkg_spatial = json.loads(dataset_dict.get('spatial', '{}'))
            if pkg_spatial:
                datacite_geolocation = collections.OrderedDict()
                coordinates_list = self._flatten_list( pkg_spatial.get('coordinates', '[]'), reverse = True)
                if pkg_spatial.get('type', '').lower() == 'polygon' :
                    datacite_geolocation['geoLocationBox'] = ' '.join(coordinates_list[:2] +  coordinates_list[4:6])
                else:
                    datacite_geolocation['geoLocationPoint'] = ' '.join(coordinates_list[:2])
                if ckan_geolocations:
                    datacite_geolocation_place = ckan_geolocations[0].get(self._joinTags([datacite_geolocation_tag, datacite_geolocation_place_tag]), '')
                    if datacite_geolocation_place:
                        datacite_geolocation[datacite_geolocation_place_tag] = datacite_geolocation_place
                datacite_geolocations += [ datacite_geolocation ]
        except:
           # directly defined fields
           for geolocation in ckan_geolocations:
                datacite_geolocation = collections.OrderedDict()
                datacite_geolocation[datacite_geolocation_point_tag] = geolocation.get(self._joinTags([datacite_geolocation_point_tag]), '')
                datacite_geolocation[datacite_geolocation_box_tag] = geolocation.get(self._joinTags([datacite_geolocation_box_tag]), '')
                datacite_geolocation[datacite_geolocation_place_tag] = geolocation.get(self._joinTags([datacite_geolocation_tag, datacite_geolocation_place_tag]), '')
                datacite_geolocations += [ datacite_geolocation ]

        if datacite_geolocations:
            datacite_dict['resource']['geoLocations'] = {'geoLocation': datacite_geolocations }

        # Convert to xml
        converted_package = unparse(datacite_dict, pretty=True)

        return converted_package

    def _flatten_list(self, input_list, reverse = False):
        output_list = []
        for item in input_list:
            if type(item) is not list:
                if reverse:
                     output_list = [str(item)] + output_list
                else:
                     output_list += [str(item)]
            else:
                output_list += self._flatten_list(item, reverse)
        return output_list
