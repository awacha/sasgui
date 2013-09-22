from gi.repository import Gtk
from gi.repository import GObject
from sastool.classes.headerfields import SASHeaderField
from sastool.classes import SASBeamTime

__all__ = ['HeaderEditor']

class HeaderEditorConfigDialog(Gtk.Dialog):
    def __init__(self, title='Select header fields to display', parent=None,
                 flags=Gtk.DialogFlags.DESTROY_WITH_PARENT | Gtk.DialogFlags.MODAL,
                 buttons=(Gtk.STOCK_OK, Gtk.ResponseType.OK, Gtk.STOCK_APPLY,
                          Gtk.ResponseType.APPLY, Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)):
        Gtk.Dialog.__init__(self, title, parent, flags, buttons)
        self._treemodel = Gtk.ListStore(GObject.TYPE_BOOLEAN, GObject.TYPE_STRING, GObject.TYPE_STRING)
        self._treeview = Gtk.TreeView(self._treemodel)
        self._treeview.set_headers_visible(True)
        self._treeview.set_rules_hint(True)
        self._treeview.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
        cr = Gtk.CellRendererToggle()
        cr.set_activatable(True)
        self._treeview.append_column(Gtk.TreeViewColumn('Visible', cr, active=0))
        cr.connect('toggled', self._on_visibility_toggled)
        self._treeview.append_column(Gtk.TreeViewColumn('Field name', Gtk.CellRendererText(), text=1))
        self._treeview.append_column(Gtk.TreeViewColumn('Description', Gtk.CellRendererText(), text=2))
        
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_size_request(-1, 300)
        sw.add(self._treeview)
        hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.get_content_area().pack_start(hb, True, True, 0)
        hb.pack_start(sw, True, True, 0)
        
        bbox = Gtk.ButtonBox(orientation=Gtk.Orientation.VERTICAL)
        hb.pack_start(bbox, False, False, 0)
        bbox.set_layout(Gtk.ButtonBoxStyle.START)
        
        b = Gtk.Button(stock=Gtk.STOCK_GOTO_TOP)
        bbox.add(b)
        b.connect('clicked', self._move_top)
        b = Gtk.Button(stock=Gtk.STOCK_GO_UP)
        bbox.add(b)
        b.connect('clicked', self._move_up)
        b = Gtk.Button(stock=Gtk.STOCK_GO_DOWN)
        bbox.add(b)
        b.connect('clicked', self._move_down)
        b = Gtk.Button(stock=Gtk.STOCK_GOTO_BOTTOM)
        bbox.add(b)
        b.connect('clicked', self._move_bottom)
        self.show_all()
        
    def _move_top(self, button):
        model, it = self._treeview.get_selection().get_selected()
        if it is None:
            return
        model.move_after(it, None)

    def _move_up(self, button):
        model, it = self._treeview.get_selection().get_selected()
        if it is None:
            return
        prev = model.iter_previous(it)
        if prev is not None:
            model.move_before(it, prev)

    def _move_down(self, button):
        model, it = self._treeview.get_selection().get_selected()
        if it is None:
            return
        next = model.iter_next(it)
        if next is not None:
            model.move_after(it, next)

    def _move_bottom(self, button):
        model, it = self._treeview.get_selection().get_selected()
        if it is None:
            return
        model.move_before(it, None)
        
    def _on_visibility_toggled(self, crt, path):
        self._treemodel[path][0] ^= True
        return True
    
    def get_visible_fields(self):
        return [row[1] for row in self._treemodel if row[0]]
    
    def set_visible_fields(self, fieldslist):
        self._treemodel.clear()
        for shf in [SASHeaderField.get_instance(fn) for fn in fieldslist]:
            self._treemodel.append((True, shf.fieldname, shf.mnemonic))
        for shf in [shf for shf in SASHeaderField._allknownfields if shf.fieldname not in fieldslist]:
            self._treemodel.append((False, shf.fieldname, shf.mnemonic))
            

class HeaderEditor(Gtk.Box):
    def __init__(self, sasbeamtime):
        self._fieldnames = ['FSN', 'Date', 'Title', 'MeasTime', 'Dist', 'Energy', 'Temperature']
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self._beamtime = sasbeamtime
        self._treemodel = Gtk.ListStore(GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT)
        self._treeview = Gtk.TreeView(self._treemodel)
        self._treeview.set_headers_visible(True)
        self._treeview.set_headers_clickable(True)
        self._treeview.set_rules_hint(True)
        self._treeview.set_rubber_banding(True)
        self._treeview.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self._bbox = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        self.pack_start(self._bbox, False, False, 0)
        self._swindow = Gtk.ScrolledWindow()
        self.pack_start(self._swindow, True, True, 0)
        self._swindow.add(self._treeview)
        self._swindow.set_size_request(400, 300)
        self.reload_headers()
        self._update_treeview()
        
        
        self._commit_button = Gtk.Button(label='Commit')
        self._bbox.pack_start(self._commit_button, True, True, 0)
        self._commit_button.connect('clicked', lambda b:self._on_commit())
        
        self._forget_button = Gtk.Button(label='Forget')
        self._bbox.pack_start(self._forget_button, True, True, 0)
        self._forget_button.connect('clicked', lambda b:self._on_forget())
        
        self._apply1_button = Gtk.Button(label='Apply 1 down')
        self._bbox.pack_start(self._apply1_button, True, True, 0)
        self._apply1_button.connect('clicked', lambda b:self._on_apply1())
        
        self._applyall_button = Gtk.Button(label='Apply all down')
        self._bbox.pack_start(self._applyall_button, True, True, 0)
        self._applyall_button.connect('clicked', lambda b:self._on_applyall())

        self._configure_button = Gtk.Button(label='Configure')
        self._bbox.pack_start(self._configure_button, True, True, 0)
        self._configure_button.connect('clicked', lambda b:self._on_configure())


        self._commit_button.set_sensitive(False)
        self._apply1_button.set_sensitive(False)
        self._applyall_button.set_sensitive(False)
        self._forget_button.set_sensitive(False)

        self.connect('notify::orientation', self._on_orientation_changed)
        
        self.show_all()
    
    def _on_configure(self):
        cd = HeaderEditorConfigDialog(parent=self.get_toplevel())
        cd.set_visible_fields(self._fieldnames)
        while True:
            result = cd.run()
            if result == Gtk.ResponseType.APPLY:
                self._fieldnames = cd.get_visible_fields()
                self._update_treeview()
            elif result == Gtk.ResponseType.OK:
                self._fieldnames = cd.get_visible_fields()
                self._update_treeview()
                break
            elif result == Gtk.ResponseType.CANCEL:
                break
            elif result == Gtk.ResponseType.DELETE_EVENT:
                break
        cd.destroy()
        del cd
    
    def _on_orientation_changed(self, self_, prop):
        if prop.name == 'orientation':
            self.remove(self._swindow)
            self.remove(self._bbox)
            if self.get_property('orientation') == Gtk.Orientation.VERTICAL:
                self._bbox.set_orientation(Gtk.Orientation.HORIZONTAL)
                self.pack_start(self._bbox, False, False, 0)
                self.pack_start(self._swindow, True, True, 0)
            else:
                self._bbox.set_orientation(Gtk.Orientation.VERTICAL)
                self.pack_start(self._swindow, True, True, 0)
                self.pack_start(self._bbox, False, False, 0)
        return False
    
    def _on_commit(self):
        self._forget_button.set_sensitive(False)
        self._commit_button.set_sensitive(False)
        self._apply1_button.set_sensitive(False)
        self._applyall_button.set_sensitive(False)
    
    def _on_forget(self):
        self._forget_button.set_sensitive(False)
        self._commit_button.set_sensitive(False)
        self._apply1_button.set_sensitive(False)
        self._applyall_button.set_sensitive(False)
        self.reload_headers(True)
    
    def _on_apply1(self):
        it = self._treemodel.get_iter_first()
        just_modified = []
        while it is not None:
            nextit = self._treemodel.iter_next(it)
            if nextit is None:
                it = nextit
                continue
            if self._treemodel[it][1] is not None:
                # if there are some changes, self._treemodel[it][1] is a list of the names
                # of the affected fields.
                new_just_modified = []
                # now go through the affected fields, ignoring those which were modified
                # only during the previous iteration.
                for fn in [x for x in self._treemodel[it][1] if x not in just_modified]:
                    if (self._treemodel[nextit][1] is None) or (fn not in self._treemodel[nextit][1]):
                        # if this field is not yet changed in the next row, add this fieldname to the skip list
                        # of the next iteration. We thus avoid to propagate the change more than one times.
                        new_just_modified.append(fn)
                    # get the treeview column.
                    self._on_cell_edited([c for c in self._treeview.get_columns() if c.get_title() == fn][0].get_cells()[0],
                                         self._treemodel.get_path(nextit),
                                         SASHeaderField.get_instance(fn).tostring(self._treemodel[it][0][fn]), fn, True)
            just_modified = new_just_modified
            it = nextit
    
    def _on_applyall(self):
        it = self._treemodel.get_iter_first()
        alreadydone = []
        while it is not None:
            nextit = self._treemodel.iter_next(it)
            if nextit is None:
                it = nextit
                continue
            if self._treemodel[it][1] is not None:
                for fn in [n for n in self._treemodel[it][1] if n not in alreadydone]:
                    ni = nextit
                    while ni is not None:
                        tvc = [c for c in self._treeview.get_columns() if c.get_title() == fn][0]
                        self._on_cell_edited(tvc.get_cells()[0], self._treemodel.get_path(ni), SASHeaderField.get_instance(fn).tostring(self._treemodel[it][0][fn]), fn, True)
                        ni = self._treemodel.iter_next(ni)
                    alreadydone.append(fn)
            it = nextit
    
    def append_columns(self, *names):
        self._validate_column_names(*names)
        self._fieldnames.extend(names)
        self._update_treeview()
    
    def remove_columns(self, *names):
        for c in self._treeview.get_columns()[:]:
            if c.get_title() in names:
                self._treeview.remove_column(c)
        for n in names:
            self._fieldnames.remove(n)
    
    def insert_column(self, name, idx=0):
        self._validate_column_names(name)
        self._fieldnames.insert(idx, name)
        self._update_treeview()
    
    def _cell_datafunction(self, column, renderer, model, iterator, sasheaderfield):
        try:
            value = sasheaderfield.tostring(model[iterator][0][sasheaderfield.fieldname])
        except KeyError:
            value = 'N/A'
        renderer.set_property('text', value)
        if (model[iterator][1] is not None) and (sasheaderfield.fieldname in model[iterator][1]):
            renderer.set_property('background', 'yellow')
            renderer.set_property('background-set', True)
        else:
            renderer.set_property('background-set', False)
    
    def _on_cell_edited(self, cellrenderer, path, newtext, fieldname, force_edit=False):
        shf = SASHeaderField.get_instance(fieldname)
        newvalue = shf.fromstring(newtext)
        if (self._treemodel[path][0][fieldname] == newvalue) and not force_edit:
            return True
        self._treemodel[path][0][fieldname] = newvalue
        if self._treemodel[path][1] is None:
            self._treemodel[path][1] = []
        self._treemodel[path][1].append(fieldname)
        self._cell_datafunction([c for c in self._treeview.get_columns() if c.get_title() == fieldname][0], cellrenderer, self._treemodel, self._treemodel.get_iter(path), shf)
        self._apply1_button.set_sensitive(True)
        self._applyall_button.set_sensitive(True)
        self._commit_button.set_sensitive(True)
        self._forget_button.set_sensitive(True)
    
    def _update_treeview(self):
        for col in self._treeview.get_columns()[:]:
            self._treeview.remove_column(col)
        if hasattr(self, '_renderer_connections'):
            for cr, conn in self._renderer_connections:
                cr.disconnect(conn)
            del self._renderer_connections
        self._renderer_connections = []
        for fn in self._fieldnames:
            cr = Gtk.CellRendererText()
            cr.set_property('editable', True)
            self._renderer_connections.append((cr, cr.connect('edited', self._on_cell_edited, fn)))
            shf = SASHeaderField.get_instance(fn)
            tvc = Gtk.TreeViewColumn(shf.fieldname, cr)
            tvc.set_cell_data_func(cr, self._cell_datafunction, shf)
            self._treeview.append_column(tvc)
            
    def reload_headers(self, forced=False):
        self._beamtime.refresh_cache(forced)
        self._treemodel.clear()
        for h in self._beamtime:
            self._treemodel.append((h, None))
        return True

    def _validate_column_names(self, *names):
        try:
            [SASHeaderField.get_instance(n) for n in names]
        except ValueError as ve:
            raise ve
            
