from ckanext.package_converter.model.metadata_format import MetadataFormats, MetadataFormat, XMLMetadataFormat, FormatType
from ckanext.package_converter.model.converter import Converters, XSLConverter

# Add Formats
MetadataFormats()._add_format(MetadataFormat('dcat', '20140116', format_type=FormatType.RDF, 
                                description='DCAT is an RDF vocabulary designed to facilitate interoperability '+
                                            ' between data catalogs published on the Web ' +
                                            '(https://www.w3.org/TR/2014/REC-vocab-dcat-20140116)'))
MetadataFormats()._add_format(MetadataFormat('ckan', '', format_type=FormatType.JSON, description='CKAN base format for package'))

MetadataFormats()._add_format(XMLMetadataFormat('datacite', '3.1', 'http://schema.datacite.org/meta/kernel-3/metadata.xsd',
                                   description='DataCite Metadata Format'))
#MetadataFormats()._add_format(XMLMetadataFormat('datacite', '4.0', 'https://schema.datacite.org/meta/kernel-4.0/metadata.xsd',
#                                   description='DataCite Metadata Format'))

MetadataFormats()._add_format(XMLMetadataFormat('oai_dc', '2.0', 'http://www.openarchives.org/OAI/2.0/oai_dc.xsd',
                                   description='XML Schema adjusted for usage in the OAI-PMH that imports the Dublin Core elements from the DCMI schema.'))

# Add Converters
datacite_oai_dc_xsl_path = '../public/package_converter_xsl/datacite_v.3.1_to_oai_dc_v2.0.xsl'

Converters().add_converter(XSLConverter(MetadataFormats().get_metadata_formats('datacite', '3.1')[0],
                      MetadataFormats().get_metadata_formats('oai_dc')[0],
                      datacite_oai_dc_xsl_path))

