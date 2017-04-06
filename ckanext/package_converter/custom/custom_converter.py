import sys
sys.path.insert(0, "H:\\Envidat_project\\dev\\ckan\\test\\package_converter")

from model.record import Record, XMLRecord, JSONRecord
from model.metadata_format import MetadataFormats, XMLMetadataFormat
from model.converter import BaseConverter

from logging import getLogger
log = getLogger(__name__)

class CustomConverter(BaseConverter):

    def __init__(self):
        datacite_format = MetadataFormats().get_metadata_formats('datacite', '3.1')[0]
        BaseConverter.__init__(self, datacite_format)

    def convert(self, record):
        if self.can_convert(record):
            converted_content = '''<?xml version="1.0" encoding="UTF-8"?>
<resource xmlns="http://datacite.org/schema/kernel-3">
	<identifier identifierType="DOI">10.16904/17</identifier>
	<creators>
		<creator>
			<creatorName>Nander Wever</creatorName>
			<affiliation xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">SLF</affiliation>
		</creator>
	</creators>
	<titles>
		<title xml:lang="en-us">IRKIS Soil moisture measurements Davos</title>
	</titles>
	<publisher>SLF</publisher>
	<publicationYear>2017</publicationYear>
</resource>'''
            converted_record = XMLRecord.from_record(Record(self.output_format, converted_content))
            return converted_record
        else:
            raise TypeError(('Converter is not compatible with the record format {record_format}({record_version}). ' +
                             'Accepted format is CKAN {input_format}.').format(
                                 record_format=record.get_metadata_format().get_format_name(), record_version=record.get_metadata_format().get_version(),
                                 input_format=self.get_input_format().get_format_name()))

    def __unicode__(self):
        return super(CustomConverter, self).__unicode__() + u' Custom.'

class CustomTest(object):
    pass

