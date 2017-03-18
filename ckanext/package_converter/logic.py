import sys
import ckan.plugins.toolkit as toolkit
from xmltodict import unparse
from pylons import config
import xml.dom.minidom as minidom
import collections

import json

from logging import getLogger

from ckanext.scheming import helpers

log = getLogger(__name__)


# CONSTANT TAGS (TODO: put in separate file)
FIELD_NAME = 'field_name'


@toolkit.side_effect_free
def package_export(context, data_dict):
    '''Return the given CKAN converted to a format.

    :param id: the ID of the dataset
    :type id: string
    :format id: string

    :param format: the format name
    :type format: string
    :format format: string

    :returns: the package metadata
    :rtype: string
    '''

    try:
        package_id = data_dict['id']
    except KeyError:
        raise toolkit.ValidationError({'id': 'missing id'})

    dataset_dict = toolkit.get_action('package_show')(context,
                                                      {'id': package_id})
    file_format = data_dict.get('format', '').lower()

    metadata_map = _schema_map(file_format)
    log.debug( 'Metadata map:'+ repr(metadata_map))

    converted_package = 'No converter available for format ' + file_format

    if (file_format=='datacite'):
         schema_converted_package = _datacite_converter_schema(dataset_dict, metadata_map['metadata'])
         log.debug(schema_converted_package)

         converted_package = _datacite_converter(dataset_dict)
         log.debug(converted_package)

    return schema_converted_package

def _schema_map(format):
    schema = helpers.scheming_get_schema('dataset','dataset')
    schema_map = {'format':format, 'metadata':{}}
    for field in schema['dataset_fields']:
        datacite_field = ''
        if field.get('datacite', False):
            datacite_field = field['datacite']
            schema_map['metadata'][datacite_field] = {FIELD_NAME:field[FIELD_NAME], 'subfields':{}}
        for subfield in field.get('subfields',[]):
            if subfield.get('datacite', False):
                datacite_subfield = subfield['datacite']
                if datacite_field:
                    schema_map['metadata'][datacite_field]['subfields'][datacite_subfield]= {FIELD_NAME:subfield[FIELD_NAME]}
                else:
                    schema_map['metadata'][datacite_subfield] = {FIELD_NAME:field[FIELD_NAME] + '.' + subfield[FIELD_NAME]}

    return schema_map

def _get_single_mapped_value(format_tag, dataset_dict, metadata_map, default=''):

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
            json_field = json.loads(dataset_dict[field])
            if type(json_field) is list:
                json_field = json_field[0]
            value = json_field[subfield]
        except:
            sys.exc_clear()

    if not value:
        value = default
        log.debug ('Cannot map single value for ' + format_tag)

    return (value)

def _joinTags(tag_list, sep='.'):
    return (sep.join([tag for tag in tag_list if tag]))

def _get_complex_mapped_value(group_tag, element_tag, field_tags, dataset_dict, metadata_map):
    values_list = []

    # Simple fields
    simple_fields_object = collections.OrderedDict()
    for field in field_tags:
        simple_field_tag = _joinTags([element_tag, field])
        group_field_tag = _joinTags([group_tag, simple_field_tag])

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
            json_field = json.loads(dataset_dict[ckan_tag])
            if type(json_field) is not list:
                json_field = [json_field]
            for ckan_element in json_field:
                composite_object = collections.OrderedDict()
                for field in field_tags:
                    field_tag = _joinTags([element_tag, field])
                    ckan_subfield_tag = ckan_subfields.get(field_tag, {FIELD_NAME:''})[FIELD_NAME]
                    subfield_value = ckan_element.get(ckan_subfield_tag, '')
                    if subfield_value:
                        composite_object[field_tag] = subfield_value
                if composite_object:
                    values_list += [composite_object]
        except:
            log.debug('Cannot get composite value: (' + ', '.join([group_tag, element_tag] + field_tags )+ '): '+ ckan_tag)

    return values_list

def _valueToDataciteCV (value, datacite_tag, default=''):

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

def _datacite_converter_schema(dataset_dict, metadata_map):
    datacite_dict = collections.OrderedDict()

    # Header
    datacite_dict['resource']=collections.OrderedDict()
    datacite_dict['resource']['@xsi:schemaLocation'] = 'http://datacite.org/schema/kernel-3 http://schema.datacite.org/meta/kernel-3/metadata.xsd'
    datacite_dict['resource']['@xmlns']='http://datacite.org/schema/kernel-3'
    datacite_dict['resource']['@xmlns:xsi']='http://www.w3.org/2001/XMLSchema-instance'

    # Identifier*
    datacite_identifier_tag = 'identifier'
    datacite_dict['resource'][datacite_identifier_tag] = {'#text': _get_single_mapped_value(datacite_identifier_tag, dataset_dict, metadata_map), '@identifierType':'DOI'}

    # Creators
    datacite_creators_tag = 'creators'
    datacite_creator_tag = 'creator'
    datacite_creator_subfields = ['creatorName', 'affiliation', 'nameIdentifier', 'nameIdentifier.nameIdentifierScheme']

    datacite_dict['resource'][datacite_creators_tag] = { datacite_creator_tag: [ ] }
    ckan_creators = _get_complex_mapped_value(datacite_creators_tag, datacite_creator_tag, datacite_creator_subfields, dataset_dict, metadata_map)
    for ckan_creator in ckan_creators:
        datacite_creator = collections.OrderedDict()
        datacite_creator['creatorName'] = ckan_creator.get(_joinTags([datacite_creator_tag, 'creatorName']), '')
        if ckan_creator.get(_joinTags([datacite_creator_tag, 'nameIdentifier']), False):
            datacite_creator['nameIdentifier'] = { '#text': ckan_creator.get(_joinTags([datacite_creator_tag, 'nameIdentifier']), ''),
                                                   '@nameIdentifierScheme':  ckan_creator.get(_joinTags([datacite_creator_tag, 'nameIdentifier', 'nameIdentifierScheme']), '').upper() }
        datacite_creator['affiliation'] = ckan_creator.get(_joinTags([datacite_creator_tag, 'affiliation']), '')
        datacite_dict['resource'][datacite_creators_tag][datacite_creator_tag] += [ datacite_creator ]

    # Titles*
    datacite_titles_tag = 'titles'
    datacite_title_tag = 'title'
    datacite_xml_lang_tag = 'xml:lang' 
    datacite_dict['resource'][datacite_titles_tag] = { datacite_title_tag: [ ] }
    datacite_title_type_tag = 'titleType'
    ckan_titles = _get_complex_mapped_value(datacite_titles_tag, datacite_title_tag, ['', datacite_title_type_tag, datacite_xml_lang_tag], dataset_dict, metadata_map)
    for ckan_title in ckan_titles:
        datacite_title = {'#text': ckan_title.get( datacite_title_tag, ''),
                          '@' + datacite_xml_lang_tag: ckan_title.get( _joinTags([datacite_title_tag, datacite_xml_lang_tag]) , 'en-us')}
        if ckan_title.get( _joinTags([datacite_title_tag, datacite_title_type_tag]) ,''):
            ckan_title_type =  ckan_title.get( _joinTags([datacite_title_tag, datacite_title_type_tag]) , 'other')
            datacite_title['@' + datacite_title_type_tag] =  _valueToDataciteCV (ckan_title_type, datacite_title_type_tag)
        datacite_dict['resource'][datacite_titles_tag][datacite_title_tag] += [ datacite_title ]

    # Publication year*
    datacite_publication_year_tag = 'publicationYear'
    datacite_dict['resource'][datacite_publication_year_tag] = {'#text': _get_single_mapped_value(datacite_publication_year_tag, dataset_dict, metadata_map) }

    # Publisher
    datacite_publisher_tag = 'publisher'
    publisher_value = _get_single_mapped_value(datacite_publisher_tag, dataset_dict, metadata_map) 
    if (publisher_value):
        datacite_dict['resource'][datacite_publisher_tag] = {'#text': _get_single_mapped_value(datacite_publisher_tag, dataset_dict, metadata_map) }

    # Subjects
    datacite_subjects_tag = 'subjects'
    datacite_subject_tag = 'subject'
    datacite_subjects = []
    # Defined by usual field
    ckan_subjects = _get_complex_mapped_value(datacite_subjects_tag, datacite_subject_tag, [ '', datacite_xml_lang_tag ], dataset_dict, metadata_map)
    for ckan_subject in ckan_subjects:
        datacite_subject = {'#text': ckan_subject.get( datacite_subject_tag, ''),
                          '@' + datacite_xml_lang_tag: ckan_subject.get( _joinTags([datacite_subject_tag, datacite_xml_lang_tag]) , 'en-us')}
        datacite_subjects += [ datacite_subject ]
    # Defined by autocomplete tags
    if metadata_map.get(_joinTags([datacite_subjects_tag, datacite_subject_tag]),{FIELD_NAME:''})[FIELD_NAME].find('tag')>=0:
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
    ckan_contributors = _get_complex_mapped_value(datacite_contributors_tag, datacite_contributor_tag, datacite_contributor_subfields, dataset_dict, metadata_map)
    for ckan_contributor in ckan_contributors:
        datacite_contributor = collections.OrderedDict()
        datacite_contributor['contributorName'] = ckan_contributor.get(_joinTags([datacite_contributor_tag, 'contributorName']), '')
        datacite_contributor['affiliation'] = ckan_contributor.get(_joinTags([datacite_contributor_tag, 'affiliation']), '')
        if ckan_contributor.get(datacite_contributor_tag + '.' + 'nameIdentifier', False):
            datacite_contributor['nameIdentifier'] = { '#text': ckan_contributor.get(_joinTags([datacite_contributor_tag, 'nameIdentifier']), ''),
                                                       '@nameIdentifierScheme':  ckan_contributor.get(_joinTags([datacite_contributor_tag, 'nameIdentifier', 'nameIdentifierScheme']) , '').upper() }
        ckan_contributor_type = ckan_contributor.get(_joinTags([datacite_contributor_tag, 'contributorType']), 'ContactPerson')
        datacite_contributor['@contributorType'] = _valueToDataciteCV (ckan_contributor_type, 'contributorType')
        datacite_contributors += [ datacite_contributor ]

    if datacite_contributors:
        datacite_dict['resource'][datacite_contributors_tag] = { datacite_contributor_tag: datacite_contributors }

    # Dates
    datacite_dates_tag = 'dates'
    datacite_date_tag = 'date'
    datacite_date_type_tag = 'dateType'
    datacite_dates = []
    ckan_dates = _get_complex_mapped_value(datacite_dates_tag, datacite_date_tag, [ '', datacite_date_type_tag ], dataset_dict, metadata_map)
    for ckan_date in ckan_dates:
        datacite_date =  {'#text': ckan_date.get(datacite_date_tag, ''),
                          '@' + datacite_date_type_tag: ckan_date.get(_joinTags([datacite_date_tag, datacite_date_type_tag]), 'Valid').title()}
        datacite_dates += [ datacite_date ]
    if datacite_dates:
        datacite_dict['resource'][datacite_dates_tag] = { datacite_date_tag: datacite_dates }

    # Language
    datacite_language_tag = 'language'
    datacite_dict['resource'][datacite_language_tag] = {'#text': _get_single_mapped_value(datacite_language_tag, dataset_dict, metadata_map, 'en') }

    # ResourceType
    datacite_resource_type_tag = 'resourceType'
    datacite_resource_type_general_tag = 'resourceTypeGeneral'
    ckan_resource_type = _get_complex_mapped_value('', datacite_resource_type_tag, [ '', datacite_resource_type_general_tag ], dataset_dict, metadata_map)
    if ckan_resource_type:
         ckan_resource_type_general = ckan_resource_type[0].get(_joinTags([datacite_resource_type_tag, datacite_resource_type_general_tag]))
         datacite_resource_type_general = _valueToDataciteCV(ckan_resource_type_general, datacite_resource_type_general_tag, default = 'Dataset')
         datacite_dict['resource'][datacite_resource_type_tag] = { '#text': ckan_resource_type[0].get(datacite_resource_type_tag, ''),
                                                                   '@' + datacite_resource_type_general_tag: datacite_resource_type_general }

    # Alternate Identifier (CKAN URL)
    ckan_package_url = config.get('ckan.site_url','') + toolkit.url_for(controller='package', action='read', id=dataset_dict.get('name', ''))
    datacite_dict['resource']['alternateIdentifiers']={'alternateIdentifier':[{'#text':ckan_package_url, '@alternateIdentifierType':'URL'}]}
    # legacy
    if dataset_dict.get('url', ''):
        datacite_dict['resource']['alternateIdentifiers']['alternateIdentifier'] += [{'#text': dataset_dict.get('url', ''), '@alternateIdentifierType':'URL'}]

    # Version
#    if  dataset_dict.get('version', ''):
#        datacite_dict['resource']['version'] = dataset_dict.get('version', '')

    # Rights
#    if dataset_dict.get('license_title', ''):
#        datacite_dict['resource']['rightsList'] = {'rights':[{'#text': dataset_dict.get('license_title', '')}]}

    # Description
    datacite_descriptions_tag = 'descriptions'
    datacite_description_tag = 'description'
    datacite_description_type_tag = 'descriptionType'
    datacite_descriptions = []
    ckan_descriptions = _get_complex_mapped_value(datacite_descriptions_tag, datacite_description_tag, [ '', datacite_xml_lang_tag, datacite_description_type_tag], dataset_dict, metadata_map)
    for ckan_description in ckan_descriptions:
        datacite_description = {'#text': ckan_description.get( datacite_description_tag, ''),
                          '@' + datacite_description_type_tag: ckan_description.get( _joinTags([datacite_description_tag, datacite_description_type_tag]) , 'Abstract'),
                          '@' + datacite_xml_lang_tag: ckan_description.get( _joinTags([datacite_description_tag, datacite_xml_lang_tag]) , 'en-us')}
        datacite_descriptions += [ datacite_description ]
    if datacite_descriptions:
        datacite_dict['resource'][datacite_descriptions_tag] = { datacite_description_tag: datacite_descriptions }

    # Convert to xml
    converted_package = unparse(datacite_dict)

    return converted_package

def _datacite_converter(dataset_dict):

    datacite_dict = collections.OrderedDict()
    datacite_dict['resource']=collections.OrderedDict()
    datacite_dict['resource']['@xsi:schemaLocation'] = 'http://datacite.org/schema/kernel-3 http://schema.datacite.org/meta/kernel-3/metadata.xsd'
    datacite_dict['resource']['@xmlns']='http://datacite.org/schema/kernel-3'
    datacite_dict['resource']['@xmlns:xsi']='http://www.w3.org/2001/XMLSchema-instance'

    # Identifier
    datacite_dict['resource']['identifier'] = {'#text':dataset_dict.get('doi', ''), '@identifierType':'DOI'}

    # Creators
    try:
        pkg_authors = json.loads(dataset_dict.get('author', '[]'))
    except:
        pkg_authors = []

    dc_creators_list = []
    for author in pkg_authors:
        dc_creator = collections.OrderedDict()
        if author.get('name', False):
            dc_creator['creatorName'] = author.get('name', '')
        if author.get('affiliation', False):
            dc_creator['affiliation'] = author.get('affiliation', '')
        if author.get('identifier', False):
            dc_creator['nameIdentifier'] = {'#text':author.get('identifier', '')}
            if author.get('identifier_scheme', False):
                dc_creator['nameIdentifier']['@nameIdentifierScheme'] = author.get('identifier_scheme', '').upper()
        if dc_creator:
            dc_creators_list += [ dc_creator ]
    if dc_creators_list:
        datacite_dict['resource']['creators'] = {'creator': dc_creators_list }

    # Titles
    dc_titles = []
    if dataset_dict.get('title', ''):
        dc_titles += [ {'#text': dataset_dict.get('title', ''), '@xml:lang': 'en-us' } ]

    title_type_dict = { 'alternative_title':'AlternativeTitle', 'subtitle':'Subtitle', 'translated_title':'TranslatedTitle', 'other':'Other' }
    try:
        pkg_subtitles = json.loads(dataset_dict.get('subtitle', '[]'))
    except:
        pkg_subtitles = []
    for subtitle in pkg_subtitles:
        dc_title = collections.OrderedDict()
        if subtitle.get('subtitle', False):
            dc_title['#text'] = subtitle.get('subtitle', '')
        if subtitle.get('type', False):
            dc_title['@titleType'] = title_type_dict.get(subtitle.get('type', ''), 'Other')
        if subtitle.get('language', False):
            dc_title['@xml:lang'] = subtitle.get('language', '')
        if dc_title:
             dc_titles += [ dc_title ]
    if dc_titles:
        datacite_dict['resource']['titles'] = {'title': dc_titles }

    # Publisher & publication year
    try:
        pkg_publication = json.loads(dataset_dict.get('publication', '{}'))
    except:
        pkg_publication = {}
    if  pkg_publication.get('publisher',''):
        datacite_dict['resource']['publisher'] = {'#text': pkg_publication.get('publisher','')}
    if  pkg_publication.get('publication_year',''):
        datacite_dict['resource']['publicationYear'] = {'#text': pkg_publication.get('publication_year','')}

    # Subjects
    dc_subjects = []
    for tag in dataset_dict.get('tags', []):
        tag_name = tag.get('display_name', tag.get('name',''))
        dc_subjects += [{ '@xml:lang':'en-us', '#text':tag_name}]
    if dc_subjects:
        datacite_dict['resource']['subjects'] = {'subject':dc_subjects}

    # Contributor (contact person)
    try:
        pkg_contributor = json.loads(dataset_dict.get('maintainer', '{}'))
    except:
        pkg_contributor = {}
    if pkg_contributor:
        dc_contributor = collections.OrderedDict()
        if pkg_contributor.get('name', False):
            dc_contributor['contributorName'] = pkg_contributor.get('name', '')
        if pkg_contributor.get('affiliation', False):
            dc_contributor['affiliation'] = pkg_contributor.get('affiliation', '')
        if pkg_contributor.get('identifier', False):
            dc_contributor['nameIdentifier'] = {'#text':pkg_contributor.get('identifier', '')}
            if pkg_contributor.get('identifier_scheme', False):
                dc_contributor['nameIdentifier']['@nameIdentifierScheme'] = pkg_contributor.get('identifier_scheme', '').upper()
        if dc_contributor:
            dc_contributor['@contributorType'] = 'ContactPerson'
            datacite_dict['resource']['contributors'] = {'contributor': [dc_contributor] }

    # Dates
    try:
        pkg_dates = json.loads(dataset_dict.get('date', '[]'))
    except:
        pkg_dates = []
    dates_list = []
    for date in  pkg_dates:
        dc_date =  collections.OrderedDict()
        if date.get('date', ''):
            dc_date['#text'] = date.get('date', '')
            if date.get('end_date', ''):
                dc_date['#text'] += '/' + date.get('end_date', '')
        if date.get('date_type', ''):
            dc_date['@dateType'] = date.get('date_type', '').title()
        if dc_date:
            dates_list += [dc_date]
    if dates_list:
        datacite_dict['resource']['dates']={'date':dates_list}

    # Language
    if dataset_dict.get('language', ''):
        datacite_dict['resource']['language'] = dataset_dict.get('language', 'en')

    # ResourceType
    resource_type_general_dict ={'audiovisual': 'Audiovisual', 'collection': 'Collection', 'dataset': 'Dataset', 'event': 'Event', 'image': 'Image', 
                                 'interactive_resource': 'InteractiveResource', 'model': 'Model', 'physical_object': 'PhysicalObject', 
                                 'service': 'Service', 'software': 'Software', 'sound': 'Sound', 'text': 'Text', 'workflow': 'Workflow', 'other': 'Other'}
    if dataset_dict.get('resource_type', ''):
        resource_type_general = resource_type_general_dict.get(dataset_dict.get('resource_type_general', 'other'), 'Other')
        datacite_dict['resource']['resourceType'] = {'#text': dataset_dict.get('resource_type',''), '@resourceTypeGeneral':resource_type_general}

    # Alternate Identifier (CKAN URL)
    ckan_package_url = config.get('ckan.site_url','') + toolkit.url_for(controller='package', action='read', id=dataset_dict.get('name', ' '))
    datacite_dict['resource']['alternateIdentifiers']={'alternateIdentifier':[{'#text':ckan_package_url, '@alternateIdentifierType':'URL'}]}
    # legacy
    if dataset_dict.get('url', ''):
        datacite_dict['resource']['alternateIdentifiers']['alternateIdentifier'] += [{'#text': dataset_dict.get('url', ''), '@alternateIdentifierType':'URL'}]

    # Related identifiers (TODO)

    # Sizes
    datacite_sizes = []
    for resource in dataset_dict.get('resources', []):
        if resource.get('size', ''):
            datacite_sizes += [{'#text': resource.get('size', ' ') + ' bytes'}]
    if datacite_sizes:
         datacite_dict['resource']['sizes'] = {'size': datacite_sizes}

    # Formats
    datacite_formats = []
    for resource in dataset_dict.get('resources', []):
        if resource.get('format', resource.get('mimetype', resource.get('mimetype_inner', ''))):
            format = {'#text': resource.get('format', '')}
            if format not in datacite_formats:
                datacite_formats += [format]
    if datacite_formats:
         datacite_dict['resource']['formats'] = {'format': datacite_formats}

    # Version
    if  dataset_dict.get('version', ''):
        datacite_dict['resource']['version'] = dataset_dict.get('version', '')

    # Rights
    if dataset_dict.get('license_title', ''):
        datacite_dict['resource']['rightsList'] = {'rights':[{'#text': dataset_dict.get('license_title', '')}]}

    # Description
    if dataset_dict.get('notes', ''):
        datacite_dict['resource']['descriptions'] = {'description': {'#text':dataset_dict.get('notes', ' '), '@xml:lang':'en-us', '@descriptionType':'Abstract'}}

    # GeoLocation
    datacite_geolocation = collections.OrderedDict()
    if  dataset_dict.get('spatial_info', ''):
       datacite_geolocation['geoLocationPlace'] = dataset_dict.get('spatial_info', '')
    try:
        pkg_spatial = json.loads(dataset_dict.get('spatial', '{}'))
    except:
        pkg_spatial =  collections.OrderedDict()
    if pkg_spatial:
       coordinates_list = _flatten_list( pkg_spatial.get('coordinates', '[]'), reverse = True)
       if pkg_spatial.get('type', '').lower() == 'polygon' :
            datacite_geolocation['geoLocationBox'] = ' '.join(coordinates_list[:2] +  coordinates_list[4:6])
       else:
            datacite_geolocation['geoLocationPoint'] = ' '.join(coordinates_list[:2])
    if datacite_geolocation:
       datacite_dict['resource']['geoLocations'] = {'geoLocation': [datacite_geolocation]}

    # Converto to xml
    converted_package = unparse(datacite_dict)

    return converted_package

def _flatten_list(input_list, reverse = False):
    output_list = []
    for item in input_list:
        if type(item) is not list:
            if reverse:
                 output_list = [str(item)] + output_list
            else:
                 output_list += [str(item)]
        else:
            output_list += _flatten_list(item, reverse)
    return output_list

