from . record import Record, XMLRecord
from . metadata_format import MetadataFormats, XMLMetadataFormat
import importlib

from logging import getLogger

log = getLogger(__name__)


class Converter(object):

    def __init__(self, input_format, output_format):
        self.input_format = input_format
        self.output_format = output_format

    def get_input_format(self):
        return self.input_format

    def get_output_format(self):
        return self.output_format

    def convert(self, record):
        raise NotImplementedError('This is an abstract class and cannot be instantiated for conversion')

    def can_convert(self, record, check_version=False):
        return self.can_convert_from_format(record.get_metadata_format(), check_version=check_version)

    def can_convert_from_format(self, input_format, check_version=False):
        if input_format.is_compatible(self.input_format, check_version=check_version):
            return True
        return False

    def can_convert_to_format(self, output_format, check_version=False):
        if output_format.is_compatible(self.output_format, check_version=check_version):
            return True
        return False

    def can_convert_format(self, input_format, output_format=None, check_version=False):
        return (self.can_convert_from_format(input_format, check_version=check_version)) and (
                not output_format or self.can_convert_to_format(output_format, check_version=check_version))

    def __repr__(self):
        return str(self)

    def __str__(self):
        return str(self).encode('utf-8')

    def __unicode__(self):
        return (u'Converter: {input_format}({input_version}) -> {output_format}({output_version}) ').format(
            input_format=self.input_format.get_format_name(), input_version=self.input_format.get_version(),
            output_format=self.output_format.get_format_name(), output_version=self.output_format.get_version())


class BaseConverter(Converter):

    def __init__(self, output_format):
        ckan_base_format = MetadataFormats().get_metadata_formats('ckan')[0]
        Converter.__init__(self, ckan_base_format, output_format)

    def __unicode__(self):
        return super(BaseConverter, self).__unicode__() + u' Base converter for CKAN metadata.'


class XSLConverter(Converter):

    def __init__(self, input_format, output_format, xsl_path):
        Converter.__init__(self, input_format, output_format)
        self.xsl_path = xsl_path

    def can_convert(self, record, check_version=False):
        return (super(XSLConverter, self).can_convert(record, check_version) and issubclass(type(record), XMLRecord))

    def convert(self, record):
        if self.can_convert(record):
            converted_content = self._xsl_transform(self.xsl_path, record)
            converted_record = Record(self.output_format, converted_content)
            if issubclass(type(self.output_format), XMLMetadataFormat):
                return XMLRecord.from_record(converted_record)
            return converted_record
        else:
            raise TypeError(('Converter is not compatible with the record format {record_format}({record_version}). ' +
                             'Accepted format is XML {input_format}({input_version}).').format(
                record_format=record.get_metadata_format().get_format_name(),
                record_version=record.get_metadata_format().get_version(),
                input_format=self.get_input_format().get_format_name(), input_version=self.input_format.get_version()))

    @classmethod
    def _xsl_transform(cls, xsl_path, record):
        return record.xsl_transform(xsl_path)

    def __unicode__(self):
        return super(XSLConverter, self).__unicode__() + (u' using XSL {xsl_path}').format(xsl_path=self.xsl_path)


class Converters(object):
    # Singleton
    class __Converters:
        def __init__(self):
            self.converters_dict = {}

        def add_converter(self, converter):
            # TODO: Check duplicates
            key = converter.get_input_format().get_format_name()
            if key not in self.converters_dict.keys():
                self.converters_dict[key] = []
            self.converters_dict[key] = [converter] + self.converters_dict[key]

        def set_converter(self, converter):
            key = converter.get_input_format().get_format_name()
            if key not in self.converters_dict.keys():
                self.converters_dict[key] = []
            self.converters_dict[key] = [converter]

        def add_converter_by_name(self, converter_name):
            package_name, class_name = converter_name.rsplit('.', 1)
            module = importlib.import_module(package_name)
            converter_class = getattr(module, class_name)
            converter = converter_class()
            if issubclass(type(converter), Converter):
                Converters().add_converter(converter)
            else:
                raise TypeError(
                    'Converter class {converter_class} is not a subclass of {standard_converter_class}.'.format(
                        converter_class=converter_class, standard_converter_class=Converter))
            return

        def get_num_converters(self):
            num = 0
            for key in self.converters_dict.keys():
                for metadata_converter in self.converters_dict[key]:
                    num += 1
            return num

        def get_all_converters(self):
            converters_list = [item for sublist in self.converters_dict.values() for item in sublist]
            return converters_list

        def get_converters_for_record(self, record, output_format=None, check_version=False):
            input_format = record.get_metadata_format()
            return self.get_converters_for_format(input_format, output_format, check_version)

        def get_converters_for_format(self, input_format, output_format=None, check_version=False):
            matching_converters_list = []
            for converter in self.converters_dict.get(input_format.get_format_name(), []):
                if converter.can_convert_format(input_format, output_format, check_version=check_version):
                    matching_converters_list += [converter]
            return matching_converters_list

        def find_conversion_chain(self, input_format, output_format, check_version=False, limit=3):
            initial_converters = self.get_converters_for_format(input_format, check_version=check_version)

            converter_chains = []
            for converter in initial_converters:
                converter_chain = [converter]
                if converter.can_convert_to_format(output_format, check_version=check_version):
                    return converter_chain
                else:
                    converter_chains += [converter_chain]

            for i in range(1, limit):
                new_converter_chains = []
                for converter_chain in converter_chains:
                    last_converter = converter_chain[-1]
                    next_converters = self.get_converters_for_format(last_converter.get_output_format(),
                                                                     check_version=check_version)
                    for converter in next_converters:
                        if converter not in converter_chain:
                            new_converter_chain = converter_chain + [converter]
                            if converter.can_convert_to_format(output_format, check_version=check_version):
                                return new_converter_chain
                            else:
                                new_converter_chains += [new_converter_chain]
                converter_chains = new_converter_chains
            return []

        def get_conversion(self, record, output_format, check_version=False, limit=3):
            input_format = record.get_metadata_format()
            conversion_chain = self.find_conversion_chain(input_format, output_format, check_version=check_version,
                                                          limit=limit)
            if not conversion_chain:
                return None
            latest_record = record
            for converter in conversion_chain:
                converted_record = converter.convert(latest_record)
                latest_record = converted_record
            return latest_record

        def __repr__(self):
            return str(self)

        def __str__(self):
            return str(self).encode('utf-8')

        def __unicode__(self):
            return (u'Converters ({num_converters}): {converters_dict}').format(
                num_converters=self.get_num_converters(), converters_dict=self.converters_dict)

    instance = None

    def __new__(cls):  # __new__ always a classmethod
        if not Converters.instance:
            Converters.instance = Converters.__Converters()
        return Converters.instance
