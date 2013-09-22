from gi.repository import Gtk
from gi.repository import GObject

class MaskTab(Gtk.HBox):
    __gsignals__ = {'new-mask':(GObject.SignalFlags.RUN_FIRST, None, ()),
                    'edit-mask':(GObject.SignalFlags.RUN_FIRST, None, ()),
                    'error':(GObject.SignalFlags.RUN_FIRST, None, (object,)),
                    }
    def __init__(self):
        Gtk.HBox.__init__(self)
        tb = Gtk.Toolbar()
        tb.set_show_arrow(False)
        tb.set_style(Gtk.ToolbarStyle.BOTH)
        self.pack_start(tb, False, True, 0)

        b = Gtk.ToolButton(Gtk.STOCK_NEW)
        tb.insert(b, -1)
        b.connect('clicked', self.on_button_clicked, 'new-mask')

        b = Gtk.ToolButton(Gtk.STOCK_EDIT)
        tb.insert(b, -1)
        b.connect('clicked', self.on_button_clicked, 'edit-mask')

    def on_button_clicked(self, widget, argument):  # IGNORE:W0613
        self.emit(argument)
