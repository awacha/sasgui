#!/usb/bin/env python

from setuptools import setup, find_packages


setup(name='sasgui', version='0.0.1', author='Andras Wacha',
      author_email='awacha@gmail.com', url='http://github.com/awacha/sasgui',
      description='Graphical User Interface utilities for small-angle scattering',
      packages=find_packages(),
      install_requires=['PyGObject'],
      #entry_points={'gui_scripts':['sas2dutil = sastool:_sas2dgui_main_program'],
      #              },
      keywords="saxs sans sas small-angle scattering x-ray neutron gui graphical user interface",
      license="",
      package_data={'sasgui': ['resource/*/*']},
      )
