from ckanext.package_converter.model.metadata_format import MetadataFormats
from ckanext.package_converter.model.converter import BaseConverter
from ckanext.package_converter.model.record import Record, JSONRecord, XMLRecord
from ckanext.package_converter.model.scheming_converter import SchemingConverter

from logging import getLogger
log = getLogger(__name__)

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
            converted_xml_record = XMLRecord.from_record(converted_record)
            #log.debug("Validating record..." + str(converted_xml_record.validate()))
            return converted_xml_record
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
        datacite_creator_subfields = ['creatorName', 'givenName', 'familyName', 'affiliation', 'nameIdentifier', 'nameIdentifier.nameIdentifierScheme']

        datacite_dict['resource'][datacite_creators_tag] = { datacite_creator_tag: [ ] }
        ckan_creators = self._get_complex_mapped_value(datacite_creators_tag, datacite_creator_tag, datacite_creator_subfields, dataset_dict, metadata_map)
        for ckan_creator in ckan_creators:
            datacite_creator = collections.OrderedDict()
            
            creator_full_name = ckan_creator.get(self._joinTags([datacite_creator_tag, 'creatorName']), '')
            if creator_full_name:
                datacite_creator['creatorName'] = creator_full_name
            else:
                creator_family_name = ckan_creator.get(self._joinTags([datacite_creator_tag, 'familyName']), '').strip()
                creator_given_name = ckan_creator.get(self._joinTags([datacite_creator_tag, 'givenName']), '').strip()
                datacite_creator['creatorName'] = creator_family_name
                if creator_given_name:
                    datacite_creator['givenName'] = creator_given_name
                    datacite_creator['familyName'] = creator_family_name 
                    datacite_creator['creatorName'] = creator_given_name + ' ' + creator_family_name 
            if ckan_creator.get(self._joinTags([datacite_creator_tag, 'nameIdentifier']), False):
                datacite_creator['nameIdentifier'] = { '#text': ckan_creator.get(self._joinTags([datacite_creator_tag, 'nameIdentifier']), ''),
                                                       '@nameIdentifierScheme':  ckan_creator.get(self._joinTags([datacite_creator_tag, 'nameIdentifier', 'nameIdentifierScheme']), 'orcid').upper() }
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
        datacite_contributor_subfields = ['contributorName', 'givenName', 'familyName', 'affiliation', 'contributorType', 'nameIdentifier', 'nameIdentifier.nameIdentifierScheme']
        datacite_contributors = []
        ckan_contributors = self._get_complex_mapped_value(datacite_contributors_tag, datacite_contributor_tag, datacite_contributor_subfields, dataset_dict, metadata_map)
        for ckan_contributor in ckan_contributors:
            datacite_contributor = collections.OrderedDict()

            contributor_full_name = ckan_contributor.get(self._joinTags([datacite_contributor_tag, 'contributorName']), '')
            if contributor_full_name:
                datacite_contributor['contributorName'] = contributor_full_name
            else:
                contributor_family_name = ckan_contributor.get(self._joinTags([datacite_contributor_tag, 'familyName']), '').strip()
                contributor_given_name = ckan_contributor.get(self._joinTags([datacite_contributor_tag, 'givenName']), '').strip()
                datacite_contributor['contributorName'] = contributor_family_name
                if contributor_given_name:
                    datacite_contributor['givenName'] = contributor_given_name
                    datacite_contributor['familyName'] = contributor_family_name 
                    datacite_contributor['contributorName'] = contributor_given_name + ' ' + contributor_family_name 

            if ckan_contributor.get(datacite_contributor_tag + '.' + 'nameIdentifier', False):
                datacite_contributor['nameIdentifier'] = { '#text': ckan_contributor.get(self._joinTags([datacite_contributor_tag, 'nameIdentifier']), ''),
                                                           '@nameIdentifierScheme':  ckan_contributor.get(self._joinTags([datacite_contributor_tag, 'nameIdentifier', 'nameIdentifierScheme']) , 'orcid').upper() }
            datacite_contributor['affiliation'] = ckan_contributor.get(self._joinTags([datacite_contributor_tag, 'affiliation']), '')
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
        #ckan_package_url = config.get('ckan.site_url','') + toolkit.url_for(controller='dataset', action='read', id=dataset_dict.get('name', ''))
        ckan_package_url = config.get('ckan.site_url','') + '/dataset/' + dataset_dict.get('name', dataset_dict.get('id'))
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
                datacite_sizes += [{'#text': str(resource.get('size', ' ')) + ' bytes'}]
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
        log.debug("ckan_geolocations=" + str(ckan_geolocations))
        datacite_geolocations = []
        try:
            # Spatial extension
            pkg_spatial = json.loads(dataset_dict['spatial'])
            log.debug("pkg_spatial=" + str(pkg_spatial))
            if pkg_spatial:
                coordinates_list = self._flatten_list( pkg_spatial.get('coordinates', '[]'), reverse = True)
                if pkg_spatial.get('type', '').lower() == 'polygon' :
                    datacite_geolocation = collections.OrderedDict()
                    datacite_geolocation['geoLocationBox'] = ' '.join(coordinates_list[:2] +  coordinates_list[4:6])
                    datacite_geolocations += [ datacite_geolocation ]
                else:
                    if pkg_spatial.get('type', '').lower() == 'multipoint' :
                        for point in pkg_spatial.get('coordinates', ''):
                            log.debug("point=" + str(point))
                            datacite_geolocation = collections.OrderedDict()
                            datacite_geolocation['geoLocationPoint'] = ' '.join(self._flatten_list( point, reverse = True))
                            datacite_geolocations += [ datacite_geolocation ]
                    else:
                        datacite_geolocation = collections.OrderedDict()
                        datacite_geolocation['geoLocationPoint'] = ' '.join(coordinates_list[:2])
                        datacite_geolocations += [ datacite_geolocation ]
                if ckan_geolocations:
                    datacite_geolocation_place = ckan_geolocations[0].get(self._joinTags([datacite_geolocation_tag, datacite_geolocation_place_tag]), '')
                    if datacite_geolocation_place:
                        datacite_geolocation = collections.OrderedDict()
                        datacite_geolocation[datacite_geolocation_place_tag] = datacite_geolocation_place
                        datacite_geolocations += [ datacite_geolocation ]
        except:
           # directly defined fields
           for geolocation in ckan_geolocations:
                datacite_geolocation = collections.OrderedDict()
                if geolocation.get(self._joinTags([datacite_geolocation_point_tag])):
                    datacite_geolocation[datacite_geolocation_point_tag] = geolocation.get(self._joinTags([datacite_geolocation_point_tag]), '')
                if geolocation.get(self._joinTags([datacite_geolocation_box_tag])):
                    datacite_geolocation[datacite_geolocation_box_tag] = geolocation.get(self._joinTags([datacite_geolocation_box_tag]), '')
                datacite_geolocation[datacite_geolocation_place_tag] = geolocation.get(self._joinTags([datacite_geolocation_tag, datacite_geolocation_place_tag]), '')
                datacite_geolocations += [ datacite_geolocation ]

        if datacite_geolocations:
            log.debug("datacite_geolocations=" + str(datacite_geolocations))
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
        
    def flatten_list(self, input_list, reverse = False):
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

from logging import getLogger
log = getLogger(__name__)

class Datacite31SchemingResourceConverter(Datacite31SchemingConverter):

    def __init__(self):
        Datacite31SchemingConverter.__init__(self)
        ckan_resource_base_format = MetadataFormats().get_metadata_formats('ckan_resource')[0]
        self.input_format = ckan_resource_base_format

    def _datacite_converter_schema(self, resource_dict):
        try:
            schema_map = self._get_schema_map(self.output_format.get_format_name())
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
            datacite_dict['resource'][datacite_identifier_tag] = {'#text': self._get_single_mapped_value(datacite_identifier_tag, resource_dict, metadata_resource_map), '@identifierType':'DOI'}

            # Titles*
            datacite_titles_tag = 'titles'
            datacite_title_tag = 'title'
            datacite_xml_lang_tag = 'xml:lang'
            datacite_dict['resource'][datacite_titles_tag] = { datacite_title_tag: [ ] }
            datacite_title_type_tag = 'titleType'
            ckan_titles = self._get_complex_mapped_value(datacite_titles_tag, datacite_title_tag, ['', datacite_title_type_tag, datacite_xml_lang_tag], resource_dict, metadata_resource_map)
            for ckan_title in ckan_titles:
                datacite_title = {'#text': ckan_title.get( datacite_title_tag, ''),
                                  '@' + datacite_xml_lang_tag: ckan_title.get( self._joinTags([datacite_title_tag, datacite_xml_lang_tag]) , 'en-us')}
                if ckan_title.get( self._joinTags([datacite_title_tag, datacite_title_type_tag]) ,''):
                    ckan_title_type =  ckan_title.get( self._joinTags([datacite_title_tag, datacite_title_type_tag]) , 'other')
                    datacite_title['@' + datacite_title_type_tag] =  self._valueToDataciteCV (ckan_title_type, datacite_title_type_tag)
                datacite_dict['resource'][datacite_titles_tag][datacite_title_tag] += [ datacite_title ]

            # Alternate Identifier (CKAN URL) Decide which is landing page, resource or package
            ckan_resource_url = config.get('ckan.site_url','') + toolkit.url_for(controller='dataset', action='resource_read',
                                                                             id = resource_dict.get('package_id', ''),
                                                                             resource_id = resource_dict.get('id', ''))
            datacite_dict['resource']['alternateIdentifiers']={'alternateIdentifier':[{'#text':ckan_resource_url, '@alternateIdentifierType':'URL'}]}

            # Sizes (not defined in scheming, taken from default CKAN resource)
            datacite_size_group_tag = 'sizes'
            datacite_size_tag = 'size'
            datacite_sizes = []
            if resource_dict.get('size', ''):
                datacite_sizes += [{'#text': resource_dict.get('size', ' ') + ' bytes'}]
            if datacite_sizes:
                datacite_dict['resource'][datacite_size_group_tag] = {datacite_size_tag: datacite_sizes}

            # Formats (get from resources)
            datacite_format_group_tag = 'formats'
            datacite_format_tag = 'format'
            datacite_formats = []

            resource_format = self._get_single_mapped_value( self._joinTags([datacite_format_group_tag, datacite_format_tag]),
                                                           resource_dict, metadata_resource_map, 
                                                           default=resource_dict.get('mimetype', resource_dict.get('mimetype_inner', '')))
            if resource_format:
                datacite_formats += [{'#text': resource_format}]
            if datacite_formats:
                datacite_dict['resource'][datacite_format_group_tag] = {datacite_format_tag: datacite_formats}

            # Version
            datacite_version_tag = 'version'
            datacite_version = self._get_single_mapped_value(datacite_version_tag, resource_dict, metadata_resource_map, '')
            if datacite_version:
                datacite_dict['resource'][datacite_version_tag] = {'#text': datacite_version }

            # Description
            datacite_descriptions_tag = 'descriptions'
            datacite_description_tag = 'description'
            datacite_description_type_tag = 'descriptionType'
            datacite_descriptions = []
            ckan_descriptions = self._get_complex_mapped_value(datacite_descriptions_tag, datacite_description_tag, [ '', datacite_xml_lang_tag, datacite_description_type_tag], resource_dict, metadata_resource_map)
            for ckan_description in ckan_descriptions:
                datacite_description = {'#text': ckan_description.get( datacite_description_tag, ''),
                                  '@' + datacite_description_type_tag: ckan_description.get( self._joinTags([datacite_description_tag, datacite_description_type_tag]) , 'Abstract'),
                                  '@' + datacite_xml_lang_tag: ckan_description.get( self._joinTags([datacite_description_tag, datacite_xml_lang_tag]) , 'en-us')}
                datacite_descriptions += [ datacite_description ]
            if datacite_descriptions:
                datacite_dict['resource'][datacite_descriptions_tag] = { datacite_description_tag: datacite_descriptions }

            # inherit from package
            package_dict = resource_dict.get('package_dict')
            if package_dict:
                datacite_package_dict = parse(super(Datacite31SchemingResourceConverter, self)._datacite_converter_schema(package_dict))
                datacite_dict['resource'] = self._inherit_from_package(datacite_dict['resource'], datacite_package_dict['resource'])

            # Convert to xml
            converted_package = unparse(datacite_dict, pretty=True)
        except Exception as e:
            log.exception(e)
            return None
        return converted_package

    def _inherit_from_package(self, datacite_dict, datacite_package_dict):
        def merge_dict_lists(dict1, dict2):
            for key in dict1.keys():
                if type(dict1[key]) is list:
                    list1 = dict1[key]
                    list2 = dict2.get(key, [])
                    if type(dict2.get(key, [])) is not list:
                        list2 = [list2]
                    for item in list2:
                        if item not in list1:
                            dict1[key] += [item]
            return dict1

        try:
            # values from the resource are added or replace the package
            replace = ['identifier', 'sizes', 'version', 'formats', 'resourceType', 'alternateIdentifiers']
            for key in datacite_dict.keys():
                if (key in replace) or (type(datacite_dict[key]) is not dict):
                        datacite_package_dict[key] = datacite_dict[key]
                else:
                    datacite_package_dict[key] = merge_dict_lists(datacite_dict[key], datacite_package_dict.get(key,{}))
            return (datacite_package_dict)
        except Exception as e:
            log.exception(e)
            return datacite_dict
