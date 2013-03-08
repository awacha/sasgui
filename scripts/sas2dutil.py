print "SAS2DUTIL STARTING"
import warnings
warnings.filterwarnings('error')
from sasgui.sasimagegui import SASImageGUIMain
from gi.repository import Gtk
print "IMPORTED"
mw = SASImageGUIMain()
print "INSTANTIATING DONE"
mw.show_all()
Gtk.main()
