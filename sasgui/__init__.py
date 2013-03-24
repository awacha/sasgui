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

__all__ = ['sasimagegui', 'maskmaker', 'patheditor', 'calibrator', 'plot2dsasimage', 'periodic', 'fitter', 'plot1dsascurve', 'peakfind']

from plot2dsasimage import *
from calibrator import *
from patheditor import *
from maskmaker import *
from sasimagegui import *
from periodic import *
from fitter import *
from plot1dsascurve import *
from peakfind import *

for x in __all__[:]:
    __all__.extend(eval('%s.__all__' % x))
