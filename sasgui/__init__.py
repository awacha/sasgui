from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import GdkPixbuf
import os
import pkg_resources
import matplotlib
matplotlib.use('GTK3Agg')

iconfactory = Gtk.IconFactory()
for f, n in [('circle.png', 'Select a circle'),
          ('histogram_masked.png', 'Select from intensity histogram (only masked pixels'),
          ('histogram.png', 'Select from histogram'),
          ('infandnan.png', 'Select nonfinite pixels'),
          ('invert_mask.png', 'Invert mask'),
          ('pixelhunt.png', 'Pixel hunting'),
          ('polygon.png', 'Select polygon'),
          ('rectangle.png', 'Select rectangle'),
          ('nonpositive.png', 'Select non-positive pixels'),
          ('piechart.png', 'Open statistics window')]:
    basename = os.path.splitext(f)[0]
    iconset = Gtk.IconSet(GdkPixbuf.Pixbuf.new_from_file(pkg_resources.resource_filename('sasgui', 'resource/icons/%s' % f)))
    # Gtk.stock_add([('sasgui_%s' % basename, n, 0, 0, 'C')])
    iconfactory.add('sasgui_%s' % basename, iconset)
iconfactory.add_default()


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
