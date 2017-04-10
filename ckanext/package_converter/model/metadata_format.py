from flufl.enum import Enum

class FormatType(Enum):
    XML = 'xml'
    JSON = 'json'
    TEXT = 'txt'
    BINARY = 'bin'
    CSV = 'csv'
    RDF = 'rdf'
    OTHER = 'other'

class MetadataFormat(object):

    def __init__(self, format_name, version, format_type = FormatType.OTHER, file_extension='', description=''):
        self.format_name = format_name
        self.version = version
        self.format_type = format_type
        self.file_extension = file_extension or format_type.value
        self.description = description

    def get_format_name(self):
        return self.format_name

    def get_version(self):
        return self.version

    def get_format_type(self):
        return self.format_type

    def get_file_extension(self):
        return self.file_extension

    def get_description(self):
        return self.description

    def is_compatible(self, other, check_version=False):
        if self.__eq__(other):
            return True
        elif ((not check_version or self.version.lower() == other.get_version().lower()) and self.format_name.lower() == other.get_format_name().lower()):
            return True
        return False

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __repr__(self):
        return str(self)
    
    def __str__(self):
        return unicode(self).encode('utf-8') 

    def __unicode__(self):
        return ((u'MetadataFormat {format_name} v.{version}, {format_type} (.{file_extension}): {description}')
                .format(format_name=self.format_name, version=self.version, format_type=self.format_type.name,
                        file_extension=self.file_extension, description=self.description))

class XMLMetadataFormat(MetadataFormat):

    def __init__(self, format_name, version, xsd_url, description=''):
        MetadataFormat.__init__(self, format_name, version, format_type=FormatType.XML, description=description)
        self.xsd_url = xsd_url

    def get_xsd_url(self):
        return self.xsd_url

    def __unicode__(self):
        return super(XMLMetadataFormat, self).__unicode__() + (u', xsd = {xsd}').format(xsd=self.xsd_url,)

class MetadataFormats(object):
    # Singleton
    class __MetadataFormats:
        def __init__(self):
            self.formats_dict = {}

        def add_metadata_format(self, metadata_format, replace=False):
            # TODO: Check duplicates 
            key = metadata_format.get_format_name()
            if not self.formats_dict.has_key(key):
                self.formats_dict[key] = []
            if replace:
                self.formats_dict[key] = [metadata_format]
            else:
                self.formats_dict[key] = [metadata_format] + self.formats_dict[key]

        def get_num_formats(self):
            num = 0
            for key in self.formats_dict.keys():
                for metadata_format in self.formats_dict[key]:
                    num += 1
            return num
        
        def get_metadata_formats(self):
            return self.formats_dict
        
        def get_metadata_formats(self, format_name, version=''):
            formats_matching_name = self.formats_dict.get(format_name, [])
            if not version:
                return formats_matching_name
            else:
                for metadata_format in self.formats_dict.get(format_name, []):
                    if metadata_format.get_version() == version:
                        return [metadata_format]
            return []
        
        def __repr__(self):
            return str(self)
        
        def __str__(self):
            return unicode(self).encode('utf-8') 

        def __unicode__(self):
            return (u'MetadataFormats ({num_formats}): {formats_dict}').format(num_formats=self.get_num_formats(), formats_dict=self.formats_dict)

    instance = None
    def __new__(cls): # __new__ always a classmethod
        if not MetadataFormats.instance:
            MetadataFormats.instance = MetadataFormats.__MetadataFormats()
        return MetadataFormats.instance

