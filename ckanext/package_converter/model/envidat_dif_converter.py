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
# converts to GCMD DIF 10.2
class GcmdDifConverter(BaseConverter):

    def __init__(self):
        iso_output_format = MetadataFormats().get_metadata_formats('gcmd_dif')[0]
        BaseConverter.__init__(self, iso_output_format)

    def convert(self, record):
        if self.can_convert(record):
            dataset_dict = record.get_json_dict()
            converted_content = self._dif_convert_dataset(dataset_dict)
            converted_record = XMLRecord.from_record(Record(self.output_format, converted_content))
            
            # fix issue with dif included XSD
            current_url = helpers.full_current_url()
            site_url = current_url.split('//',3)[0] + '//' + current_url.split('://',1)[1].split('/',1)[0]
            log.debug(" **** Validating record..." + str(converted_record.validate(custom_replace=[('xs:include schemaLocation="U', 'xs:include schemaLocation="'+ site_url +'/package_converter_xsd/U')])) + ' ****')
            return converted_record
        else:
            raise TypeError(('Converter is not compatible with the record format {record_format}({record_version}). ' +
                             'Accepted format is CKAN {input_format}.').format(
                                 record_format=record.get_metadata_format().get_format_name(), record_version=record.get_metadata_format().get_version(),
                                 input_format=self.get_input_format().get_format_name()))

    def __unicode__(self):
        return super(GcmdDifConverter, self).__unicode__() + u'GCMD DIF Converter '


    def _dif_convert_dataset(self, dataset_dict):
    
        extras_dict = self._extras_as_dict(dataset_dict.get('extras',{}))
        
        dif_metadata_dict = collections.OrderedDict()

        # Header
        dif_metadata_dict['@xmlns']="http://gcmd.gsfc.nasa.gov/Aboutus/xml/dif/"
        dif_metadata_dict['@xmlns:dif']="http://gcmd.gsfc.nasa.gov/Aboutus/xml/dif/"
        dif_metadata_dict['@xmlns:xsi']="http://www.w3.org/2001/XMLSchema-instance"
        
        dif_metadata_dict['@xsi:schemaLocation'] = '{namespace} {schema}'.format(namespace=self.output_format.get_namespace(), 
                                                                                schema=self.output_format.get_xsd_url())
        
        # Entry_ID (M)
        dif_metadata_dict['Entry_ID'] = collections.OrderedDict()
        dif_metadata_dict['Entry_ID']['Short_Name'] = dataset_dict.get('name', '')
        dif_metadata_dict['Entry_ID']['Version'] = dataset_dict.get('version', '1.0')
        
        # Version_Description (O)
        
        # Entry_Title (M)
        dif_metadata_dict['Entry_Title'] = dataset_dict.get('title', '')
        
        
        # Dataset_Citation (O)*
        dif_metadata_dict['Dataset_Citation'] = collections.OrderedDict()
        ## "Dataset_Creator" organization?
        ## "Dataset_Editor" maintainer?
        
        ## "Dataset_Title" 
        dif_metadata_dict['Dataset_Citation']['Dataset_Title'] = dataset_dict.get('title', '')
        
        ## "Dataset_Series_Name" 
        ## "Dataset_Release_Date"
        publication_year = json.loads(dataset_dict.get('publication', '{}')).get('publication_year','')
        dif_metadata_dict['Dataset_Citation']['Dataset_Release_Date'] = publication_year
        
        ## "Dataset_Release_Place" 
        
        ## "Dataset_Publisher"
        dif_metadata_dict['Dataset_Citation']['Dataset_Publisher'] = json.loads(dataset_dict.get('publication', '{}')).get('publisher','')
        
        ## "Version"
        dif_metadata_dict['Dataset_Citation']['Version'] = dataset_dict.get('version', '')
        
        ## "Issue_Identification" 
        ## "Data_Presentation_Form" 
        ## "Other_Citation_Details"
        ## "Persistent_Identifier"
        doi = dataset_dict.get('doi','')
        if doi:
            identifier = collections.OrderedDict()
            identifier['Type'] = 'DOI'
            identifier['Identifier'] = 'doi:' + doi.strip()     
            dif_metadata_dict['Dataset_Citation']['Persistent_Identifier'] = identifier        
        ## "Online_Resource"
        protocol, host = helpers.get_site_protocol_and_host()
        package_url = protocol + '://' + host + toolkit.url_for(controller='package', action='read', id=dataset_dict.get('name', ''))
        dif_metadata_dict['Dataset_Citation']['Online_Resource'] = package_url
        
        #<xs:element name="Personnel" type="PersonnelType" minOccurs="0" maxOccurs="unbounded"/>

        # Science_Keywords (M)*
        science_keywords = self.get_science_keywords(dataset_dict, extras_dict)
        dif_metadata_dict['Science_Keywords'] = collections.OrderedDict()
        dif_metadata_dict['Science_Keywords']['Category'] = science_keywords[0]
        dif_metadata_dict['Science_Keywords']['Topic'] = science_keywords[1]
        dif_metadata_dict['Science_Keywords']['Term'] = science_keywords[2]
        
        #<xs:element name="ISO_Topic_Category" type="ISOTopicCategoryType" minOccurs="0" maxOccurs="unbounded"/>
        # select from https://gcmd.nasa.gov/add/difguide/iso_topic_category.html
        #dif_metadata_dict['ISO_Topic_Category'] = 'Geoscientific Information'
        
        # Ancillary_Keyword (O)* 
        dif_metadata_dict['Ancillary_Keyword'] = self.get_keywords(dataset_dict)
        
        # "Platform"
        dif_metadata_dict['Platform'] = collections.OrderedDict()
        dif_metadata_dict['Platform']['Type'] = "Not provided"
        dif_metadata_dict['Platform']['Short_Name'] = "Not provided"
        dif_metadata_dict['Platform']['Instrument'] = {'Short_Name':"Not provided"}

        # Temporal_Coverage (M)
        dif_metadata_dict['Temporal_Coverage'] = collections.OrderedDict()
        # default set to publication year
        dif_metadata_dict['Temporal_Coverage']['Single_DateTime'] = publication_year + '-01-01'
        # TODO: check if collected date(s) defined
        
        #<xs:element name="Dataset_Progress" type="DatasetProgressType" minOccurs="0"/>

        # Spatial_Coverage (M) 
        dif_metadata_dict['Spatial_Coverage'] = collections.OrderedDict()
        ## <xs:element name="Spatial_Coverage_Type" type="SpatialCoverageTypeEnum" minOccurs="0"/>
        ## "Granule_Spatial_Representation" 
        dif_metadata_dict['Spatial_Coverage']['Granule_Spatial_Representation']= 'CARTESIAN'
        
        ## <xs:element name="Zone_Identifier" type="xs:string" minOccurs="0"/>
        ## <xs:element name="Geometry" type="Geometry" minOccurs="0"/>
        ## <xs:element name="Orbit_Parameters" type="OrbitParameters" minOccurs="0"/>
        ## <xs:element name="Vertical_Spatial_Info" type="VerticalSpatialInfo" minOccurs="0" maxOccurs="unbounded"/>
        ## <xs:element name="Spatial_Info" type="SpatialInfo" minOccurs="0"/>

        #<xs:element name="Location" type="LocationType" minOccurs="0" maxOccurs="unbounded"/>
        #<xs:element name="Data_Resolution" type="DataResolutionType" minOccurs="0" maxOccurs="unbounded"/>

        # Project (M)
        dif_metadata_dict['Project'] = {'Short_Name':'Not provided'}

        #<xs:element name="Quality" type="QualityType" minOccurs="0"/>
        #<xs:element name="Access_Constraints" type="AccessConstraintsType" minOccurs="0"/>
        #<xs:element name="Use_Constraints" type="UseConstraintsType" minOccurs="0"/>
        #<xs:element name="Dataset_Language" type="DatasetLanguageType" minOccurs="0" maxOccurs="unbounded"/>
        #<xs:element name="Originating_Center" type="OriginatingCenterType" minOccurs="0"/>
        
        # Organization (M) (I put WSL, we should think about adding
        dif_metadata_dict['Organization'] = collections.OrderedDict()
        ## "Organization_Type" * DISTRIBUTOR/ARCHIVER/ORIGINATOR/PROCESSOR
        dif_metadata_dict['Organization']['Organization_Type'] = 'DISTRIBUTOR'
        
        ## "Organization_Name" "Short_Name" "Long_Name" 
        dif_metadata_dict['Organization']['Organization_Name'] = collections.OrderedDict()
        dif_metadata_dict['Organization']['Organization_Name']['Short_Name']= 'WSL'
        dif_metadata_dict['Organization']['Organization_Name']['Long_Name']= 'Swiss Federal Institute for Forest, Snow and Landscape Research WSL'
        
        ## <xs:element name="Hours_Of_Service" type="xs:string" minOccurs="0"/>
        ## <xs:element name="Instructions" type="xs:string" minOccurs="0"/>
        ## <xs:element name="Organization_URL" type="xs:string" minOccurs="0"/>
        dif_metadata_dict['Organization']['Organization_URL']= 'https://www.wsl.ch'
        
        ## <xs:element name="Dataset_ID" type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
        ## <xs:element name="Personnel" type="OrgPersonnelType" maxOccurs="unbounded"/>
        dif_metadata_dict['Organization']['Personnel'] = collections.OrderedDict()
        dif_metadata_dict['Organization']['Personnel']['Role'] = 'DATA CENTER CONTACT'
        dif_metadata_dict['Organization']['Personnel']['Contact_Group'] = collections.OrderedDict()

        dif_metadata_dict['Organization']['Personnel']['Contact_Group']["Name"] = 'EnviDat'
        dif_metadata_dict['Organization']['Personnel']['Contact_Group']["Email"] = 'envidat@wsl.ch'
        
        #<xs:element name="Distribution" type="DistributionType" minOccurs="0" maxOccurs="unbounded"/>
        #<xs:element name="Multimedia_Sample" type="MultimediaSampleType" minOccurs="0" maxOccurs="unbounded"/>
        #<xs:element name="Reference" type="ReferenceType" minOccurs="0" maxOccurs="unbounded"/>
        
        # Summary (M)
        dif_metadata_dict['Summary'] = collections.OrderedDict()
        ## Abstract
        dif_metadata_dict['Summary']['Abstract'] = dataset_dict.get('notes','').replace('\n', ' ').replace('\r', ' ')
        ## "Purpose" TODO: get from extras as in ISO
        
        # Related_URL (M)*
        dif_metadata_dict['Related_URL'] = {'URL':package_url}

        #<xs:element name="Metadata_Association" type="MetadataAssociationType" minOccurs="0" maxOccurs="unbounded"/>
        #   <!-- Added from UMM (ECHO) -->
        #<xs:element name="IDN_Node" type="IDNNodeType" minOccurs="0" maxOccurs="unbounded"/>
        #<xs:element name="Originating_Metadata_Node" type="OriginatingMetadataNodeType" minOccurs="0"/>
        
        # Metadata_Name (M)
        dif_metadata_dict['Metadata_Name'] = self.output_format.get_format_name()

        # Metadata_Version (M)
        dif_metadata_dict['Metadata_Version'] = 'VERSION ' + self.output_format.get_version()
        
        #<xs:element name="DIF_Revision_History" type="DIFRevisionHistoryType" minOccurs="0"/>

        # Metadata_Dates (M)
        dif_metadata_dict['Metadata_Dates'] = collections.OrderedDict()

        metadata_created = dataset_dict.get('metadata_created')
        metadata_modified = dataset_dict.get('metadata_modified')
        dif_metadata_dict['Metadata_Dates']["Metadata_Creation"] = metadata_created
        dif_metadata_dict['Metadata_Dates']["Metadata_Last_Revision"] = metadata_modified
        dif_metadata_dict['Metadata_Dates']["Data_Creation"] = metadata_created
        dif_metadata_dict['Metadata_Dates']["Data_Last_Revision"] = metadata_modified

        #<xs:element name="Private" type="PrivateType" minOccurs="0"/>
        #<xs:element name="Additional_Attributes" type="AdditionalAttributesType" minOccurs="0" maxOccurs="unbounded"/>
        #<xs:element name="Product_Level_Id" type="ProcessingLevelIdType" minOccurs="0"/>
        #<xs:element name="Collection_Data_Type" type="CollectionDataTypeEnum" minOccurs="0" maxOccurs="unbounded"/>
        #<xs:element name="Product_Flag" type="ProductFlagEnum" minOccurs="0"/>
        #<xs:element name="Extended_Metadata" type="ExtendedMetadataType" minOccurs="0" maxOccurs="unbounded"/>
 
        # Root element
        gcmd_dif_dict = collections.OrderedDict()
        gcmd_dif_dict['DIF'] = dif_metadata_dict

        # Convert to xml
        converted_package = unparse(gcmd_dif_dict, pretty=True)

        return converted_package
    
    # extract keywords from tags
    def get_keywords(self, data_dict):
        keywords = []
        for tag in data_dict.get('tags',[]):
            name = tag.get('display_name', '').upper()
            keywords += [name]
        return keywords
    
    # guess keywords from organization
    def get_science_keywords(self, data_dict, extras_dict):
        default_keywords = ['EARTH SCIENCE', 'LAND SURFACE', 'ENVIRONMENT']
        
        # check if defined in extras, comma-separated
        custom_keywords = self._get_ignore_case(extras_dict, 'science_keywords').upper().split(',')
        if len(custom_keywords) == 3:
            return custom_keywords

        # map to organization (#TODO)
        dataset_organization = data_dict.get('organization', {}).get('name','')
        
        # possible topics: AGRICULTURE, ATMOSPHERE, BIOSPHERE, BIOLOGICAL CLASSIFICATION, CLIMATE INDICATORS, 
        #                  CRYOSPHERE, HUMAN DIMENSIONS, LAND SURFACE, OCEANS, PALEOCLIMATE, SOLID EARTH, 
        #                  SPECTRAL/ENGINEERING, SUN-EARTH INTERACTIONS, TERRESTRIAL HYDROSPHERE
        organizations_keywords_dict = {
            "biodiversity-and-conservation-biology":['EARTH SCIENCE', 'BIOSPHERE', 'BIODIVERSITY'],
			"cces":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
			"clench":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
			"community-ecology":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ECOLOGY'],
			"conservation-biology":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
			"cryos":['EARTH SCIENCE', 'CRYOSPHERE', 'ICE'],
			"d-baug":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
			"usys":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
			"dynamic-macroecology":['EARTH SCIENCE', 'BIOSPHERE', 'MACROECOLOGY'],
			"ecosystems-dynamics":['EARTH SCIENCE', 'BIOSPHERE', 'ECOSYSTEMS'],
			"epfl":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
			"ethz":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
			"feh":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
			"forema":['EARTH SCIENCE', 'BIOSPHERE', 'FOREST'],
			"forest-dynamics":['EARTH SCIENCE', 'BIOSPHERE', 'FOREST'],
			"forest-soils-and-biogeochemistry":['EARTH SCIENCE', 'SOLID EARTH', 'BIOGEOCHEMISTRY'],
			"gebirgshydrologie":['EARTH SCIENCE', 'LAND SURFACE', 'HYDROLOGY'],
			"gis":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'GIS'],
			"hazri":['EARTH SCIENCE', 'SOLID EARTH', 'NATURAL HAZARDS'],
			"ibp":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
			"landscape-dynamics":['EARTH SCIENCE', 'LAND SURFACE', 'LADSCAPE'],
			"lwf":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
			"mountain-ecosystems":['EARTH SCIENCE', 'BIOSPHERE', 'MOUNTAIN ECOSYSTEMS'],
			"nfi":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
			"plant-animal-interactions":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
			"remote-sensing":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
			"resource-analysis":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
			"slf":['EARTH SCIENCE', 'CRYOSPHERE', 'SNOW'],
			"stand-dynamics-and-silviculture":['EARTH SCIENCE', 'BIOSPHERE', 'SILVICULTURE'],
			"swissforestlab-swissfl":['EARTH SCIENCE', 'BIOSPHERE', 'FOREST'],
			"vaw":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
			"wsl":['EARTH SCIENCE', 'LAND SURFACE', 'LANDSCAPE']
        }
        science_keywords = organizations_keywords_dict.get(dataset_organization, default_keywords)
        
        return science_keywords
        
    def _get_ignore_case(self, data_dict, tag, ignore_blanks = True):
        tag_lower = tag.lower()
        if ignore_blanks:
            tag_lower = tag_lower.replace(' ','')
        tag_key = ''
        for key in data_dict.keys():
            key_lower = key.lower()
            if ignore_blanks:
                key_lower = key_lower.replace(' ','')
            if key_lower == tag_lower:
                tag_key = key
                break
        return (data_dict.get(tag_key, ''))

    # extras as a simple dictionary
    def _extras_as_dict(self, extras):
        extras_dict = {}
        for extra in extras:
            extras_dict[extra.get('key')] = extra.get('value')
        return extras_dict
