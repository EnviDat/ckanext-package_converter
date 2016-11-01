import ckan.plugins.toolkit as toolkit

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
    print(data_dict)
    dataset_dict = toolkit.get_action('package_show')(context,
                                                      {'id': package_id})
    converted_package = '<?xml version="1.0" encoding="utf-8"?> <resource><identifier identifierType="DOI">' + package_id  + '</identifier></resource>'

    return converted_package
