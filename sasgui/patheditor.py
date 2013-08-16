'''
Created on Apr 19, 2012

@author: andris
'''

from gi.repository import Gtk
from gi.repository import GObject
import os

from sastool import misc

__all__ = ['PathEditor', 'pathedit']

class PathEditor(Gtk.Dialog):
    __gtype_name__ = 'SASGUI_PathEditor'
    def __init__(self, parent=None, pathlist=None):
        if parent is not None:
            parent = parent.get_toplevel()
        if pathlist is None:
            pathlist = misc.searchpath.sastool_search_path
        elif not isinstance(pathlist, misc.searchpath.SearchPath):
            pathlist = misc.searchpath.SearchPath(pathlist)
        self.pathlist = pathlist

        Gtk.Dialog.__init__(self, 'Edit sastool search path...', parent,
                            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                             Gtk.STOCK_OK, Gtk.ResponseType.OK))
        self.set_default_response(Gtk.ResponseType.CANCEL)
        hbox = Gtk.HBox()
        self.get_content_area().pack_start(hbox, True, True, 0)

        sw = Gtk.ScrolledWindow()
        hbox.pack_start(sw, True, True, 0)

        self.pathstore = Gtk.ListStore(GObject.TYPE_STRING)
        self.tw = Gtk.TreeView(self.pathstore)
        sw.add(self.tw)
        self.tw.set_size_request(300, 150)
        self.tw.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)
        self.tw.set_rules_hint(True)
        self.tw.set_reorderable(True)
        self.tw.set_enable_search(True)


        pathcolumn = Gtk.TreeViewColumn('Folder', Gtk.CellRendererText(), text=0)
        self.tw.append_column(pathcolumn)

        bb = Gtk.VButtonBox()
        hbox.pack_start(bb, False, True, 0)
        b = Gtk.Button(label='Add folder')
        b.connect('clicked', self.callback_add)
        bb.add(b)
        b = Gtk.Button(label='Add current folder')
        b.connect('clicked', self.callback_add, '.')
        bb.add(b)
        b = Gtk.Button(label='Add home folder')
        b.connect('clicked', self.callback_add, os.path.expanduser('~'))
        bb.add(b)
        b = Gtk.Button(stock=Gtk.STOCK_GOTO_TOP)
        b.connect('clicked', self.callback_move, 'top')
        bb.add(b)
        b = Gtk.Button(stock=Gtk.STOCK_GO_UP)
        b.connect('clicked', self.callback_move, 'up')
        bb.add(b)
        b = Gtk.Button(stock=Gtk.STOCK_GO_DOWN)
        b.connect('clicked', self.callback_move, 'down')
        bb.add(b)
        b = Gtk.Button(stock=Gtk.STOCK_GOTO_BOTTOM)
        b.connect('clicked', self.callback_move, 'bottom')
        bb.add(b)
        b = Gtk.Button(stock=Gtk.STOCK_REMOVE)
        b.connect('clicked', self.callback_remove)
        bb.add(b)
        b = Gtk.Button(stock=Gtk.STOCK_CLEAR)
        b.connect('clicked', self.callback_clear)
        bb.add(b)
        b = Gtk.Button(stock=Gtk.STOCK_SAVE)
        b.connect('clicked', self.callback_savedefault)
        bb.add(b)


        self.update_from_search_path()
        self.show_all()
        self.hide()
    def run(self, *args, **kwargs):
        self.update_from_search_path()
        return Gtk.Dialog.run(self, *args, **kwargs)
    def update_from_search_path(self):
        self.pathstore.clear()
        for k in self.pathlist:
            self.pathstore.append([k])
    def update_search_path(self):
        it = self.pathstore.get_iter_first()
        mypath = []
        while it is not None:
            mypath.append(self.pathstore.get_value(it, 0))
            it = self.pathstore.iter_next(it)
        mypath = [p[0] for p in self.pathstore]
        self.pathlist.set(mypath)
    def callback_move(self, button, whatmove):
        it = self.tw.get_selection().get_selected()[1]
        if it is None:
            return
        if whatmove == 'down':
            nextit = self.pathstore.iter_next(it)
            if nextit is not None:
                self.pathstore.move_after(it, nextit)
        elif whatmove == 'up':
            nr = self.pathstore.get_path(it)[0]
            nr_to = max(nr - 1, 0)
            self.pathstore.move_before(it, self.pathstore.get_iter(nr_to))
        elif whatmove == 'top':
            self.pathstore.move_after(it, None)
        elif whatmove == 'bottom':
            self.pathstore.move_before(it, None)
        else:
            assert True
    def callback_remove(self, button=None):
        it = self.tw.get_selection().get_selected()[1]
        if it is None:
            return
        nr = self.pathstore.get_path(it)[0]
        self.pathstore.remove(it)
        if len(self.pathstore):
            self.tw.get_selection().select_iter(self.pathstore.get_iter(min(nr, len(self.pathstore) - 1)))
    def callback_clear(self, button=None):
        self.pathstore.clear()
    def callback_add(self, button=None, folder=None):
        if folder is not None:
            self.pathstore.prepend([folder])
            return True
        if not hasattr(self, '_filechooser_for_add'):
            self._filechooser_for_add = Gtk.FileChooserDialog(title='Choose folder...',
                parent=self, action=Gtk.FileChooserAction.SELECT_FOLDER,
                buttons=(Gtk.STOCK_OK, Gtk.ResponseType.OK, Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
            self._filechooser_for_add.set_modal(True)
            self._filechooser_for_add.set_transient_for(self)
            self._filechooser_for_add.set_destroy_with_parent(True)
            hbox = Gtk.HBox()
            self._filechooser_for_add.withsubfolders = Gtk.CheckButton('Recursive add')
            self._filechooser_for_add.withsubfolders.set_active(True)
            self._filechooser_for_add.recursedepth = Gtk.SpinButton()
            self._filechooser_for_add.recursedepth.set_digits(0)
            self._filechooser_for_add.recursedepth.set_value(1)
            self._filechooser_for_add.recursedepth.set_increments(1, 10)
            self._filechooser_for_add.recursedepth.set_range(1, 100)
            hbox.pack_start(self._filechooser_for_add.withsubfolders, False, True, 0)
            l = Gtk.Label(label='    Recursion depth:')
            l.set_alignment(0, 0.5)
            hbox.pack_start(l, False, True, 0)
            hbox.pack_start(self._filechooser_for_add.recursedepth, False, True, 0)
            hbox.show_all()
            self._filechooser_for_add.set_extra_widget(hbox)
        if self._filechooser_for_add.run() == Gtk.ResponseType.OK:
            folder = self._filechooser_for_add.get_filename()
            folder_slashes = os.path.abspath(folder).count(os.sep)
            recursedepth = self._filechooser_for_add.recursedepth.get_value_as_int()
            if self._filechooser_for_add.withsubfolders.get_active():
                [self.pathstore.prepend([x[0]]) for x in os.walk(folder)
                 if os.path.abspath(x[0]).count(os.sep) - folder_slashes <= recursedepth]
            else:
                self.pathstore.prepend([folder])
        self._filechooser_for_add.hide()
    def callback_savedefault(self, button=None):
        it = self.pathstore.get_iter_first()
        mypath = []
        while it is not None:
            mypath.append(self.pathstore.get_value(it, 0))
            it = self.pathstore.iter_next(it)
        misc.sastoolrc.set('misc.searchpath', mypath)

def pathedit(mainwindow=None, searchpath=None):
    pe = PathEditor(mainwindow, searchpath)
    if pe.run() == Gtk.ResponseType.OK:
        pe.update_search_path()
    pe.destroy()
