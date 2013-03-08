from sastool.classes import SASHeader
from gi.repository import Gtk
import math
from gi.repository import GObject

def _default_getter(header, key):
    return header[key]

def _default_setter(header, key, value):
    header[key] = value

class HeaderEditorColumn(object):
    """HeaderEditorColumn: interface between a TreeViewColumn and the corresponding field(s) of a SASHeader.
    
    Main parameters:
        title: the title to be used as the column title in the TreeView
        coltype: the GObject.TYPE_??? type designator of this value.
        fieldname: the name of the field(s) of a SASHeader corresponding to this column. Only used as arguments of the getter and setter functions
        renderer: an instance of Gtk.CellRenderer or one of its subclasses.
        getter: function with the signature:   getter(header,fieldname). Should return a value which can be safely set into the column, i.e.
            is of the type coltype.
        setter: function with the signature:   setter(header, fieldname, value). Should update the field(s) in header designated by fieldname from
            value.
    """
    def __init__(self, title, coltype, fieldname, renderer, getter=_default_getter, setter=_default_setter, **kwargs):
        self.title = title
        self.coltype = coltype
        self.fieldname = fieldname
        self.renderer = renderer
        self.getter = getter
        self.setter = setter
        if isinstance(self.renderer, Gtk.CellRendererCombo):
            self.renderer.connect('changed', self.on_change_combo)
            self.renderer.connect('edited', self.on_edit_combo)
            self.colnum = kwargs['text']
        elif isinstance(self.renderer, Gtk.CellRendererSpin):
            self.renderer.connect('edited', self.on_edit_spinbutton)
            self.colnum = kwargs['text']
        elif isinstance(self.renderer, Gtk.CellRendererText):
            self.renderer.connect('edited', self.on_edit_text)
            self.colnum = kwargs['text']
        elif isinstance(self.renderer, Gtk.CellRendererToggle):
            self.renderer.connect('toggled', self.on_edit_toggle)
            self.colnum = kwargs['active']
        self.treeviewcolumn = Gtk.TreeViewColumn(title, self.renderer, **kwargs)
        if isinstance(self.renderer, Gtk.CellRendererCombo):
            self.renderer.set_property('model', Gtk.ListStore(GObject.TYPE_STRING))
            self.renderer.set_property('editable', True)
        elif isinstance(self.renderer, Gtk.CellRendererSpin):
            if 'spindigits' not in kwargs:
                spindigits = 0
            else:
                spindigits = kwargs['spindigits']
            if 'spinmin' not in kwargs:
                spinmin = 0
            else:
                spinmin = kwargs['spinmin']
            if 'spinmax' not in kwargs:
                spinmax = 1e100
            else:
                spinmax = kwargs['spinmax']
            if 'spinlowinc' not in kwargs:
                spinlowinc = pow(10, -spindigits)
            else:
                spinlowinc = kwargs['spinlowinc']
            if 'spinhighinc' not in kwargs:
                spinhighinc = pow(10, -spindigits + 2)
            else:
                spinhighinc = kwargs['spinhighinc']
            self.renderer.set_property('digits', spindigits)
            self.renderer.set_property('editable', True)
            self.renderer.set_property('adjustment', Gtk.Adjustment(spinmin, spinmin, spinmax, spinlowinc, spinhighinc))
        elif isinstance(self.renderer, Gtk.CellRendererText):
            self.renderer.set_property('editable', True)
        elif isinstance(self.renderer, Gtk.CellRendererToggle):
            self.renderer.set_property('activatable', True)
    def get_model(self):
        try:
            return self.treeviewcolumn.get_tree_view().get_model()
        except AttributeError:
            return None
    def on_change_combo(self, widget, path_string, new_iter):
        model = self.get_model()
        if model is None:
            return
        model[model.get_iter(path_string)] = widget[new_iter]
        self.setter(model[model.get_iter(path_string)][0], self.fieldname, widget[new_iter])
    def on_edit_combo(self, widget, path, new_text):
        model = self.get_model()
        if model is None:
            return
        self.setter(model[model.get_iter(path)][0], self.fieldname, new_text)
        self.update([m[0] for m in model])
        return True
    def on_edit_spinbutton(self, widget, path, new_text):
        model = self.get_model()
        if model is None:
            return
        self.setter(model[model.get_iter(path)][0], self.fieldname, new_text)
        self.update([m[0] for m in model])
        return True
    def on_edit_text(self, widget, path, new_text):
        model = self.get_model()
        if model is None:
            return
        self.setter(model[model.get_iter(path)][0], self.fieldname, new_text)
        self.update([m[0] for m in model])
        return True
    def on_edit_toggle(self, widget, path):
        model = self.get_model()
        if model is None:
            return
        self.setter(model[model.get_iter(path)][0], self.fieldname, widget.get_active())
        self.update([m[0] for m in model])
        return True
    def update(self, headers):
        model = self.get_model()
        if model is None:
            return
        if isinstance(self.renderer, Gtk.CellRendererCombo):
            combomodel = self.renderer.get_property(model)
            combomodel.clear()
            for data in sorted(set([self.getter(m[0], self.fieldname) for m in model])):
                combomodel.append_text(data)
        for m in model:
            value = self.getter(m[0], self.fieldname)
            m[self.colnum] = value
        return True
    
    
class HeaderEditor(Gtk.VBox):
    def __init__(self):
        Gtk.VBox.__init__(self)
        columns = None
        self.liststore = Gtk.ListStore(GObject.TYPE_PYOBJECT)
        self.treeview = Gtk.TreeView()
    def append_column(self, hecolumn):
        liststore1 = Gtk.ListStore(*([self.liststore.get_column_type(i) for i in range(self.liststore.get_n_columns())] + [hecolumn.coltype]))
        
