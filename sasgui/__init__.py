import gtk
import matplotlib
matplotlib.use('GTKAgg')

import sasimagegui
import maskmaker
import patheditor
import calibrator
import plot2dsasimage

__all__ = ['sasimagegui', 'maskmaker', 'patheditor', 'calibrator', 'plot2dsasimage']

from plot2dsasimage import *
from calibrator import *
from patheditor import *
from maskmaker import *
from sasimagegui import *

for x in __all__[:]:
    __all__.extend(eval('%s.__all__' % x))
