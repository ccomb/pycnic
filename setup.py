from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='pycnic',
      version=version,
      description="cnc command in python via usb",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='cnc usb python',
      author='Christophe Combelles',
      author_email='ccomb@gorfou.fr',
      url='',
      license='LGPL',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
          'pylibusb',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
