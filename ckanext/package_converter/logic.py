import ckan.plugins.toolkit as toolkit
from xmltodict import unparse
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
    datacite_dict = {'resource':{'identifier':dataset_dict.get('doi', ' '), '@identifierType':"DOI"}}

    # Authors
    pkg_authors = json.loads(dataset_dict.get("author", "[]"))
    datacite_authors_list = []
    for author in pkg_authors:
        datacite_authors_list += [{'creatorName':author.get('name', ''), 'affiliation':author.get('affiliation', '')}]
    if datacite_authors_list:
        datacite_dict['resource']['creators'] = {'creator': datacite_authors_list }
    converted_package = unparse(datacite_dict)
    print("\n ********** \n" + converted_package + "\n ********** \n")
    return converted_package

