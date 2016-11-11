import ckan.plugins.toolkit as toolkit
from xmltodict import unparse
from pylons import config
import xml.dom.minidom as minidom
import collections

import json

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
    file_format = data_dict.get("format", "")

    converted_package = "No converter available for format " + file_format

    if (file_format.lower()=='datacite'):
         converted_package = _datacite_converter(dataset_dict)

    return converted_package


def _datacite_converter(dataset_dict):

    datacite_dict = collections.OrderedDict()
    datacite_dict['resource']=collections.OrderedDict()
    datacite_dict['resource']["@xsi:schemaLocation"] = "http://datacite.org/schema/kernel-3 http://schema.datacite.org/meta/kernel-3/metadata.xsd"
    datacite_dict['resource']["@xmlns"]="http://datacite.org/schema/kernel-3"
    datacite_dict['resource']["@xmlns:xsi"]="http://www.w3.org/2001/XMLSchema-instance"

    # Identifier
    datacite_dict['resource']['identifier'] = {"#text":dataset_dict.get('doi', ''), '@identifierType':"DOI"}

    # Creators
    try:
        pkg_authors = json.loads(dataset_dict.get("author", "[]"))
    except:
        pkg_authors = []

    dc_creators_list = []
    for author in pkg_authors:
        dc_creator ={}
        if author.get('name', False):
            dc_creator['creatorName'] = author.get('name', '')
        if author.get('affiliation', False):
            dc_creator['affiliation'] = author.get('affiliation', '')
        if author.get('identifier', False):
            dc_creator['nameIdentifier'] = {"#text":author.get('identifier', '')}
        if author.get('identifier_scheme', False):
            dc_creator['nameIdentifier']['@nameIdentifierScheme'] = author.get('identifier_scheme', '').upper()
        if dc_creator:
            dc_creators_list += [ dc_creator ]
    if dc_creators_list:
        datacite_dict['resource']['creators'] = {'creator': dc_creators_list }

    # Titles
    dc_titles = []
    if dataset_dict.get("title", ""):
        dc_titles += [ {"#text": dataset_dict.get("title", "")} ]

    title_type_dict = { "alternative_title":"AlternativeTitle", "subtitle":"Subtitle", "translated_title":"TranslatedTitle", "other":"Other" }
    try:
        pkg_subtitles = json.loads(dataset_dict.get("subtitle", "[]"))
    except:
        pkg_subtitles = []
    for subtitle in pkg_subtitles:
        dc_title = {}
        if subtitle.get('subtitle', False):
            dc_title['#text'] = subtitle.get('subtitle', '')
        if subtitle.get('type', False):
            dc_title['@titleType'] = title_type_dict.get(subtitle.get('type', ''), "Other")
        if subtitle.get('language', False):
            dc_title['@xml:lang'] = subtitle.get('language', '')
        if dc_title:
             dc_titles += [ dc_title ]
    if dc_titles:
        datacite_dict['resource']['titles'] = {'title': dc_titles }

    # Publisher & publication year
    try:
        pkg_publication = json.loads(dataset_dict.get("publication", "{}"))
    except:
        pkg_publication = {}
    if  pkg_publication.get("publisher",""):
        datacite_dict['resource']['publisher'] = {"#text": pkg_publication.get("publisher","")}
    if  pkg_publication.get("publication_year",""):
        datacite_dict['resource']['publicationYear'] = {"#text": pkg_publication.get("publication_year","")}

    # Subjects
    dc_subjects = []
    for tag in dataset_dict.get("tags", []):
        tag_name = tag.get("display_name", tag.get("name",""))
        dc_subjects += [{ "@xml:lang":"en-us", "#text":tag_name}]
    if dc_subjects:
        datacite_dict['resource']['subjects'] = {'subject':dc_subjects}

    # Contributor (contact person)
    try:
        pkg_contributor = json.loads(dataset_dict.get("maintainer", "{}"))
    except:
        pkg_contributor = {}
    if pkg_contributor:
        dc_contributor ={}
        if pkg_contributor.get('name', False):
            dc_contributor['contributorName'] = author.get('name', '')
        if pkg_contributor.get('affiliation', False):
            dc_contributor['affiliation'] = author.get('affiliation', '')
        if pkg_contributor.get('identifier', False):
            dc_contributor['nameIdentifier'] = {"#text":author.get('identifier', '')}
        if pkg_contributor.get('identifier_scheme', False):
            dc_contributor['nameIdentifier']['@nameIdentifierScheme'] = author.get('identifier_scheme', '').upper()
        if dc_contributor:
            dc_contributor['contributorType'] = 'ContactPerson'
            datacite_dict['resource']['contributors'] = {'contributor': [dc_contributor] }

    # Dates (TODO)
    try:
        pkg_dates = json.loads(dataset_dict.get("date", "[]"))
    except:
        pkg_dates = []
    dates_list = []
    for date in  pkg_dates:
        dc_date = {}
        if date.get('date', ""):
            dc_date['#text'] = date.get('date', "")
            if date.get('end_date', ""):
                dc_date['#text'] += '/' + date.get('end_date', "")
        if date.get('date_type', ""):
            dc_date['@dateType'] = date.get('date_type', "").title()
        if dc_date:
            dates_list += [dc_date]
    if dates_list:
        datacite_dict['resource']['dates']={'date':dates_list}

    # Language
    datacite_dict['resource']['language'] = dataset_dict.get("language", "en")

    # ResourceType
    resource_type_general_dict ={"audiovisual": "Audiovisual", "collection": "Collection", "dataset": "Dataset", "event": "Event", "image": "Image", 
                                 "interactive_resource": "InteractiveResource", "model": "Model", "physical_object": "PhysicalObject", 
                                 "service": "Service", "software": "Software", "sound": "Sound", "text": "Text", "workflow": "Workflow", "other": "Other"}
    if dataset_dict.get("resource_type", ""):
        resource_type_general = resource_type_general_dict.get(dataset_dict.get("resource_type_general", "other"), "Other")
        datacite_dict['resource']['resourceType'] = {"#text": dataset_dict.get("resource_type",""), '@resourceTypeGeneral':resource_type_general}

    # Alternate Identifier (CKAN URL)
    ckan_package_url = config.get('ckan.site_url',"") + toolkit.url_for(controller='package', action='read', id=dataset_dict.get('name', ' '))
    datacite_dict['resource']['alternateIdentifiers']={'AlternateIdentifier':[{"#text":ckan_package_url, '@alternateIdentifierType':"URL"}]}
    # legacy
    if dataset_dict.get('url', ''):
        datacite_dict['resource']['alternateIdentifiers']['AlternateIdentifier'] += [{"#text": dataset_dict.get('url', ''), '@alternateIdentifierType':"URL"}]

    # Related identifiers (TODO)

    # Sizes
    datacite_sizes = []
    for resource in dataset_dict.get("resources", []):
        if resource.get("size", ""):
            datacite_sizes += [{"#text": resource.get("size", " ") + " bytes"}]
    if datacite_sizes:
         datacite_dict['resource']['sizes'] = {'size': datacite_sizes}

    # Formats
    datacite_formats = []
    for resource in dataset_dict.get("resources", []):
        if resource.get("format", resource.get("mimetype", resource.get("mimetype_inner", ""))):
            format = {"#text": resource.get("format", "")}
            if format not in datacite_formats:
                datacite_formats += [format]
    if datacite_formats:
         datacite_dict['resource']['formats'] = {'format': datacite_formats}

    # Version
    if  dataset_dict.get("version", ""):
        datacite_dict['resource']['version'] = dataset_dict.get("version", "")

    # Rights
    if dataset_dict.get("license_title", ""):
        datacite_dict['resource']['rightsList'] = {"rights":[{"#text": dataset_dict.get("license_title", "")}]}

    # Description
    if dataset_dict.get("notes", ""):
        datacite_dict['resource']['descriptions'] = {'description': {"#text":dataset_dict.get("notes", " "), "@xml:lang":"en-us", "@descriptionType":"Abstract"}}

    # GeoLocation
    datacite_geolocation = {}
    if  dataset_dict.get("spatial_info", ""):
       datacite_geolocation["geoLocationPlace"] = dataset_dict.get("spatial_info", "")

    try:
        pkg_spatial = json.loads(dataset_dict.get("spatial", "{}"))
    except:
        pkg_spatial = {}
    if pkg_spatial:
       coordinates_list = _flatten_list( pkg_spatial.get("coordinates", "[]"))
       coordinates = " ".join(coordinates_list)
       if pkg_spatial.get("type", "").lower() == "polygon" :
            datacite_geolocation["geoLocationBox"] = coordinates
       else:
            datacite_geolocation["geoLocationPoint"] = coordinates

    if datacite_geolocation:
       datacite_dict['resource']['geoLocations'] = {"geoLocation": [datacite_geolocation]}

    # Converto to xml
    converted_package = unparse(datacite_dict)

    return converted_package

def _flatten_list(input_list):
    output_list = []
    for item in input_list:
        if type(item) is not list:
            output_list += [str(item)]
        else:
            output_list += _flatten_list(item)
    return output_list

