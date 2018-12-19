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
            #log.debug(" **** Validating record..." + str(converted_record.validate(custom_replace=[('xs:include schemaLocation="U', 'xs:include schemaLocation="'+ site_url +'/package_converter_xsd/U')])) + ' ****')
            return converted_record
        else:
            raise TypeError(('Converter is not compatible with the record format {record_format}({record_version}). ' +
                             'Accepted format is CKAN {input_format}.').format(
                                 record_format=record.get_metadata_format().get_format_name(), record_version=record.get_metadata_format().get_version(),
                                 input_format=self.get_input_format().get_format_name()))

    def __unicode__(self):
        return super(GcmdDifConverter, self).__unicode__() + u'GCMD DIF Converter '


    def _dif_convert_dataset(self, dataset_dict):
    
        # some values only as custom fields
        extras_dict = self._extras_as_dict(dataset_dict.get('extras',{}))
        dif_extras = ['science_keywords', 'purpose']
        
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
        ## "Dataset_Creator" organization
        author_names = []
        try:
            for author in json.loads(dataset_dict.get('author', '[]')):
                author_names += [author.get('name','')]
        except:
            pass
        
        if author_names:
            dif_metadata_dict['Dataset_Citation']['Dataset_Creator'] = ', '.join(author_names)
        
        ## "Dataset_Editor" maintainer
        try:
            maintainer_name = json.loads(dataset_dict.get('maintainer', '{}')).get('name','')
            dif_metadata_dict['Dataset_Citation']['Dataset_Editor'] = maintainer_name
        except:
            pass
        
        ## "Dataset_Title" 
        dif_metadata_dict['Dataset_Citation']['Dataset_Title'] = dataset_dict.get('title', '')
        
        ## "Dataset_Series_Name" 
        ## "Dataset_Release_Date"
        publication_year = json.loads(dataset_dict.get('publication', '{}')).get('publication_year','')
        dif_metadata_dict['Dataset_Citation']['Dataset_Release_Date'] = publication_year
        
        ## "Dataset_Release_Place" 
        dif_metadata_dict['Dataset_Citation']['Dataset_Release_Place'] = 'Birmensdorf, Switzerland'
        
        ## "Dataset_Publisher"
        dif_metadata_dict['Dataset_Citation']['Dataset_Publisher'] = json.loads(dataset_dict.get('publication', '{}')).get('publisher','')
        
        ## "Version"
        dif_metadata_dict['Dataset_Citation']['Version'] = dataset_dict.get('version', '')
        
        ## "Issue_Identification" 
        ## "Data_Presentation_Form" 
        dif_metadata_dict['Dataset_Citation']['Data_Presentation_Form'] = ','.join(self._get_resource_formats(dataset_dict))
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
        
        # "Personnel"
        maintainer = json.loads(dataset_dict.get('maintainer', '{}'))
        dif_metadata_dict['Personnel'] = collections.OrderedDict()
        dif_metadata_dict['Personnel']['Role'] = "TECHNICAL CONTACT"
        dif_metadata_dict['Personnel']['Contact_Person'] = collections.OrderedDict()
        dif_metadata_dict['Personnel']['Contact_Person']['First_Name'] = maintainer.get('name', '').strip().split(' ')[0]
        dif_metadata_dict['Personnel']['Contact_Person']['Last_Name'] = maintainer.get('name', '').strip().split(' ')[-1]
        dif_metadata_dict['Personnel']['Contact_Person']['Email'] = maintainer.get('email', '')

        # Science_Keywords (M)*
        science_keywords = self._get_science_keywords(dataset_dict, extras_dict)
        dif_metadata_dict['Science_Keywords'] = collections.OrderedDict()
        dif_metadata_dict['Science_Keywords']['Category'] = science_keywords[0]
        dif_metadata_dict['Science_Keywords']['Topic'] = science_keywords[1]
        dif_metadata_dict['Science_Keywords']['Term'] = science_keywords[2]
        
        # "ISOTopicCategoryType"
        # select from https://gcmd.nasa.gov/add/difguide/iso_topic_category.html
        dif_metadata_dict['ISO_Topic_Category'] = 'environment'
        
        # Ancillary_Keyword (O)* 
        dif_metadata_dict['Ancillary_Keyword'] = self._get_keywords(dataset_dict)
        
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
        
        # "Dataset_Progress" draft or private -> IN WORK, doi -> COMPLETE (otherwise empty)
        if dataset_dict.get('private',False) or dataset_dict.get('num_resources',0)==0:
            dif_metadata_dict['Dataset_Progress'] = 'IN WORK'
        elif dataset_dict.get('doi',''):
            dif_metadata_dict['Dataset_Progress'] = 'COMPLETE'
        
        # Spatial_Coverage (M) 
        dif_metadata_dict['Spatial_Coverage'] = collections.OrderedDict()
        ## "Spatial_Coverage_Type"
        ## "Granule_Spatial_Representation" 
        dif_metadata_dict['Spatial_Coverage']['Granule_Spatial_Representation']= 'CARTESIAN'
        
        ## <xs:element name="Zone_Identifier" type="xs:string" minOccurs="0"/>
        
        ## "Geometry" [1]
        try:
            spatial = json.loads(dataset_dict.get('spatial', '{}'))
        except:
            spatial = {}    
        if spatial:
                dif_metadata_dict['Spatial_Coverage']['Geometry'] = collections.OrderedDict()
                dif_metadata_dict['Spatial_Coverage']['Geometry']['Coordinate_System'] = 'CARTESIAN'
                ### "Bounding_Rectangle"
                bounding_rectangle = collections.OrderedDict()
                bound_box_coordinates = self._get_bounding_rectangle(spatial.get('coordinates',[]))
                bounding_rectangle["Center_Point"] = collections.OrderedDict()
                bounding_rectangle["Center_Point"]["Point_Longitude"] = str((bound_box_coordinates[1] + bound_box_coordinates[0])/2.0)
                bounding_rectangle["Center_Point"]["Point_Latitude"] = str((bound_box_coordinates[3] + bound_box_coordinates[2])/2.0)
                bounding_rectangle["Southernmost_Latitude"] = str(max(bound_box_coordinates[2], -90))
                bounding_rectangle["Northernmost_Latitude"] = str(min(bound_box_coordinates[3],  90))
                bounding_rectangle["Westernmost_Longitude"] = str(max(bound_box_coordinates[0],   0))
                bounding_rectangle["Easternmost_Longitude"] = str(min(bound_box_coordinates[1],  180))
                dif_metadata_dict['Spatial_Coverage']['Geometry']['Bounding_Rectangle'] = bounding_rectangle        
                
                ### <xs:element name="Point" type="Point"/>
                if spatial.get('type') == 'Point':
                     dif_metadata_dict['Spatial_Coverage']['Geometry']['Point'] = collections.OrderedDict()
                     dif_metadata_dict['Spatial_Coverage']['Geometry']['Point']['Point_Longitude'] = bound_box_coordinates[0]
                     dif_metadata_dict['Spatial_Coverage']['Geometry']['Point']['Point_Latitude'] = bound_box_coordinates[3]
                     latitude = bound_box_coordinates[3]
                elif spatial.get('type') == 'MultiPoint':
                     points = []
                     for coordinate_pair in spatial.get('coordinates',[]):
                         point = collections.OrderedDict()
                         point['Point_Longitude'] = str(coordinate_pair[0])
                         point['Point_Latitude'] = str(coordinate_pair[1])
                         points += [point]
                     dif_metadata_dict['Spatial_Coverage']['Geometry']['Point'] = points
                elif spatial.get('type') == 'Polygon':
                ### <xs:element name="Polygon" type="GPolygon"/>
                     points = []
                     for coordinate_pair in spatial.get('coordinates',[])[0]:
                         point = collections.OrderedDict()
                         point['Point_Longitude'] = str(coordinate_pair[0])
                         point['Point_Latitude'] = str(coordinate_pair[1])
                         points += [point]
                     if len(points)>1:
                         points.pop()
                     
                     if self._is_counter_clockwise(points):
                         print("Conterclockwise REVERSing!!")
                         points.reverse()

                     dif_metadata_dict['Spatial_Coverage']['Geometry']['Polygon'] = collections.OrderedDict()
                     dif_metadata_dict['Spatial_Coverage']['Geometry']['Polygon']['Boundary'] = {'Point': points}
                     dif_metadata_dict['Spatial_Coverage']['Geometry']['Polygon']['Center_Point'] = copy.deepcopy(dif_metadata_dict['Spatial_Coverage']['Geometry']['Bounding_Rectangle']['Center_Point'])

        
        ## <xs:element name="Orbit_Parameters" type="OrbitParameters" minOccurs="0"/>
        ## <xs:element name="Vertical_Spatial_Info" type="VerticalSpatialInfo" minOccurs="0" maxOccurs="unbounded"/>
        ## <xs:element name="Spatial_Info" type="SpatialInfo" minOccurs="0"/>

        #<xs:element name="Location" type="LocationType" minOccurs="0" maxOccurs="unbounded"/>
        #TODO: Cannot know type, could be set to CONTINENT type and then Europe (?)
        #<xs:element name="Data_Resolution" type="DataResolutionType" minOccurs="0" maxOccurs="unbounded"/>

        # Project (M)
        dif_metadata_dict['Project'] = {'Short_Name':'Not provided'}

        #<xs:element name="Quality" type="QualityType" minOccurs="0"/>
        dif_metadata_dict['Access_Constraints'] = 'Public access to the data'
        
        dataset_restrictions = self._get_resource_restrictions(dataset_dict)
        if "registered" in dataset_restrictions:
            dif_metadata_dict['Access_Constraints'] = 'Registration is required to access the data'
        elif ("any_organization" in dataset_restrictions) \
          or ("same_organization" in dataset_restrictions) \
          or ("only_allowed_users" in dataset_restrictions):
            dif_metadata_dict['Access_Constraints'] = 'Access to the data upon request'
 
        # "Use_Constraints"
        license = dataset_dict.get('license_title', 'Open Data Commons Open Database License (ODbL)')
        license_url = dataset_dict.get('license_url', 'http://www.opendefinition.org/licenses/odc-odbl')
        dif_metadata_dict['Use_Constraints'] = 'Usage constraintes defined by the license "' + license.strip() + '", see ' + license_url
        
        # Dataset_Language
        dif_metadata_dict['Dataset_Language'] = self._get_dif_language_code(dataset_dict.get('language', 'en'))

        # "Originating_Center"
        dif_metadata_dict['Originating_Center'] = dataset_dict.get('organization', {}).get('title','')

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
        ##  "Organization_URL"
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
        # TODO: find paper citation in the description and parse it to this element
              
        # Summary (M)
        dif_metadata_dict['Summary'] = collections.OrderedDict()
        ## Abstract
        dif_metadata_dict['Summary']['Abstract'] = dataset_dict.get('notes','').replace('\n', ' ').replace('\r', ' ')
        ## "Purpose"
        purpose = self._get_ignore_case(extras_dict, 'purpose')
        if purpose:
            dif_metadata_dict['Summary']['Purpose'] = self._get_or_missing(extras_dict, 'purpose', ignore_case=True)

        # Related_URL (M)*
        dif_metadata_dict['Related_URL'] = {'URL':package_url}

        #<xs:element name="Metadata_Association" type="MetadataAssociationType" minOccurs="0" maxOccurs="unbounded"/>
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

        # "Private"
        if dataset_dict.get('private',False):
            dif_metadata_dict['Private'] = 'True'
        else:
            dif_metadata_dict['Private'] = 'False'

        # "Additional_Attributes"
        # Maybe the authors should go here
        
        #<xs:element name="Product_Level_Id" type="ProcessingLevelIdType" minOccurs="0"/>
        #<xs:element name="Collection_Data_Type" type="CollectionDataTypeEnum" minOccurs="0" maxOccurs="unbounded"/>
        #<xs:element name="Product_Flag" type="ProductFlagEnum" minOccurs="0"/>
        
        # "Extended_Metadata"
        extended_metadata = []
        for key in extras_dict:
            if key.lower() not in dif_extras:
                value = extras_dict[key]
                metadata = collections.OrderedDict()
                metadata['Name'] = key
                metadata['Type'] = 'String'
                metadata['Value'] = value
                extended_metadata += [metadata]
        if len(extended_metadata)>0:
            dif_metadata_dict['Extended_Metadata'] = {'Metadata': extended_metadata}
                
        # Root element
        gcmd_dif_dict = collections.OrderedDict()
        gcmd_dif_dict['DIF'] = dif_metadata_dict

        # Convert to xml
        converted_package = unparse(gcmd_dif_dict, pretty=True)

        return converted_package
    
    # extract keywords from tags
    def _get_keywords(self, data_dict):
        keywords = []
        for tag in data_dict.get('tags',[]):
            name = tag.get('display_name', '').upper()
            keywords += [name]
        return keywords
    
    # guess keywords from organization
    def _get_science_keywords(self, data_dict, extras_dict):
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
            "community-ecology":['EARTH SCIENCE', 'BIOSPHERE', 'ECOLOGY'],
            "conservation-biology":['EARTH SCIENCE', 'BIOSPHERE', 'BIOLOGY'],
            "cryos":['EARTH SCIENCE', 'CRYOSPHERE', 'SNOW'],
            "d-baug":['EARTH SCIENCE', 'SPECTRAL/ENGINEERING', 'ENVIRONMENT'],
            "usys":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
            "dynamic-macroecology":['EARTH SCIENCE', 'BIOSPHERE', 'MACROECOLOGY'],
            "ecosystems-dynamics":['EARTH SCIENCE', 'BIOSPHERE', 'ECOSYSTEMS'],
            "epfl":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
            "ethz":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
            "feh":['EARTH SCIENCE', 'AGRICULTURE', 'ENVIRONMENT'],
            "forema":['EARTH SCIENCE', 'BIOSPHERE', 'FOREST'],
            "forest-dynamics":['EARTH SCIENCE', 'BIOSPHERE', 'FOREST'],
            "forest-soils-and-biogeochemistry":['EARTH SCIENCE', 'SOLID EARTH', 'BIOGEOCHEMISTRY'],
            "gebirgshydrologie":['EARTH SCIENCE', 'LAND SURFACE', 'HYDROLOGY'],
            "gis":['EARTH SCIENCE', 'LAND SURFACE', 'GIS'],
            "hazri":['EARTH SCIENCE', 'SOLID EARTH', 'NATURAL HAZARDS'],
            "ibp":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
            "landscape-dynamics":['EARTH SCIENCE', 'LAND SURFACE', 'LANDSCAPE'],
            "lwf":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
            "mountain-ecosystems":['EARTH SCIENCE', 'BIOSPHERE', 'MOUNTAIN ECOSYSTEMS'],
            "nfi":['EARTH SCIENCE', 'BIOSPHERE', 'FOREST'],
            "plant-animal-interactions":['EARTH SCIENCE', 'BIOSPHERE', 'INTERACTIONS'],
            "remote-sensing":['EARTH SCIENCE', 'CLIMATE INDICATORS', 'ENVIRONMENT'],
            "resource-analysis":['EARTH SCIENCE', 'BIOSPHERE', 'FOREST RESOURCES'],
            "slf":['EARTH SCIENCE', 'CRYOSPHERE', 'SNOW'],
            "stand-dynamics-and-silviculture":['EARTH SCIENCE', 'BIOSPHERE', 'SILVICULTURE'],
            "swissforestlab-swissfl":['EARTH SCIENCE', 'BIOSPHERE', 'FOREST'],
            "vaw":['EARTH SCIENCE', 'TERRESTRIAL HYDROSPHERE', 'GLACIOLOGY'],
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

    # get resource formats
    def _get_resource_formats(self, dataset_dict):
        resource_formats = []
        for resource in dataset_dict.get('resources', []):
            resource_format = resource.get('format', resource.get('mimetype', resource.get('mimetype_inner', '')))
            if resource_format:
                resource_format = resource_format.lower()
                if resource_format not in resource_formats:
                    resource_formats += [resource_format]
        return resource_formats

    # get resource restrictions
    def _get_resource_restrictions(self, dataset_dict):
        resource_restrictions = []
        for resource in dataset_dict.get('resources', []):
            try:
                restricted = json.loads(resource.get('restricted'))
            except:
                restricted = {}
            resource_restriction = restricted.get('level','')
            if resource_restriction:
                resource_restriction = resource_restriction.lower()
                if resource_restriction not in resource_restrictions:
                    resource_restrictions += [resource_restriction]
        return resource_restrictions

    # translate to full word codehttps://gcmd.nasa.gov/DocumentBuilder/defaultDif10/guide/data_set_language.html
    # Values: English; Afrikaans; Arabic; Bosnia; Bulgarian; Chinese; Croation; Czech; Danish; Dutch; Estonian; 
    # Finnish; French; German; Hebrew; Hungarian; Indonesian; Italian; Japanese; Korean; Latvian; Lithuanian; Norwegian; 
    # Polish; Portuguese; Romanian; Russian; Slovak; Spanish; Ukrainian; Vietnamese
    def _get_dif_language_code(self, code):
        lang_code = code.lower()[:2]
        lookup_dict = {'en':'English','de':'German','it':'Italian','fr':'French'} #, 'ro':'roh'}        
        return lookup_dict.get(lang_code, 'English').title()
        
    def _get_bounding_rectangle(self, coordinates):
        flatten_coordinates = coordinates
        while type(flatten_coordinates[0]) is list:
            flatten_coordinates = [item for sublist in flatten_coordinates for item in sublist]
        longitude_coords = flatten_coordinates[0:][::2]                   
        latitude_coords = flatten_coordinates[1:][::2]  
        return([min(longitude_coords),max(longitude_coords), min(latitude_coords), max(latitude_coords)])
    
    def _is_counter_clockwise(self, points):
        
        if len(points)<3:
            return False
        
        akku = 0
        print(points)
        
        for i in range(len(points)):
            p1 = points[i]         
            p2 = points[0]
               
            if i+1 < len(points):
                p2 = points[i+1]
            print(akku)
            akku += (p2['Point_Longitude'] - p1['Point_Longitude'])*(p2['Point_Latitude'] + p1['Point_Latitude'])
        print(akku)
        if akku >= 0:
            return False  
        else:
            return True      

        