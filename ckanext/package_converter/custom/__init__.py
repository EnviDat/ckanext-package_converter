# this is a namespace package
try:
    import pkg_resources
    pkg_resources.declare_namespace(__name__)
except ImportError:
    import pkgutil
    __path__ = pkgutil.extend_path(__path__, __name__)

from ckanext.package_converter.custom.custom_converter import CustomMetadataFormat
from ckanext.package_converter.model.metadata_format import MetadataFormats

MetadataFormats().add_metadata_format(CustomMetadataFormat('this is a custom parameter'), replace=True)

