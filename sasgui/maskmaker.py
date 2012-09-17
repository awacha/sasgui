'''
Created on Feb 14, 2012

@author: andris
'''

from .plot2dsasimage import PlotSASImage
from sastool.io.twodim import readmask

import gtk
import re
import matplotlib
import pkg_resources

import uuid
import numpy as np
import matplotlib.nxutils
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg, \
NavigationToolbar2GTKAgg
from matplotlib.figure import Figure
import os
import scipy.io

from sastool.classes import SASExposure, SASMask
from sastool import misc

__all__ = ['MaskMaker', 'makemask']

iconfactory = gtk.IconFactory()
for f, n in [('circle.png', 'Select a circle'),
          ('histogram_masked.png', 'Select from intensity histogram (only masked pixels'),
          ('histogram.png', 'Select from histogram'),
          ('infandnan.png', 'Select nonfinite pixels'),
          ('invert_mask.png', 'Invert mask'),
          ('pixelhunt.png', 'Pixel hunting'),
          ('polygon.png', 'Select polygon'),
          ('rectangle.png', 'Select rectangle'),
          ('nonpositive.png', 'Select non-positive pixels')]:
    basename = os.path.splitext(f)[0]
    iconset = gtk.IconSet(gtk.gdk.pixbuf_new_from_file(pkg_resources.resource_filename('sasgui', 'resource/icons/%s' % f)))
    gtk.stock_add([('sasgui_%s' % basename, n, 0, 0, 'C')])
    iconfactory.add('sasgui_%s' % basename, iconset)
iconfactory.add_default()

class HistogramSelector(gtk.Dialog):
    def __init__(self, data, *args, **kwargs):
        gtk.Dialog.__init__(self, *args, **kwargs)
        self.set_default_response(gtk.RESPONSE_CANCEL)
        self._data = data
        vbox = self.get_content_area()
        hbox = gtk.HBox()
        vbox.pack_start(hbox, False)
        l = gtk.Label('Number of histogram bins:')
        l.set_alignment(0, 0.5)
        hbox.pack_start(l, False)
        self.nbins_spin = gtk.SpinButton()
        hbox.pack_start(self.nbins_spin)
        self.nbins_spin.set_range(0, 1e100)
        self.nbins_spin.set_increments(1, 10)
        self.nbins_spin.set_digits(0)
        self.nbins_spin.set_numeric(True)
        self.nbins_spin.connect('changed', self.on_nbins_changed)
        b = gtk.Button(gtk.STOCK_APPLY)
        hbox.pack_star(b, False)
        b.connect('clicked', self.on_nbins_changed)
        self.fig = Figure((640 / 72., 480 / 72.), 72)
        self.canvas = FigureCanvasGTKAgg(self.fig)
        self.canvas.set_size_request(300, 200)
        vbox.pack_start(self.canvas)
        self.figure_toolbar = NavigationToolbar2GTKAgg(self.canvas, self)
        vbox.pack_start(self.figure_toolbar, False)
        self.fig.add_subplot(1, 1, 1)
        self.show_all()
        self.hide()
    def get_data(self):
        return self._data
    def set_data(self, value):
        self._data = value
        self.on_bins_changed(None)
    data = property(get_data, set_data)
    def set_nbins(self, value):
        self.nbins_spin.set_value(value)
        self.on_nbins_changed(self.nbins_spin)
    def get_nbins(self):
        return self.nbins_spin.get_value_as_int()
    nbins = property(get_nbins, set_nbins)
    def on_nbins_changed(self, widget):
        self.fig.gca().cla()
        self.fig.gca().hist(self.data, self.nbins)
        self.fig.canvas.draw()
        return True
    def get_xlimits(self):
        return self.fig.gca().axis()[0:2]
    def gca(self):
        return self.fig.gca()

class StatusLine(gtk.HBox):
    _signal_handlers = []
    _button_clicks = []

    def __init__(self, Nbuttons=2):
        gtk.HBox.__init__(self)
        self.label = gtk.Label()
        self.label.set_alignment(0, 0)
        self.pack_start(self.label)
        self.button = []
        for i in range(Nbuttons):
            self.button.append(gtk.Button())
            self.pack_start(self.button[i], False, True)
            self.button[i].connect('clicked', self.buttonclicked)
        self._button_clicks = [0] * Nbuttons
        self.label.show()
        self.connect('expose_event', self.on_expose)

    def buttonclicked(self, widget):
        i = self.button.index(widget)
        self._button_clicks[i] += 1
        for f, a, kw in self._signal_handlers:
            f(self, i, *a, **kw)   #IGNORE:W0142

    def connect(self, eventname, function, *args, **kwargs):
        if eventname == 'buttonclicked':
            hid = uuid.uuid4()
            self._signal_handlers.append((hid, function, args, kwargs))
        else:
            return gtk.HBox.connect(self, eventname, function, *args, **kwargs)

    def disconnect(self, hid):
        self._signal_handlers = [x for x in self._signal_handlers \
                                 if not x[0] == hid]

    def setup(self, text=None, *args):
        if text is None:
        #    self.hide()
            text = ''
        #else:
        #    self.show()
        self.label.set_text(text)
        for b in self.button:
            b.set_label('')
            b.hide()
        for b, t in zip(self.button, args):
            if t is not None:
                b.set_label(t)
                b.show()

    def clear(self):
        self.setup('')
        self.hide()

    def nbuttonclicks(self, i=None):
        if i is None:
            ret = self._button_clicks[:]
            self._button_clicks = [0] * len(self._button_clicks)
        else:
            ret = self._button_clicks[i]
            self._button_clicks[i] = 0
        return ret

    def on_expose(self, *args): #IGNORE:W0613
        for b in self.button:
            b.set_visible(bool(b.get_label()))

    def reset_counters(self, n=None):
        if n is None:
            self._button_clicks = [0] * len(self._button_clicks)
        else:
            self._button_clicks[n] = 0

class GraphToolbarVisibility(object):

    def __init__(self, toolbar, *args):
        self.graphtoolbar = toolbar
        self.widgetstohide = args
        self._was_zooming = False
        self._was_panning = False

    def __enter__(self):
        if self.graphtoolbar.mode.startswith('zoom'):
            self.graphtoolbar.zoom()
            self._was_zooming = True
        else:
            self._was_zooming = False
        if self.graphtoolbar.mode.startswith('pan'):
            self.graphtoolbar.pan()
            self._was_panning = True
        else:
            self._was_panning = False
        self.graphtoolbar.set_sensitive(False)
        for w in self.widgetstohide:
            w.set_sensitive(False)
        while gtk.events_pending():
            gtk.main_iteration()

    def __exit__(self, *args, **kwargs):
        if self._was_panning:
            self.graphtoolbar.pan()
        if self._was_zooming:
            self.graphtoolbar.zoom()
        self.graphtoolbar.set_sensitive(True)
        for w in self.widgetstohide:
            w.set_sensitive(True)
        while gtk.events_pending():
            gtk.main_iteration()


class MaskMaker(gtk.Dialog):
    _mouseclick_mode = None  # Allowed: 'Points', 'Lines', 'PixelHunt' and None
    _mouseclick_last = ()
    _selection = None
    _maskimage = None
    _extra_lines = []
    _mask_backup = []
    def __init__(self, title='Make mask...', parent=None,
                 flags=gtk.DIALOG_DESTROY_WITH_PARENT | \
                 gtk.DIALOG_NO_SEPARATOR,
                 buttons=(gtk.STOCK_OK, gtk.RESPONSE_OK, gtk.STOCK_CANCEL,
                          gtk.RESPONSE_CANCEL),
                 matrix=None, mask=None, maskid=None):
        if matrix is None:
            raise ValueError("Argument 'matrix' is required!")
        if not isinstance(matrix, SASExposure):
            matrix = SASExposure(matrix)
            if mask is None:
                matrix.set_mask(np.ones_like(matrix).astype(np.bool8))
        elif mask is not None:
            matrix.set_mask(mask)
        gtk.Dialog.__init__(self, title, parent, flags, buttons)
        self._exposure = matrix

        self.set_default_response(gtk.RESPONSE_CANCEL)

        clearbutton = gtk.Button(stock=gtk.STOCK_NEW)
        self.get_action_area().pack_end(clearbutton)
        clearbutton.connect('clicked', self.newmask)
        clearbutton.show()
        savebutton = gtk.Button(stock=gtk.STOCK_SAVE_AS)
        self.get_action_area().pack_end(savebutton)
        savebutton.connect('clicked', self.savemask)
        savebutton.show()
        loadbutton = gtk.Button(stock=gtk.STOCK_OPEN)
        self.get_action_area().pack_end(loadbutton)
        loadbutton.connect('clicked', self.loadmask)
        loadbutton.show()

        vbox = self.get_content_area()
        self.toolbar = gtk.Toolbar()
        self.toolbar.set_style(gtk.TOOLBAR_ICONS)
        vbox.pack_start(self.toolbar, False, True)


        self.fig = PlotSASImage()
        self.fig.exposure = self.exposure
        vbox.pack_start(self.fig)
        self.graphtoolbar = self.fig.figure_toolbar
        self.fig.canvas.mpl_connect('button_press_event', self._on_matplotlib_mouseclick)

        self.pixelhunt_button = gtk.ToggleToolButton('sasgui_pixelhunt')
        self.toolbar.insert(self.pixelhunt_button, -1)
        self.pixelhunt_button.connect('toggled', self.on_pixel_hunt)

        self.maskingmode = gtk.combo_box_new_text()
        self.maskingmode.append_text('mask')
        self.maskingmode.append_text('unmask')
        self.maskingmode.append_text('invert')
        self.maskingmode.set_active(0)
        ti = gtk.ToolItem()
        ti.add(self.maskingmode)
        self.toolbar.insert(ti, -1)

        for name, stock in [('Rectangle', 'sasgui_rectangle'),
                           ('Circle', 'sasgui_circle'),
                           ('Polygon', 'sasgui_polygon'),
                           ('Histogram_masked', 'sasgui_histogram_masked'),
                           ('Histogram_all', 'sasgui_histogram'),
                           ('Invert', 'sasgui_invert_mask'),
                           ('Mask_nonfinite', 'sasgui_infandnan'),
                           ('Mask_nonpositive', 'sasgui_nonpositive')]:
            b = gtk.ToolButton(stock)
            self.toolbar.insert(b, -1)
            b.connect('clicked', self.on_button_clicked, name)
        self.undobutton = gtk.ToolButton(gtk.STOCK_UNDO)
        self.toolbar.insert(self.undobutton, -1)
        self.undobutton.connect('clicked', self.on_button_clicked, 'Undo')
        self.undobutton.set_sensitive(False)

        self.statusline = StatusLine()
        self.statusline.setup(None)
        self.get_content_area().pack_start(self.statusline, False, True, 0)

        self.get_content_area().show_all()
        self.update_graph()
    def backup_mask(self):
        self._mask_backup.append(self.mask)
        self.undobutton.set_sensitive(True)
    def restore_mask(self):
        if self._mask_backup:
            self.mask = self._mask_backup.pop()
        if not self._mask_backup:
            self.undobutton.set_sensitive(False)
    def zap_backups(self):
        self._mask_backup = []
        self.undobutton.set_sensitive(False)
    def addline(self, val):
        if isinstance(val, list):
            for v in val:
                self.addline(v)
        else:
            self._extra_lines.append(val)
    def get_maskingmode(self):
        return self.maskingmode.get_active_text().lower()
    def on_pixel_hunt(self):
        with GraphToolbarVisibility(self.graphtoolbar, self.toolbar):
            self.statusline.setup('Click pixels to change masking. If finished, press --->', 'Finished')
            self.statusline.reset_counters()
            self._mouseclick_last = []
            self._mouseclick_mode = 'Pixelhunt'
            while not self.statusline.nbuttonclicks(0):
                gtk.main_iteration()
            self._mouseclick_mode = None
        self.statusline.setup(None)
        self.update_graph()

    def on_button_clicked(self, button, whattodo=None):
        if whattodo is None:
            return True
        if whattodo == 'Undo':
            self.restore_mask()
        elif whattodo in ['Rectangle', 'Circle', 'Polygon']:
            with GraphToolbarVisibility(self.graphtoolbar, self.toolbar):
                if whattodo == 'Rectangle':
                    self.statusline.setup('Click two opposite corners of the rectangle')
                    self._mouseclicks = []
                    self._mouseclick_mode = 'POINTS'
                    while len(self._mouseclicks) < 2:
                        gtk.main_iteration()
                    self._mouseclick_mode = None
                    self.backup_mask()
                    self.mask.edit_rectangle(self._mouseclicks[0][1], self._mouseclicks[0][0],
                                             self._mouseclicks[1][1], self._mouseclicks[1][0],
                                             whattodo=self.get_maskingmode())
                    self.update_graph(justthemask=True)
                elif whattodo == 'Circle':
                    self.statusline.setup('Click the center of the circle')
                    self._mouseclicks = []
                    self._mouseclick_mode = 'POINTS'
                    while len(self._mouseclicks) < 1:
                        gtk.main_iteration()
                    self.statusline.setup('Click a peripheric point of the circle')
                    while len(self._mouseclicks) < 2:
                        gtk.main_iteration()
                    self._mouseclick_mode = None
                    self.backup_mask()
                    self.mask.edit_circle(self._mouseclicks[0][1], self._mouseclicks[0][0],
                                          np.sqrt((self._mouseclicks[1][0] - self._mouseclicks[0][0]) ** 2 +
                                                  (self._mouseclicks[1][1] - self._mouseclicks[0][1]) ** 2),
                                          whattodo=self.get_maskingmode())
                    self.update_graph(justthemask=True)
                elif whattodo == 'Polygon':
                    self.statusline.setup('Select corners of the polygon. If finished, press --->', 'Finished')
                    self.statusline.reset_counters()
                    self._mouseclicks = []
                    self._mouseclick_mode = 'LINES'
                    while not self.statusline.nbuttonclicks(0):
                        gtk.main_iteration()
                    self._mouseclick_mode = None
                    if len(self._mouseclicks) > 2:
                        row = [t[1] for t in self._mouseclicks]
                        col = [t[0] for t in self._mouseclicks]
                        self.backup_mask()
                        self.mask.edit_polygon(row, col, self.get_maskingmode())
                        self.update_graph(justthemask=True)
                    else:
                        self.update_graph(purifyonly=True)
            self.statusline.setup(None)
        elif whattodo == 'Histogram_masked':
            self.selecthisto(data=self.matrix[np.array(self.mask, 'bool')])
        elif whattodo == 'Histogram_all':
            self.selecthisto()
        elif whattodo == 'Invert':
            self.backup_mask()
            self.mask.invert()
            self.update_graph(justthemask=True)
        elif whattodo == 'Mask_nonfinite':
            self.backup_mask()
            self.mask.edit_nonfinite(self.matrix, 'mask')
            self.update_graph(justthemask=True)
        elif whattodo == 'Mask_nonpositive':
            self.backup_mask()
            self.mask.edit_nonpositive(self.matrix, 'mask')
            self.update_graph(justthemask=True)
        else:
            raise NotImplementedError('Masking method %s not implemented!' % whattodo)
        return True
    def get_maskid(self):
        return self.mask.maskid
    def set_maskid(self, value):
        self.mask.maskid = value
    maskid = property(get_maskid, set_maskid)
    def increment_maskid(self):
        m = re.search('_mod(\d+)$', self.maskid)
        if m is not None:
            self.maskid = self.maskid[:-len(m.group(1))] + str(int(m.group(1)) + 1)
        else:
            self.maskid = self.maskid + '_mod1'
        return self.maskid
    def get_mask(self):
        return self.exposure.mask
    def set_mask(self, value):
        self.exposure.set_mask(value)
    mask = property(get_mask, set_mask)
    def get_matrix(self):
        return self.exposure.Intensity
    matrix = property(get_matrix)
    def get_exposure(self):
        return self._exposure
    exposure = property(get_exposure)
    def update_graph(self, purifyonly=False, redraw=False, justthemask=False):
        while self._extra_lines:
            try:
                self._extra_lines.pop().remove()
            except ValueError:
                pass
        if purifyonly:
            return True
        if justthemask:
            self.fig.draw_image(what='plotmask')
            return True
        if redraw:
            self.fig.draw_image(what='uberforce')
        else:
            self.fig.draw_image(what='force')
        return True
    def newmask(self, widget=None): #IGNORE:W0613
        self.mask = np.ones_like(self._matrix.Intensity)
        self.update_graph(True)
        return True
    def savemask(self, widget=None): #IGNORE:W0613
        fcd = gtk.FileChooserDialog('Select file to save mask...', self,
                                  gtk.FILE_CHOOSER_ACTION_SAVE,
                                  (gtk.STOCK_OK, gtk.RESPONSE_OK,
                                   gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        fcd.set_current_folder(os.getcwd())
        fcd.set_destroy_with_parent(True)
        fcd.set_modal(True)
        fcd.set_do_overwrite_confirmation(True)
        ff = gtk.FileFilter(); ff.set_name('All files'); ff.add_pattern('*')
        fcd.add_filter(ff)
        ff = gtk.FileFilter(); ff.set_name('Matlab(R) mask matrices'); ff.add_pattern('*.mat')
        fcd.add_filter(ff)
        ff = gtk.FileFilter(); ff.set_name('Numpy mask matrices'); ff.add_pattern('*.npy'); ff.add_pattern('*.npz')
        fcd.add_filter(ff)
        fcd.set_filter(ff)
        fcd.set_current_name(self.maskid + ".mat")
        if fcd.run() == gtk.RESPONSE_OK:
            self.increment_maskid()
            filename = fcd.get_filename()
            # guess the mask file format
            maskname = os.path.splitext(os.path.split(filename)[1])[0].lower()
            if not maskname.startswith('mask'):
                maskname = 'mask' + maskname
            fdict = {maskname:np.array(self.mask)}
            if filename.lower().endswith('.mat'):
                scipy.io.savemat(filename, fdict)
            elif filename.lower().endswith('.npz'):
                np.savez_compressed(filename, **fdict) #IGNORE:W0142
            elif filename.lower().endswith('.npy'):
                np.save(filename, np.array(self.mask))
            else:
                np.savez_compressed(filename + '.npz', **fdict) #IGNORE:W0142
        os.chdir(fcd.get_current_folder())
        fcd.destroy()
    def loadmask(self, widget=None): #IGNORE:W0613
        fcd = gtk.FileChooserDialog('Select file to load mask...', self,
                                  gtk.FILE_CHOOSER_ACTION_OPEN,
                                  (gtk.STOCK_OK, gtk.RESPONSE_OK,
                                   gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        fcd.set_current_folder(os.getcwd())
        fcd.set_destroy_with_parent(True)
        fcd.set_modal(True)
        ff = gtk.FileFilter(); ff.set_name('All files'); ff.add_pattern('*')
        fcd.add_filter(ff)
        ff = gtk.FileFilter(); ff.set_name('Matlab(R) mask matrices'); ff.add_pattern('*.mat')
        fcd.add_filter(ff)
        fcd.set_filter(ff)
        if fcd.run() == gtk.RESPONSE_OK:
            filename = fcd.get_filename()
            try:
                mask1 = readmask(filename).astype(np.bool8)
            except Exception:   #IGNORE:W0703
                self.statusline.setup('Invalid mask file.')
            else:
                if mask1.shape != self.mask.shape:
                    self.statusline.setup('Incompatible mask shape.')
                else:
                    self.mask = mask1
                    if re.match('mask([.]*).mat', os.path.split(filename)[-1]):
                        self.maskid = os.path.split(filename)[-1][:-4]
        os.chdir(fcd.get_current_folder())
        fcd.destroy()
        self.update_graph(True)
        return True
    def _on_matplotlib_mouseclick(self, event):
        if self._mouseclick_mode is None:
            return False
        if event.button == 1:
            if self._mouseclick_mode.upper() == 'POINTS':
                ax = self.fig.gca().axis()
                self.addline(self.fig.gca().plot(event.xdata, event.ydata, 'o', c='white', markersize=7))
                self.fig.gca().axis(ax)
                self.fig.canvas.draw()
            if self._mouseclick_mode.upper() == 'LINES':
                ax = self.fig.gca().axis()
                self.addline(self.fig.gca().plot(event.xdata, event.ydata, 'o', c='white', markersize=7))
                if self._mouseclicks:
                    self.addline(self.fig.gca().plot([self._mouseclicks[-1][0], event.xdata],
                                        [self._mouseclicks[-1][1], event.ydata],
                                        c='white'))
                self.fig.gca().axis(ax)
                self.fig.canvas.draw()
            if self._mouseclick_mode.upper() == 'PIXELHUNT':
                if (event.xdata >= 0 and event.xdata < self.mask.shape[1] and
                    event.ydata >= 0 and event.ydata < self.mask.shape[0]):
                    self.mask[round(event.ydata), round(event.xdata)] ^= 1
                    self.update_graph(justthemask=True)
            self._mouseclicks.append((event.xdata, event.ydata))
    def selecthisto(self, data=None):  #IGNORE:W0613
        if data is None:
            data = self.matrix
        self.toolbar.set_sensitive(False)
        hs = HistogramSelector(data, 'Zoom to desired range...',
                               parent=self.get_toplevel(),
                               flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                               buttons=(gtk.STOCK_OK, gtk.RESPONSE_OK,
                                        gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        hs.nbins = max(min(data.max() - data.min(), 100), 1000)
        if hs.run() == gtk.RESPONSE_OK:
            xlim = hs.get_xlimits()
            self.backup_mask()
            self.mask.edit_function(self.matrix, lambda a:((a <= max(xlim)) & (a >= min(xlim))), whattodo=self.get_maskingmode())
            self.update_graph(justthemask=True)
        hs.destroy()
        return True
    def run(self, *args, **kwargs):
        retval = gtk.Dialog.run(self, *args, **kwargs)
        if retval == gtk.RESPONSE_OK:
            self.increment_maskid()
        return retval

def makemask(matrix=None, mask0=None):
    mm = MaskMaker(matrix=matrix, mask=mask0)
    resp = mm.run()
    if resp == gtk.RESPONSE_OK:
        mask0 = mm.get_mask()
    mm.destroy()
    return mask0
