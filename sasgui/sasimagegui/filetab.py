from gi.repository import Gtk
import os
from gi.repository import GObject

from sastool import misc
from .. import patheditor
from sastool import classes

class FileTab(Gtk.HBox):
    __gsignals__ = {'error':(GObject.SignalFlags.RUN_FIRST, None, (object,)),
                    'adjust-path-clicked':(GObject.SignalFlags.RUN_FIRST, None, (object,)),
                    'new-clicked':(GObject.SignalFlags.RUN_FIRST, None, ()),
                    'close-clicked':(GObject.SignalFlags.RUN_FIRST, None, ()),
                    'quit-clicked':(GObject.SignalFlags.RUN_FIRST, None, ()),
                    'opened':(GObject.SignalFlags.RUN_FIRST, None, (object,))
                  }
    def __init__(self, searchpath=None):
        Gtk.HBox.__init__(self)

        self.oldexptype = None
        if searchpath is None:
            searchpath = misc.sastoolrc.get('misc.searchpath')
        self.searchpath = misc.searchpath.SearchPath(searchpath)
        self.data = None

        tb = Gtk.Toolbar()
        tb.set_show_arrow(False)
        tb.set_style(Gtk.ToolbarStyle.BOTH)
        self.pack_start(tb, False, True, 0)
        b = Gtk.ToolButton(Gtk.STOCK_NEW)
        tb.insert(b, -1)
        b.connect('clicked', self.on_button_clicked, 'new-clicked')
        b = Gtk.ToolButton(Gtk.STOCK_CLOSE)
        tb.insert(b, -1)
        b.connect('clicked', self.on_button_clicked, 'close-clicked')
        b = Gtk.ToolButton(Gtk.STOCK_QUIT)
        tb.insert(b, -1)
        b.connect('clicked', self.on_button_clicked, 'quit-clicked')
        b = Gtk.ToolButton(Gtk.STOCK_EDIT)
        b.set_label("Adjust path")
        b.set_stock_id(Gtk.STOCK_DIRECTORY)
        tb.insert(b, -1)
        b.connect('clicked', self.on_button_clicked, 'adjust-path-clicked')
        frame = Gtk.Frame()
        self.pack_start(frame, False, True, 0)
        tab = Gtk.Table()
        frame.add(tab)

        tablecolumn = 0
        tablerow = 0
        l = Gtk.Label(label='FSN:');  l.set_alignment(0, 0.5);  tab.attach(l, 2 * tablecolumn + 0, 2 * tablecolumn + 1, tablerow, tablerow + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.fsn_entry = Gtk.SpinButton()
        tab.attach(self.fsn_entry, 2 * tablecolumn + 1, 2 * tablecolumn + 2, tablerow, tablerow + 1)
        self.fsn_entry.set_range(0, 10000000000)
        self.fsn_entry.set_digits(0)
        self.fsn_entry.set_value(0)
        self.fsn_entry.set_increments(1, 10)

        tablerow += 1
        l = Gtk.Label(label='Experiment type:');  l.set_alignment(0, 0.5);  tab.attach(l, 2 * tablecolumn + 0, 2 * tablecolumn + 1, tablerow, tablerow + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.exptype_entry = Gtk.ComboBoxText()
        tab.attach(self.exptype_entry, 2 * tablecolumn + 1, 2 * tablecolumn + 2, tablerow, tablerow + 1)
        self.exptype_entry.connect('changed', self.on_exptype_changed)
        self.exptype_entry.append_text('ESRF ID02')
        self.exptype_entry.append_text('B1 org')
        self.exptype_entry.append_text('B1 int2dnorm')
        self.exptype_entry.append_text('PAXE')
        self.exptype_entry.append_text('HDF5')

        tablerow += 1
        l = Gtk.Label(label='Filename format:');  l.set_alignment(0, 0.5);  tab.attach(l, 2 * tablecolumn + 0, 2 * tablecolumn + 1, tablerow, tablerow + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.filenameformat_entry = Gtk.Entry()
        tab.attach(self.filenameformat_entry, 2 * tablecolumn + 1, 2 * tablecolumn + 2, tablerow, tablerow + 1)


        tablecolumn += 1
        tablerow = 0
        l = Gtk.Label(label='Mask file name:');  l.set_alignment(0, 0.5);  tab.attach(l, 2 * tablecolumn + 0, 2 * tablecolumn + 1, tablerow, tablerow + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.maskname_entry = Gtk.Entry()
        tab.attach(self.maskname_entry, 2 * tablecolumn + 1, 2 * tablecolumn + 2, tablerow, tablerow + 1)

        tablerow += 1
        self.loadmask_checkbox = Gtk.CheckButton('Load mask')
        tab.attach(self.loadmask_checkbox, 2 * tablecolumn + 0, 2 * tablecolumn + 2, tablerow, tablerow + 1)

        tablerow += 1
        l = Gtk.Label(label='Headername format:');  l.set_alignment(0, 0.5);  tab.attach(l, 2 * tablecolumn + 0, 2 * tablecolumn + 1, tablerow, tablerow + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.headernameformat_entry = Gtk.Entry()
        tab.attach(self.headernameformat_entry, 2 * tablecolumn + 1, 2 * tablecolumn + 2, tablerow, tablerow + 1)

        tablecolumn += 1
        b = Gtk.Button(stock=Gtk.STOCK_OPEN)
        b.set_image_position(Gtk.PositionType.TOP)
        tab.attach(b, 2 * tablecolumn + 0, 2 * tablecolumn + 2, 0, 3)
        b.connect('clicked', self.on_open)

        self.exptype_entry.set_active(0)


        self.show_all()
    def on_button_clicked(self, button, argument):  # IGNORE:W0613
        if argument == 'adjust-path-clicked':
            pe = patheditor.PathEditor(self, self.searchpath)
            try:
                ret = pe.run()
                if ret == Gtk.ResponseType.OK:
                    pe.update_search_path()
            finally:
                pe.destroy()
            self.emit(argument, self.searchpath)
        else:
            self.emit(argument)
    def on_exptype_changed(self, cbox):
        exptype = cbox.get_active_text().replace(' ', '_')
        if self.oldexptype is not None:
            misc.sastoolrc.set('gui.sasimagegui.file.headerformat_%s' % self.oldexptype, self.headernameformat_entry.get_text())
            misc.sastoolrc.set('gui.sasimagegui.file.fileformat_%s' % self.oldexptype, self.filenameformat_entry.get_text())
        try:
            self.headernameformat_entry.set_text(misc.sastoolrc.get('gui.sasimagegui.file.headerformat_%s' % exptype))
        except KeyError:
            self.headernameformat_entry.set_text('')
        try:
            self.filenameformat_entry.set_text(misc.sastoolrc.get('gui.sasimagegui.file.fileformat_%s' % exptype))
        except KeyError:
            self.filenameformat_entry.set_text('')
        self.oldexptype = exptype

    def on_open(self, button):  # IGNORE:W0613
        maskname = self.maskname_entry.get_text()
        if not maskname:
            maskname = None
        try:
            self.data = classes.SASExposure(self.filenameformat_entry.get_text(),
                                            self.fsn_entry.get_value_as_int(),
                                            dirs=self.searchpath,
                                            maskfile=maskname,
                                            load_mask=self.loadmask_checkbox.get_active(),
                                            experiment_type=self.exptype_entry.get_active_text().replace(' ', '_'),
                                            fileformat=os.path.splitext(os.path.split(self.filenameformat_entry.get_text())[-1])[0],
                                            logfileformat=os.path.splitext(self.headernameformat_entry.get_text())[0],
                                            logfileextn=os.path.splitext(self.headernameformat_entry.get_text())[1])
        except IOError as ioe:
            self.emit('error', ioe)
        else:
            GObject.idle_add(self.call_callbacks_on_open)
        return True
    def call_callbacks_on_open(self):
        if self.data:
            self.emit('opened', self.data)
        return False
