#!/usb/bin/env python

from setuptools import setup, find_packages


setup(name='sasgui', version='0.0.3', author='Andras Wacha',
      author_email='awacha@gmail.com', url='http://github.com/awacha/sasgui',
      description='Graphical User Interface utilities for small-angle scattering',
      packages=find_packages(),
      install_requires=['sastool>=0.1.3'],
      entry_points={'gui_scripts':['sas2dutil = sasgui.sasimagegui:sasimagegui_main'],
                    },
      keywords="saxs sans sas small-angle scattering x-ray neutron gui graphical user interface",
      license="",
      package_data={'sasgui': ['resource/*/*']},
      )
