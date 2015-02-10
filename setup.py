from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(
    name='ckanext-storage-admin-gui',
    version=version,
    description="gui for ckanext-storage-admin",
    long_description='''
    ''',
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='Dominik Kapisinsky',
    author_email='kapisinsky@microcomp.sk',
    url='github.com/microcomp',
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.storage_gui'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
    ],
    entry_points='''
        [ckan.plugins]
        # Add plugins here, e.g.
        storage_admin_gui=ckanext.storage_gui.plugin:StorageAdminGui
    ''',
)
