'''
Created on Feb 14, 2012

@author: andris
'''

from .plot2dsasimage import PlotSASImage

from gi.repository import Gtk
import re
import matplotlib
import pkg_resources
from gi.repository import GObject
from gi.repository import GdkPixbuf

import uuid
import numpy as np
import matplotlib.nxutils
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg
from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3
from matplotlib.figure import Figure
import os
import scipy.io

from sastool.classes import SASExposure, SASMask
from sastool import misc

__all__ = ['MaskMaker', 'makemask']

iconfactory = Gtk.IconFactory()
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
    iconset = Gtk.IconSet(GdkPixbuf.Pixbuf.new_from_file(pkg_resources.resource_filename('sasgui', 'resource/icons/%s' % f)))
    # Gtk.stock_add([('sasgui_%s' % basename, n, 0, 0, 'C')])
    iconfactory.add('sasgui_%s' % basename, iconset)
iconfactory.add_default()

class HistogramSelector(Gtk.Dialog):
    __gtype_name__ = 'SASGUI_HistogramSelector'
    def __init__(self, data, *args, **kwargs):
        Gtk.Dialog.__init__(self, *args, **kwargs)
        self.set_default_response(Gtk.ResponseType.CANCEL)
        self._data = data
        vbox = self.get_content_area()
        hbox = Gtk.HBox()
        vbox.pack_start(hbox, False, True, 0)
        l = Gtk.Label(label='Number of histogram bins:')
        l.set_alignment(0, 0.5)
        hbox.pack_start(l, False, True, 0)
        self.nbins_spin = Gtk.SpinButton()
        hbox.pack_start(self.nbins_spin, True, True, 0)
        self.nbins_spin.set_range(1, 1e100)
        self.nbins_spin.set_increments(1, 10)
        self.nbins_spin.set_digits(0)
        self.nbins_spin.set_numeric(True)
        # self.nbins_spin.connect('changed', self.on_nbins_changed)
        b = Gtk.Button(stock=Gtk.STOCK_APPLY)
        hbox.pack_start(b, False, True, 0)
        b.connect('clicked', self.on_nbins_changed)
        self.fig = Figure((640 / 72., 480 / 72.), 72)
        self.canvas = FigureCanvasGTK3Agg(self.fig)
        self.canvas.set_size_request(300, 200)
        vbox.pack_start(self.canvas, True, True, 0)
        self.figure_toolbar = NavigationToolbar2GTK3(self.canvas, self)
        vbox.pack_start(self.figure_toolbar, False, True, 0)
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
    def redraw(self):
        self.fig.gca().cla()
        self.fig.gca().hist(self.data.flatten(), self.nbins)
        self.fig.canvas.draw()
        return False
    def on_nbins_changed(self, widget):
        GObject.idle_add(self.redraw)
        return True
    def get_xlimits(self):
        return self.fig.gca().axis()[0:2]
    def gca(self):
        return self.fig.gca()


class MaskMaker(Gtk.Dialog):
    __gtype_name__ = 'SASGUI_MaskMaker'
    _mouseclick_mode = None  # Allowed: 'Points', 'Lines', 'PixelHunt' and None
    _mouseclicks = []
    _selection = None
    _maskimage = None
    _extra_lines = []
    _mask_backup = []
    _graphtoolbarvisibility = None
    def __init__(self, title='Make mask...', parent=None,
                 flags=Gtk.DialogFlags.DESTROY_WITH_PARENT,
                 buttons=(Gtk.STOCK_OK, Gtk.ResponseType.OK, Gtk.STOCK_CANCEL,
                          Gtk.ResponseType.CANCEL),
                 matrix=None, mask=None, maskid=None):
        if matrix is None:
            raise ValueError("Argument 'matrix' is required!")
        if not isinstance(matrix, SASExposure):
            matrix = SASExposure(matrix)
        if mask is not None:
            matrix.set_mask(mask)
        elif matrix.mask is None:
            matrix.set_mask()
        if maskid is not None:
            self.maskid = maskid
        Gtk.Dialog.__init__(self, title, parent, flags, buttons)
        self._exposure = matrix


        self.set_default_response(Gtk.ResponseType.CANCEL)

        clearbutton = Gtk.Button(stock=Gtk.STOCK_NEW)
        self.get_action_area().pack_end(clearbutton, True, True, 0)
        clearbutton.connect('clicked', self.newmask)
        clearbutton.show()
        savebutton = Gtk.Button(stock=Gtk.STOCK_SAVE_AS)
        self.get_action_area().pack_end(savebutton, True, True, 0)
        savebutton.connect('clicked', self.savemask)
        savebutton.show()
        loadbutton = Gtk.Button(stock=Gtk.STOCK_OPEN)
        self.get_action_area().pack_end(loadbutton, True, True, 0)
        loadbutton.connect('clicked', self.loadmask)
        loadbutton.show()

        vbox = self.get_content_area()
        self.toolbar = Gtk.Toolbar()
        self.toolbar.set_style(Gtk.ToolbarStyle.ICONS)
        vbox.pack_start(self.toolbar, False, True, 0)


        self.fig = PlotSASImage()
        self.fig.exposure = self.exposure
        self.fig.set_size_request(640, 480)
        vbox.pack_start(self.fig, True, True, 0)
        self.graphtoolbar = self.fig.figure_toolbar
        self.fig.canvas.mpl_connect('button_press_event', self._on_matplotlib_mouseclick)

        # self.pixelhunt_button = Gtk.ToggleToolButton(icon_widget=Gtk.Image.new_from_icon_name('sasgui_pixelhunt', self.toolbar.get_icon_size()), label=iconlabels['sasgui_pixelhunt'])
        self.pixelhunt_button = Gtk.ToggleToolButton(stock_id='sasgui_pixelhunt')
        self.toolbar.insert(self.pixelhunt_button, -1)
        self.pixelhunt_button.connect('toggled', self.on_button_clicked, 'Pixelhunt')
        self.pixelhunt_button.set_tooltip_text('Pixel hunting mode. Mask/unmask pixels one-by-one.')

        self.maskingmode = Gtk.ComboBoxText()
        self.maskingmode.append_text('mask')
        self.maskingmode.append_text('unmask')
        self.maskingmode.append_text('invert')
        self.maskingmode.set_tooltip_text('Masking mode. This determines what happens to the mask if you select a region.')
        self.maskingmode.set_active(0)
        ti = Gtk.ToolItem()
        ti.add(self.maskingmode)
        self.toolbar.insert(ti, -1)

        self.polygon_button = Gtk.ToggleToolButton(stock_id='sasgui_polygon')
        self.toolbar.insert(self.polygon_button, -1)
        self.polygon_button.connect('toggled', self.on_button_clicked, 'Select a polygon')
        self.polygon_button.set_tooltip_text('Select a polygon by its corners. Click this button once again to finish.')
        for name, stock in [('Select a rectangle by its two opposite corners', 'sasgui_rectangle'),
                           ('Select a circle by its center and a peripheral point', 'sasgui_circle'),
                           ('Select pixels by an intensity histogram', 'sasgui_histogram'),
                           ('Select pixels by an intensity histogram: disregard already masked pixels', 'sasgui_histogram_masked'),
                           ('Invert mask', 'sasgui_invert_mask'),
                           ('Select nonfinite pixels', 'sasgui_infandnan'),
                           ('Select nonpositive pixels', 'sasgui_nonpositive')]:
            b = Gtk.ToolButton(stock_id=stock)
            self.toolbar.insert(b, -1)
            b.connect('clicked', self.on_button_clicked, name)
            b.set_tooltip_text(name)
        self.undobutton = Gtk.ToolButton(Gtk.STOCK_UNDO)
        self.toolbar.insert(self.undobutton, -1)
        self.undobutton.connect('clicked', self.on_button_clicked, 'Undo')
        self.undobutton.set_sensitive(False)
        
        self.get_content_area().show_all()
        self.update_graph()
    def backup_mask(self):
        self._mask_backup.append(SASMask(self.mask))
        self.undobutton.set_sensitive(True)
    def restore_mask(self):
        if self._mask_backup:
            self.mask = self._mask_backup.pop()
        if not self._mask_backup:
            self.undobutton.set_sensitive(False)
        self.update_graph(justthemask=True)
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
    def graphtoolbar_set_sensitive(self, value):
        if (self._graphtoolbarvisibility is None) and value:
            # trying to set the graph toolbar sensitive when it is
            return False
        if (self._graphtoolbarvisibility is not None) and not value:
            # trying to set the graph toolbar insensitive when it is
            return False
        if not value:
            self._graphtoolbarvisibility = {}
            if self.graphtoolbar.mode.startswith('zoom'):
                self.graphtoolbar.zoom()
                self._graphtoolbarvisibility['zooming'] = True
            else:
                self._graphtoolbarvisibility['zooming'] = False
            if self.graphtoolbar.mode.startswith('pan'):
                self.graphtoolbar.pan()
                self._graphtoolbarvisibility['panning'] = True
            else:
                self._graphtoolbarvisibility['panning'] = False
            self.graphtoolbar.set_sensitive(False)
        else:
            if self._graphtoolbarvisibility['zooming']:
                self.graphtoolbar.zoom()
            if self._graphtoolbarvisibility['panning']:
                self.graphtoolbar.pan()
            self._graphtoolbarvisibility = None
            self.graphtoolbar.set_sensitive(True)
        return True
    def on_button_clicked(self, button, whattodo=None):
        if whattodo is None:
            return True
        if whattodo == 'Undo':
            self.restore_mask()
        elif whattodo.find('Pixel') >= 0:
            if self._mouseclick_mode == 'Pixelhunt':
                # we are in pixel hunt mode, turn it off
                self.graphtoolbar_set_sensitive(True)
                self.toolbar.foreach(lambda x, sen:x.set_sensitive(sen), True)
                self._mouseclick_mode = None
            else:
                # we are not pixel hunting, turn it on
                self._mouseclick_mode = 'Pixelhunt'
                self._mouseclicks = []
                self.graphtoolbar_set_sensitive(False)
                self.toolbar.foreach(lambda x, sen:x.set_sensitive(sen), False)
                self.pixelhunt_button.set_sensitive(True)
                self.backup_mask()
            return True
        elif whattodo.find('polygon') >= 0:
            if self._mouseclick_mode == 'LINES':
                # polygon-ing, stop it.
                self.toolbar.foreach(lambda x, sen:x.set_sensitive(sen), True)
                self._mouseclick_mode = None
                if len(self._mouseclicks) > 2:
                    row = [t[1] for t in self._mouseclicks]
                    col = [t[0] for t in self._mouseclicks]
                    self.backup_mask()
                    self.mask.edit_polygon(row, col, self.get_maskingmode())
                    self.update_graph(justthemask=True)
                    self._mouseclicks = []
                else:
                    self.update_graph(purifyonly=True)
            else:
                # start selecting polygons.
                self._mouseclicks = []
                self._mouseclick_mode = 'LINES'
                self.toolbar.foreach(lambda x, sen:x.set_sensitive(sen), False)
                self.polygon_button.set_sensitive(True)
        elif any(whattodo.find(x) >= 0 for x in ['rectangle', 'circle']):
            try:
                self.graphtoolbar_set_sensitive(False)
                if whattodo.find('rectangle') >= 0:
                    self._mouseclicks = []
                    self._mouseclick_mode = 'POINTS'
                    while len(self._mouseclicks) < 2:
                        Gtk.main_iteration()
                    self._mouseclick_mode = None
                    self.backup_mask()
                    self.mask.edit_rectangle(self._mouseclicks[0][1], self._mouseclicks[0][0],
                                             self._mouseclicks[1][1], self._mouseclicks[1][0],
                                             whattodo=self.get_maskingmode())
                    self.update_graph(justthemask=True)
                elif whattodo.find('circle') >= 0:
                    self._mouseclicks = []
                    self._mouseclick_mode = 'POINTS'
                    while len(self._mouseclicks) < 2:
                        Gtk.main_iteration()
                    self._mouseclick_mode = None
                    self.backup_mask()
                    self.mask.edit_circle(self._mouseclicks[0][1], self._mouseclicks[0][0],
                                          np.sqrt((self._mouseclicks[1][0] - self._mouseclicks[0][0]) ** 2 + 
                                                  (self._mouseclicks[1][1] - self._mouseclicks[0][1]) ** 2),
                                          whattodo=self.get_maskingmode())
                    self.update_graph(justthemask=True)
            finally:
                self.graphtoolbar_set_sensitive(True)
        elif whattodo.find('histogram') >= 0:
            if whattodo.find('masked') >= 0:
                self.selecthisto(data=self.matrix[np.array(self.mask, 'bool')])
            else:
                self.selecthisto()
        elif whattodo.find('Invert') >= 0:
            self.backup_mask()
            self.mask.invert()
            self.update_graph(justthemask=True)
        elif whattodo.find('nonfinite') >= 0:
            self.backup_mask()
            self.mask.edit_nonfinite(self.matrix, self.get_maskingmode())
            self.update_graph(justthemask=True)
        elif whattodo.find('nonpositive') >= 0:
            self.backup_mask()
            self.mask.edit_nonpositive(self.matrix, self.get_maskingmode())
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
    def newmask(self, widget=None):  # IGNORE:W0613
        self.mask = np.ones_like(self.matrix)
        self.update_graph(justthemask=True)
        self.zap_backups()
        return True
    def savemask(self, widget=None):  # IGNORE:W0613
        fcd = Gtk.FileChooserDialog('Select file to save mask...', self,
                                  Gtk.FileChooserAction.SAVE,
                                  (Gtk.STOCK_OK, Gtk.ResponseType.OK,
                                   Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        fcd.set_current_folder(os.getcwd())
        fcd.set_destroy_with_parent(True)
        fcd.set_modal(True)
        fcd.set_do_overwrite_confirmation(True)
        ff = Gtk.FileFilter(); ff.set_name('All files'); ff.add_pattern('*')
        fcd.add_filter(ff)
        ff = Gtk.FileFilter(); ff.set_name('Numpy mask matrices'); ff.add_pattern('*.npy'); ff.add_pattern('*.npz')
        fcd.add_filter(ff)
        ff = Gtk.FileFilter(); ff.set_name('BerSANS mask matrices'); ff.add_pattern('*.sma')
        fcd.add_filter(ff)
        ff = Gtk.FileFilter(); ff.set_name('Matlab(R) mask matrices'); ff.add_pattern('*.mat')
        fcd.add_filter(ff)
        ff = Gtk.FileFilter(); ff.set_name('All mask files'); ff.add_pattern('*.sma');
        ff.add_pattern('*.mat'); ff.add_pattern('*.npy'); ff.add_pattern('*.npz')
        fcd.add_filter(ff)
        fcd.set_filter(ff)
        fcd.set_current_name(self.maskid + ".mat")
        if fcd.run() == Gtk.ResponseType.OK:
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
                np.savez_compressed(filename, **fdict)  # IGNORE:W0142
            elif filename.lower().endswith('.npy'):
                np.save(filename, np.array(self.mask))
            elif filename.lower().endswith('.sma'):
                self.mask.write_to_sma(filename)
            else:
                np.savez_compressed(filename + '.npz', **fdict)  # IGNORE:W0142
        # os.chdir(fcd.get_current_folder())
        fcd.destroy()
    def loadmask(self, widget=None):  # IGNORE:W0613
        fcd = Gtk.FileChooserDialog('Select file to load mask...', self,
                                  Gtk.FileChooserAction.OPEN,
                                  (Gtk.STOCK_OK, Gtk.ResponseType.OK,
                                   Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        fcd.set_current_folder(os.getcwd())
        fcd.set_destroy_with_parent(True)
        fcd.set_modal(True)
        ff = Gtk.FileFilter(); ff.set_name('All files'); ff.add_pattern('*')
        fcd.add_filter(ff)
        ff = Gtk.FileFilter(); ff.set_name('Numpy mask matrices'); ff.add_pattern('*.npy'); ff.add_pattern('*.npz')
        fcd.add_filter(ff)
        ff = Gtk.FileFilter(); ff.set_name('BerSANS mask matrices'); ff.add_pattern('*.sma')
        fcd.add_filter(ff)
        ff = Gtk.FileFilter(); ff.set_name('Matlab(R) mask matrices'); ff.add_pattern('*.mat')
        fcd.add_filter(ff)
        ff = Gtk.FileFilter(); ff.set_name('All mask files'); ff.add_pattern('*.sma')
        ff.add_pattern('*.mat'); ff.add_pattern('*.npy'); ff.add_pattern('*.npz')
        fcd.add_filter(ff)
        fcd.set_filter(ff)
        if fcd.run() == Gtk.ResponseType.OK:
            fcd.hide()
            filename = fcd.get_filename()
            try:
                mask1 = SASMask(filename)
            except Exception:  # IGNORE:W0703
                md = Gtk.MessageDialog(self, Gtk.DialogFlags.DESTROY_WITH_PARENT | Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                                     Gtk.ButtonsType.OK, 'Invalid mask file.')
                md.run()
                md.destroy()
            else:
                if mask1.shape != self.mask.shape:
                    md = Gtk.MessageDialog(self, Gtk.DialogFlags.DESTROY_WITH_PARENT | Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                                         Gtk.ButtonsType.OK, 'Incompatible shape for mask: %d x %d (instead of %d x %d)' % (mask1.shape + self.mask.shape))
                    md.run()
                    md.destroy()
                else:
                    self.mask = mask1
                    if re.match('mask([.]*).mat', os.path.split(filename)[-1]):
                        self.maskid = os.path.split(filename)[-1][:-4]
                    self.zap_backups()
        os.chdir(fcd.get_current_folder())
        fcd.destroy()
        self.update_graph(justthemask=True)
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
                    self.mask.mask[round(event.ydata), round(event.xdata)] ^= 1
                    self.update_graph(justthemask=True)
            self._mouseclicks.append((event.xdata, event.ydata))
    def selecthisto(self, data=None):  # IGNORE:W0613
        if data is None:
            data = self.matrix
        hs = HistogramSelector(data, 'Zoom to desired range...',
                               parent=self.get_toplevel(),
                               flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                               buttons=(Gtk.STOCK_OK, Gtk.ResponseType.OK,
                                        Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        hs.nbins = 100
        if hs.run() == Gtk.ResponseType.OK:
            xlim = hs.get_xlimits()
            self.backup_mask()
            self.mask.edit_function(self.matrix, lambda a:((a <= max(xlim)) & (a >= min(xlim))), whattodo=self.get_maskingmode())
            self.update_graph(justthemask=True)
        hs.destroy()
        return True
    def run(self, *args, **kwargs):
        retval = Gtk.Dialog.run(self, *args, **kwargs)
        if retval == Gtk.ResponseType.OK:
            self.increment_maskid()
        return retval

def makemask(matrix, mask0=None):
    """Open a mask editing dialog.

    Inputs:
    -------
        ``matrix``
            either a ``np.ndarray`` or a ``SASExposure`` instance. This is used
            as a background for the mask.
        ``mask0``
            the initial mask. Can be ``None``, an instance of ``SASMask`` or a
            ``np.ndarray``. In the first case if ``matrix`` is a ``SASExposure``,
            its mask field is used. In the two latter cases they override the
            mask defined in ``matrix`` (if it is a ``SASExposure``).

    Output:
    -------
        None
            if `Cancel` was selected from the dialog
        a `SASMask` instance
            if `OK` was selected from the dialog
    """
    mm = MaskMaker(matrix=matrix, mask=mask0)
    resp = mm.run()
    if resp == Gtk.ResponseType.OK:
        mask0 = mm.get_mask()
    mm.destroy()
    return mask0
