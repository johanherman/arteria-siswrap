from setuptools import setup, find_packages
from siswrap import __version__
import os

def read_file(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='siswrap',
    version=__version__,
    description="Wrapper for the Sisyphus tools suite",
    long_description=read_file('README'),
    keywords='bioinformatics',
    author='SNP&SEQ Technology Platform, Uppsala University',
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [ 'siswrap-ws = siswrap.siswrap_ws:start' ]
    }
)
