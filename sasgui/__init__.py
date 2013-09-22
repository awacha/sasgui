from gi.repository import Gtk
from gi.repository import GObject
import matplotlib
matplotlib.use('GTK3Agg')

import sasimagegui
import maskmaker
import patheditor
import calibrator
import plot2dsasimage
import fitter
import plot1dsascurve
import peakfind
import fileentry
import multipeakfitter
import headereditor

__all__ = ['sasimagegui', 'maskmaker', 'patheditor', 'calibrator', 'plot2dsasimage', 'periodic', 'fitter', 'plot1dsascurve', 'peakfind', 'multipeakfitter', 'fileentry', 'headereditor']

from plot2dsasimage import *
from calibrator import *
from patheditor import *
from maskmaker import *
from sasimagegui import *
from periodic import *
from fitter import *
from plot1dsascurve import *
from peakfind import *
from multipeakfitter import *
from fileentry import *
from headereditor import *

for x in __all__[:]:
    __all__.extend(eval('%s.__all__' % x))
