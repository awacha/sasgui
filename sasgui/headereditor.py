from gi.repository import Gtk
from gi.repository import GObject

def _default_getter(header, key):
    return header[key]

def _default_setter(header, key, value):
    header[key] = value

class HeaderEditorColumn(object):
    """HeaderEditorColumn: interface between a TreeViewColumn and the corresponding field(s) of a SASHeader.
    """
    def __init__(self, title, coltype, fieldname):
        self.title = title
        self.coltype = coltype
        self.fieldname = fieldname
        if issubclass(self.coltype, basestring):
            self.renderer = Gtk.CellRendererText()
        elif issubclass(self.coltype, int):
            self.renderer = Gtk.CellRendererSpin()
            self.renderer.set_property('adjustment', Gtk.Adjustment(0))

class HeaderEditorConfig(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)
        self.headerfields_list = Gtk.ListStore(object, str, str)
        self.headerfields_view = Gtk.TreeView(self.headerfields_list)
        self.headerfields_view.get_selection().set_mode(Gtk.SelectionMode.BROWSE)
        self.headerfields_view.append_column(Gtk.TreeViewColumn('Column name', Gtk.CellRendereText(), text=1))
        self.fieldnames_list = Gtk.ListStore(str)
        self.headerfields_view.append_column(Gtk.TreeViewColumn('Header field', Gtk.CellRendererCombo(), text_column=2, model=self.fieldnames_list))
        
        
        sw = Gtk.ScrolledWindow()
        self.pack_start(sw, True, True, 0)
        sw.add(self.headerfields_view)
        vbb = Gtk.ButtonBox(orientation=Gtk.Orientation.VERTICAL)
        self.pack_start(vbb, False, True, 0)
        
        for stock, callback in [(Gtk.STOCK_ADD, self.add_entry),
                                (Gtk.STOCK_REMOVE, self.remove_entry),
                                (Gtk.STOCK_CLEAR, self.clear_list),
                                (Gtk.STOCK_GOTO_TOP, self.move_to_top),
                                (Gtk.STOCK_GO_UP, self.move_up),
                                (Gtk.STOCK_GO_DOWN, self.move_down),
                                (Gtk.STOCK_GOTO_BOTTOM, self.move.to_bottom),
                                ]:
            b = Gtk.Button(stock=stock)
            b.connect('clicked', lambda button:callback)
            vbb.pack_start(b, True, True, 0)
    def add_entry(self):
        model, it = self.headerfields_view.get_selection().get_selected()
        model.insert_before(it)
    def remove_entry(self):
        model, it = self.headerfields_view.get_selection().get_selected()
        if it is not None:
            model.remove(it)
    def clear_list(self):
        self.headerfields_list.clear()
    def move_to_top(self):
        model, it = self.headerfields_view.get_selection().get_selection()
        if it is not None:
            model.move_after(it, None)
    def move_up(self):
        model, it = self.headerfields_view.get_selection().get_selection()
        if it is not None:
            model.move_before(model.iter_previous(it), None)
    def move_down(self):
        model, it = self.headerfields_view.get_selection().get_selection()
        if it is not None:
            model.move_after(model.iter_next(it), None)
    def move_to_bottom(self):
        model, it = self.headerfields_view.get_selection().get_selection()
        if it is not None:
            model.move_before(it, None)

class HeaderEditor(Gtk.VBox):
    def __init__(self):
        Gtk.VBox.__init__(self)
        columns = None
        self.liststore = Gtk.ListStore(GObject.TYPE_PYOBJECT)
        self.treeview = Gtk.TreeView()
    def append_column(self, hecolumn):
        liststore1 = Gtk.ListStore(*([self.liststore.get_column_type(i) for i in range(self.liststore.get_n_columns())] + [hecolumn.coltype]))
        
