from .mainwindow import SASImageGuiMain
from gi.repository import Gtk
from gi.repository import GObject
__all__ = ['SASImageGuiMain', 'sasimagegui_main']

def sasimagegui_main():
    mw = SASImageGuiMain()
    mw.show_all()
    Gtk.main()
