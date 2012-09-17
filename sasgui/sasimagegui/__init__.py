from mainwindow import SASImageGuiMain
import gtk

__all__ = ['SASImageGuiMain', 'sasimagegui_main']

def sasimagegui_main():
    mw = SASImageGuiMain()
    mw.show_all()
    gtk.main()
