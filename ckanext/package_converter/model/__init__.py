from ckanext.package_converter.model.metadata_format import MetadataFormats, MetadataFormat, XMLMetadataFormat, \
    FormatType
from ckanext.package_converter.model.converter import Converters, XSLConverter

import os

# Add Formats
MetadataFormats().add_metadata_format(MetadataFormat('dcat', '20140116', format_type=FormatType.RDF,
                                                     description='DCAT is an RDF vocabulary designed to facilitate interoperability ' +
                                                                 ' between data catalogs published on the Web ' +
                                                                 '(https://www.w3.org/TR/2014/REC-vocab-dcat-20140116)'))

MetadataFormats().add_metadata_format(MetadataFormat('dcat-ap-ch', '1.0', format_type=FormatType.RDF,
                                                     description='DCAT-AP-CH is an RDF Swiss data standard based on the international DCAT-AP standard ' +
                                                                 '(https://handbook.opendata.swiss/content/glossar/bibliothek/dcat-ap-ch.html)'))

MetadataFormats().add_metadata_format(
    MetadataFormat('ckan', '', format_type=FormatType.JSON, description='CKAN base format for package'))
MetadataFormats().add_metadata_format(
    MetadataFormat('ckan_resource', '', format_type=FormatType.JSON, description='CKAN base format for resources'))

# MetadataFormats().add_metadata_format(
#     XMLMetadataFormat('datacite', '3.1', 'http://schema.datacite.org/meta/kernel-3/metadata.xsd',
#                       namespace='http://datacite.org/schema/kernel-3',
#                       description='DataCite Metadata Format 3.1'))

# MetadataFormats().add_metadata_format(
#     XMLMetadataFormat('datacite', '4.3', 'http://schema.datacite.org/meta/kernel-4.3/metadata.xsd',
#                       namespace="http://datacite.org/schema/kernel-4",
#                       description='DataCite Metadata Format 4.3'))

MetadataFormats().add_metadata_format(
    XMLMetadataFormat('datacite', '4.4', 'http://schema.datacite.org/meta/kernel-4.4/metadata.xsd',
                      namespace="http://datacite.org/schema/kernel-4",
                      description='DataCite Metadata Format 4.4'))

MetadataFormats().add_metadata_format(
    XMLMetadataFormat('oai_dc', '2.0', 'http://www.openarchives.org/OAI/2.0/oai_dc.xsd',
                      namespace='http://www.openarchives.org/OAI/2.0/oai_dc/',
                      description='XML Schema adjusted for usage in the OAI-PMH that imports the Dublin Core elements from the DCMI schema.'))

MetadataFormats().add_metadata_format(
    XMLMetadataFormat('oai_pmh', '2.0', 'http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd',
                      namespace='http://www.openarchives.org/OAI/2.0/',
                      description='XML Schema which can be used to validate replies to all OAI-PMH v2.0 requests'))

MetadataFormats().add_metadata_format(XMLMetadataFormat('iso19139', '1.0', 'http://www.isotc211.org/2005/gmd/gmd.xsd',
                                                        namespace='http://www.isotc211.org/2005/gmd',
                                                        description='ISO 19115:2003/19139 XML Metadata Format'))

MetadataFormats().add_metadata_format(
    XMLMetadataFormat('gcmd_dif', '10.2', 'http://gcmd.gsfc.nasa.gov/Aboutus/xml/dif/dif_v10.2.xsd',
                      namespace='http://gcmd.gsfc.nasa.gov/Aboutus/xml/dif/',
                      description='Global Change Master Directory Directory Interchange Format (GCMD DIF)'))

MetadataFormats().add_metadata_format(MetadataFormat('bibtex', '', format_type=FormatType.TEXT, file_extension='bib',
                                                     description='Format used to describe and process lists of references'))

MetadataFormats().add_metadata_format(
    MetadataFormat('plain-text', '', format_type=FormatType.TEXT, file_extension='txt',
                   description='Format used to provide plain human readable information'))

MetadataFormats().add_metadata_format(MetadataFormat('ris', '', format_type=FormatType.TEXT, file_extension='ris',
                                                     description='Tagged format for expressing bibliographic citations'))

MetadataFormats().add_metadata_format(MetadataFormat('readme', '', format_type=FormatType.TEXT, file_extension='txt',
                                                     description='Plain text format'))

MetadataFormats().add_metadata_format(MetadataFormat('csv', '', format_type=FormatType.CSV, file_extension='csv',
                                                     description='Delimited text file format to store tabular data (comma-separated)'))

MetadataFormats().add_metadata_format(
    MetadataFormat('schemaorg', '', format_type=FormatType.JSON, file_extension='jsonld',
                   description='Schema.org structured information for datasets based upon W3C DCAT work'))

# Add Converters
datacite_oai_dc_xsl_relative_path = '../public/package_converter_xsl/datacite_v.4.3_to_oai_dc_v2.0.xsl'
datacite_oai_dc_xsl_path = os.path.join(os.path.dirname(__file__), datacite_oai_dc_xsl_relative_path)
Converters().add_converter(XSLConverter(MetadataFormats().get_metadata_formats('datacite', '4.4')[0],
                                        MetadataFormats().get_metadata_formats('oai_dc')[0],
                                        datacite_oai_dc_xsl_path))

datacite_oai_dc_xsl_relative_path = '../public/package_converter_xsl/datacite-to-dcat-ap.xsl'
datacite_oai_dc_xsl_path = os.path.join(os.path.dirname(__file__), datacite_oai_dc_xsl_relative_path)
Converters().add_converter(XSLConverter(MetadataFormats().get_metadata_formats('datacite', '4.4')[0],
                                        MetadataFormats().get_metadata_formats('dcat')[0],
                                        datacite_oai_dc_xsl_path))
