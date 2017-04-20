.. You should enable this project on travis-ci.org and coveralls.io to make
   these badges work. The necessary Travis and Coverage config files have been
   generated for you.

.. image:: https://travis-ci.org/espona/ckanext-package_converter.svg?branch=master
    :target: https://travis-ci.org/espona/ckanext-package_converter

.. image:: https://coveralls.io/repos/github/espona/ckanext-package_converter/badge.svg?branch=master
    :target: https://coveralls.io/github/espona/ckanext-package_converter?branch=master

.. image:: https://pypip.in/download/ckanext-package_converter/badge.svg
    :target: https://pypi.python.org/pypi//ckanext-package_converter/
    :alt: Downloads

.. image:: https://pypip.in/version/ckanext-package_converter/badge.svg
    :target: https://pypi.python.org/pypi/ckanext-package_converter/
    :alt: Latest Version

.. image:: https://pypip.in/py_versions/ckanext-package_converter/badge.svg
    :target: https://pypi.python.org/pypi/ckanext-package_converter/
    :alt: Supported Python versions

.. image:: https://pypip.in/status/ckanext-package_converter/badge.svg
    :target: https://pypi.python.org/pypi/ckanext-package_converter/
    :alt: Development Status

.. image:: https://pypip.in/license/ckanext-package_converter/badge.svg
    :target: https://pypi.python.org/pypi/ckanext-package_converter/
    :alt: License

=============
ckanext-package_converter
=============

.. Put a description of your extension here:
This extension allows the export (and soon import) of CKAN package metadata to multiple formats.
It allows the user to easily define custom converters and reuse existing ones.
Formats supported: DataCite, OAI_DC,...

------------
Requirements
------------
It is compatible with ckanext-scheming, ckanext-repeating, ckanext-composite and ckanext-spatial.
This extension has been developed for CKAN 2.5.2.

------------
Installation
------------

.. Add any additional install steps to the list below.
   For example installing any non-Python dependencies or adding any required
   config settings.

To install ckanext-package_converter:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/default/bin/activate

2. Install the ckanext-package_converter Python package into your virtual environment::

     pip install ckanext-package_converter

3. Add ``package_converter`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload


---------------
Config Settings
---------------

You can define custom converters by adding them to the Converters() object directly or
via the configuration file. For example::

    # full path to converters (optional)
    package_converter.converters = ckanext.package_converter.model.scheming_converter.Datacite31SchemingConverter
  


------------------------
Development Installation
------------------------

To install ckanext-package_converter for development, activate your CKAN virtualenv and
do::

    git clone https://github.com/espona/ckanext-package_converter.git
    cd ckanext-package_converter
    python setup.py develop
    pip install -r dev-requirements.txt


-----------------
Running the Tests
-----------------

To run the tests, do::

    nosetests --nologcapture --with-pylons=test.ini

To run the tests and produce a coverage report, first make sure you have
coverage installed in your virtualenv (``pip install coverage``) then run::

    nosetests --nologcapture --with-pylons=test.ini --with-coverage --cover-package=ckanext.package_converter --cover-inclusive --cover-erase --cover-tests


---------------------------------
Registering ckanext-package_converter on PyPI
---------------------------------

ckanext-package_converter should be availabe on PyPI as
https://pypi.python.org/pypi/ckanext-package_converter. If that link doesn't work, then
you can register the project on PyPI for the first time by following these
steps:

1. Create a source distribution of the project::

     python setup.py sdist

2. Register the project::

     python setup.py register

3. Upload the source distribution to PyPI::

     python setup.py sdist upload

4. Tag the first release of the project on GitHub with the version number from
   the ``setup.py`` file. For example if the version number in ``setup.py`` is
   0.0.1 then do::

       git tag 0.0.1
       git push --tags


----------------------------------------
Releasing a New Version of ckanext-package_converter
----------------------------------------

ckanext-package_converter is availabe on PyPI as https://pypi.python.org/pypi/ckanext-package_converter.
To publish a new version to PyPI follow these steps:

1. Update the version number in the ``setup.py`` file.
   See `PEP 440 <http://legacy.python.org/dev/peps/pep-0440/#public-version-identifiers>`_
   for how to choose version numbers.

2. Create a source distribution of the new version::

     python setup.py sdist

3. Upload the source distribution to PyPI::

     python setup.py sdist upload

4. Tag the new release of the project on GitHub with the version number from
   the ``setup.py`` file. For example if the version number in ``setup.py`` is
   0.0.2 then do::

       git tag 0.0.2
       git push --tags
