from mainwindow import SASImageGuiMain
import gtk

def sasimagegui_main():
    mw = SASImageGuiMain()
    mw.show_all()
    gtk.main()
