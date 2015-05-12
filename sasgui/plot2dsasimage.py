from gi.repository import Gtk
from gi.repository import GObject
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg
from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3
import matplotlib
import numpy as np
import sastool
import qrcode
import scipy
import time
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

default_palette = 'jet'
default_palette_reversed = False

__all__ = ['PlotSASImage', 'PlotSASImageWindow']


class PlotProperties(Gtk.Box):
    __gsignals__ = {'changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
                    }

    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        g = Gtk.Grid()
        self.pack_start(g, False, False, 0)
        l = Gtk.Label(label='Palette:')
        g.attach(l, 0, 0, 1, 1)
        self._palette_combo = Gtk.ComboBoxText()
        self._palette_combo.set_hexpand(True)
        g.attach(self._palette_combo, 1, 0, 1, 1)
        i = 0
        for m in dir(matplotlib.cm):
            if eval('isinstance(matplotlib.cm.%s,matplotlib.colors.Colormap)' % m) and not m.endswith('_r'):
                self._palette_combo.append_text(m)
                if default_palette == m:
                    self._palette_combo.set_active(i)
                i += 1
        if self._palette_combo.get_active_text() is None:
            self._palette_combo.set_active(0)

        self._palette_combo.connect(
            'changed', lambda combo: self.emit('changed'))

        l = Gtk.Label(label='Color scale:')
        g.attach(l, 0, 1, 1, 1)
        self._colorscale_combo = Gtk.ComboBoxText()
        self._colorscale_combo.set_hexpand(True)
        self._colorscale_combo.append_text('linear')
        self._colorscale_combo.append_text('log10')
        self._colorscale_combo.set_active(0)
        g.attach(self._colorscale_combo, 1, 1, 1, 1)
        self._colorscale_combo.connect(
            'changed', lambda combo: self.emit('changed'))

        l = Gtk.Label(label='Abscissa:')
        g.attach(l, 0, 2, 1, 1)
        self._abscissa_combo = Gtk.ComboBoxText()
        self._abscissa_combo.set_hexpand(True)
        self._abscissa_combo.append_text('pixel')
        self._abscissa_combo.append_text('q')
        self._abscissa_combo.set_active(0)
        g.attach(self._abscissa_combo, 1, 2, 1, 1)
        self._abscissa_combo.connect(
            'changed', lambda combo: self.emit('changed'))

        self._lowclip_check = Gtk.CheckButton(label='Lower clip:')
        self._lowclip_check.set_active(False)
        g.attach(self._lowclip_check, 2, 0, 1, 1)
        self._lowclip_entry = Gtk.Entry()
        self._lowclip_entry.set_hexpand(True)
        self._lowclip_entry.set_sensitive(False)
        g.attach(self._lowclip_entry, 3, 0, 1, 1)
        self._lowclip_check.connect('toggled', lambda cb, entry: entry.set_sensitive(
            cb.get_active()), self._lowclip_entry)

        self._upclip_check = Gtk.CheckButton(label='Upper clip:')
        self._upclip_check.set_active(False)
        g.attach(self._upclip_check, 2, 1, 1, 1)
        self._upclip_entry = Gtk.Entry()
        self._upclip_entry.set_hexpand(True)
        self._upclip_entry.set_sensitive(False)
        g.attach(self._upclip_entry, 3, 1, 1, 1)
        self._upclip_check.connect('toggled', lambda cb, entry: entry.set_sensitive(
            cb.get_active()), self._upclip_entry)

        hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.pack_start(hb, False, False, 0)

        self._palettereversed_check = Gtk.CheckButton(label='Reverse palette')
        hb.pack_start(self._palettereversed_check, False, False, 0)
        self._palettereversed_check.connect(
            'toggled', lambda cb: self.emit('changed'))

        self._plotmask_check = Gtk.CheckButton(label='Mask')
        self._plotmask_check.set_active(True)
        hb.pack_start(self._plotmask_check, False, False, 0)
        self._plotmask_check.connect(
            'toggled', lambda cb: self.emit('changed'))

        self._crosshair_check = Gtk.CheckButton(label='Crosshair')
        self._crosshair_check.set_active(True)
        hb.pack_start(self._crosshair_check, False, False, 0)
        self._crosshair_check.connect(
            'toggled', lambda cb: self.emit('changed'))

        self._colorbar_check = Gtk.CheckButton(label='Color bar')
        self._colorbar_check.set_active(True)
        hb.pack_start(self._colorbar_check, False, False, 0)
        self._colorbar_check.connect(
            'toggled', lambda cb: self.emit('changed'))

        self._keepzoom_check = Gtk.CheckButton(label='Freeze zoom')
        hb.pack_start(self._keepzoom_check, False, False, 0)
        self._keepzoom_check.connect(
            'toggled', lambda cb: self.emit('changed'))

    def get_show_colorbar(self):
        return self._get_show_general(self._colorbar_check)

    def get_show_mask(self):
        return self._get_show_general(self._plotmask_check)

    def get_palette(self):
        return eval('matplotlib.cm.%s' % (self._palette_combo.get_active_text() + ['', '_r'][self._palettereversed_check.get_active()]))

    def get_abscissa(self):
        return self._abscissa_combo.get_active_text()

    def get_show_crosshair(self):
        return self._get_show_general(self._crosshair_check)

    def get_colorscale(self):
        return self._colorscale_combo.get_active_text()

    def get_keep_zoom(self):
        return self._get_show_general(self._keepzoom_check)

    def get_lowclip(self):
        if self._lowclip_entry.get_sensitive():
            return float(self._lowclip_entry.get_text())
        else:
            return None

    def get_upclip(self):
        if self._upclip_entry.get_sensitive():
            return float(self._upclip_entry.get_text())
        else:
            return None

    def _get_show_general(self, checkbutton):
        return checkbutton.get_sensitive() and checkbutton.get_active()

    def update_from_exposure(self, exposure):
        if isinstance(exposure, sastool.classes.SASExposure):
            self._lowclip_entry.set_text(str(exposure.Intensity.min()))
            self._upclip_entry.set_text(str(exposure.Intensity.max()))
            self._plotmask_check.set_sensitive(exposure.mask is not None)
            self._crosshair_check.set_sensitive(
                all([x in exposure.header for x in ['BeamPosX', 'BeamPosY']]))
            if exposure.check_for_q(False):
                self._abscissa_combo.set_active(0)
                self._abscissa_combo.set_sensitive(False)
            else:
                self._abscissa_combo.set_sensitive(True)
        else:
            self._lowclip_entry.set_text(str(exposure.min()))
            self._upclip_entry.set_text(str(exposure.max()))
            self._plotmask_check.set_sensitive(False)
            self._crosshair_check.set_sensitive(False)
            self._abscissa_combo.set_sensitive(False)


class PlotSASImage(Gtk.Box):
    __gtype_name__ = 'SASGUI_PlotSASImage2'
    __gsignals__ = {'notify': 'override',
                    'exposure-changed': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
                    'destroy': 'override'}
    show_logo = GObject.Property(type=bool, default=True)
    logo = GObject.Property(type=str, default='')
    show_qr = GObject.Property(type=bool, default=True)
    mask_alpha = GObject.Property(
        type=float, default=0.6, minimum=0, maximum=1)

    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        expander = Gtk.Expander(label='Plot properties')
        self.pack_start(expander, False, False, 0)
        self._plot_properties = PlotProperties()
        expander.add(self._plot_properties)
        self._plot_properties.connect(
            'changed', self.on_plot_properties_changed)

        self._fig = Figure(figsize=(3.75, 2.5), dpi=80)
        self._canvas = FigureCanvasGTK3Agg(self._fig)
        self.pack_start(self._canvas, True, True, 0)
        self._figure_toolbar = NavigationToolbar2GTK3(self._canvas, None)
        self.pack_start(self._figure_toolbar, False, True, 0)
        tbutton = Gtk.ToolButton(Gtk.STOCK_CLEAR)
        tbutton.connect('clicked', lambda tb: self.clear())
        self._figure_toolbar.insert(tbutton, 0)
        tbutton = Gtk.ToolButton(Gtk.STOCK_REFRESH)
        tbutton.connect('clicked', lambda tb: self.redraw_image())
        self._figure_toolbar.insert(tbutton, 0)
        self._stattbutton = Gtk.ToggleToolButton(stock_id='sasgui_piechart')
        self._stattbutton.connect('toggled', self._on_statistics_toggled)
        self._figure_toolbar.insert(self._stattbutton, 0)
        y, x = np.mgrid[-512:512, -512:512] / 1024. * 20
        testdata = np.sin(x) * np.sin(y) + (x + y) / 10
        self._exposure = testdata
        self._plot_properties.update_from_exposure(testdata)
        self._imgaxis = self._fig.add_subplot(1, 1, 1)
        self._imgaxis.set_axis_bgcolor('black')
        self._img = self._imgaxis.imshow(testdata)
        self._maskimg = None
        self._colorbaraxis = self._fig.colorbar(self._img, ax=self._imgaxis).ax
        if not self._plot_properties.get_show_colorbar():
            self._colorbaraxis.set_visible(False)
        self._qraxis = self._fig.add_axes([0, 0, 0.1, 0.1], anchor='SW')
        self._qraxis.set_axis_off()
        self._qraxis.set_visible(False)
        self._logoaxis = self._fig.add_axes(
            [0.89, 0.01, 0.1, 0.1], anchor='SE')
        self._logoaxis.set_axis_off()
        self._logoaxis.set_visible(False)
        self._logo = None
        self.redraw_logo()
        self.show_all()
        self.hide()

    def do_destroy(self):
        if hasattr(self, '_statwindow'):
            logger.debug(
                'Destroying statistics window because plotsasimage is being destroyed.')
            self._statwindow.destroy()

    def _on_statistics_toggled(self, tb):
        logger.debug(
            'Statistics toolbutton toggled. Current state: ' + str(tb.get_active()))
        if tb.get_active():
            self._statwindow = SASImageStatisticsWindow()
            self._statwindow.update_statistics(self._exposure)
            self._statwindowconn = [self._statwindow.connect('delete-event', self._on_statwindow_delete),
                                    self._statwindow.connect('destroy', self._on_statwindow_destroy)]
            self._statwindow.show_all()
            self._statwindow.present()
        elif hasattr(self, '_statwindow'):
            logger.debug(
                'Calling statwindow.destroy() because of toolbutton click.')
            self._statwindow.destroy()
            del self._statwindow

    def _on_statwindow_delete(self, statwin, event):
        logger.debug('statwindow.delete callback running. Calling destroy()')
        statwin.destroy()
        logger.debug('Returned from destroy.')

    def _on_statwindow_destroy(self, statwin):
        logger.debug('statwindow.destroy callback running.')
        for c in self._statwindowconn:
            statwin.disconnect(c)
        logger.debug('Disconnected callbacks.')
        self._statwindowconn = []
        logger.debug('Setting stattbutton to inactive.')
        self._stattbutton.set_active(False)
        logger.debug('Returning from destroy callback.')

    def do_notify(self, prop):
        if prop.name == 'logo':
            try:
                self._logo = scipy.misc.imread(self.logo)
            except IOError:
                pass
        if prop.name in ['logo', 'show-logo']:
            self.redraw_logo()
        if prop.name == 'show-qr':
            self.redraw_qr()

    def clear(self):
        self._imgaxis.clear()
        self._img = None
        self._maskimg = None
        self._logoaxis.clear()
        self._qraxis.clear()
        self._figure_toolbar.update()  # reset the history stack
        self._canvas.draw()

    def redraw_image(self):
        if self._plot_properties.get_keep_zoom():
            previous_zoom = self._imgaxis.axis()
        self._imgaxis.clear()
        self._img = None
        self._maskimg = None
        vmin = self._plot_properties.get_lowclip()
        vmax = self._plot_properties.get_upclip()
        data = np.array(self._exposure)
        if self._plot_properties.get_colorscale() == 'log10':
            norm = matplotlib.colors.LogNorm()
            if (vmin is not None) and (vmin <= 0):
                norm.vmin = None
            else:
                norm.vmin = vmin
            if (vmax is not None) and (vmax <= 0):
                norm.vmax = None
            else:
                norm.vmax = vmax
            norm.autoscale_None(data)
        elif self._plot_properties.get_colorscale() == 'linear':
            norm = matplotlib.colors.Normalize()
            norm.vmin = vmin
            norm.vmax = vmax
            norm.autoscale_None(data)
        if self._plot_properties.get_abscissa() == 'pixel':
            extent = None
        elif self._plot_properties.get_abscissa() == 'q':
            extent = self._exposure.get_q_extent()
            extent = extent[:2] + extent[-1:1:-1]
        self._img = self._imgaxis.imshow(data, norm=norm, interpolation='nearest', cmap=self._plot_properties.get_palette(),
                                         extent=extent, origin='upper')
        if self._plot_properties.get_show_colorbar():
            self._colorbaraxis.clear()
            try:
                self._fig.colorbar(self._img, cax=self._colorbaraxis)
            except ValueError:
                # this can be raised if a uniform image is to be plotted, i.e.
                # image with only one colour.
                pass
            self._colorbaraxis.set_visible(True)
        else:
            self._colorbaraxis.clear()
            self._colorbaraxis.set_visible(False)
        self.redraw_mask()
        if self._plot_properties.get_show_crosshair():
            ax = self._imgaxis.axis()
            if extent is None:
                self._imgaxis.plot(
                    ax[:2], [self._exposure['BeamPosX']] * 2, '-w')
                self._imgaxis.plot(
                    [self._exposure['BeamPosY']] * 2, ax[2:], '-w')
            else:
                self._imgaxis.plot(ax[:2], [0, 0], '-w')
                self._imgaxis.plot([0, 0], ax[2:], '-w')
            self._imgaxis.axis(ax)
        if self._plot_properties.get_keep_zoom():
            self.zoom(previous_zoom)
        self._figure_toolbar.update()  # reset the history stack
        self._canvas.draw()

    def redraw_mask(self):
        if self._maskimg is not None:
            self._maskimg.remove()
            self._maskimg = None
        if self._plot_properties.get_show_mask():
            maskmatrix = np.array(self._exposure.mask) == 0
            # this is a numpy hack to save space. Instead of repeating the mask
            # 4 times along the 3th axis, we set the corresponding stride value
            # to zero.
            maskimage = np.lib.stride_tricks.as_strided(
                maskmatrix, strides=maskmatrix.strides + (0,), shape=maskmatrix.shape + (4,))
            self._maskimg = self._imgaxis.imshow(
                maskimage, alpha=self.mask_alpha, origin='upper', interpolation='nearest', extent=self._img.get_extent())

    def redraw_qr(self):
        self._qraxis.clear()
        try:
            if (not self.show_qr) or (not isinstance(self._exposure, sastool.SASExposure)):
                raise KeyError
            self._qraxis.set_axis_off()
            self._qraxis.set_visible(True)
            qr = qrcode.make(self._exposure['Owner'] + '@CREDO://' + str(
                self._exposure.header) + ' ' + str(self._exposure['Date']), box_size=10)
            self._qraxis.spy(np.array(qr._img.im).reshape(qr._img.size) == 0)
        except KeyError:
            self._qraxis.clear()
            self._qraxis.set_visible(False)
            return
        self._canvas.draw()

    def redraw_logo(self):
        if (self.show_logo and (self._logo is not None)):
            self._logoaxis.clear()
            self._logoaxis.set_axis_off()
            self._logoaxis.imshow(self._logo)
            self._logoaxis.set_visible(True)
        else:
            self._logoaxis.set_visible(False)

    def set_exposure(self, exposure):
        try:
            self._exposure = exposure
            self._plot_properties.update_from_exposure(self._exposure)
            self.redraw_image()
            self.redraw_qr()
            if hasattr(self, '_statwindow'):
                self._statwindow.update_statistics(exposure)
        finally:
            self.emit('exposure-changed', self._exposure)

    def get_exposure(self):
        return self._exposure

    def on_plot_properties_changed(self, plotprops):
        self.redraw_image()

    def get_axes(self):
        return self._imgaxis

    def zoom(self, ax):
        self._imgaxis.axis(ax)
        self._figure_toolbar.push_current()
        self._canvas.draw()

    def get_zoom(self):
        return self._imgaxis.axis()


class PlotSASImageWindow(Gtk.Window):
    __gtype_name__ = 'SASGUI_PlotSASImageWindow2'
    _instance_list = []

    def __init__(self):
        Gtk.Window.__init__(self)
        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(vb)
        self._plot = PlotSASImage()
        self._plot.connect('exposure-changed', self.on_exposure_changed)
        self._plot.set_size_request(640, 480)
        vb.pack_start(self._plot, True, True, 0)
        PlotSASImageWindow._instance_list.append(self)
        self._lastfocustime = time.time()
        self.connect('focus-in-event', self.on_focus)

    def do_destroy(self, *args, **kwargs):
        if not hasattr(self, '_plot'):
            return
        else:
            self._plot.destroy()
            PlotSASImageWindow._instance_list.remove(self)
        return True

    def on_exposure_changed(self, plotbox, exposure):
        if isinstance(exposure, sastool.classes.SASExposure):
            self.set_title(str(exposure))
        else:
            self.set_title('2D Image')

    def on_focus(self, *args, **kwargs):
        self._lastfocustime = time.time()

    @classmethod
    def get_current_plot(cls):
        if not cls._instance_list:
            return cls()
        maxfocustime = max([x._lastfocustime for x in cls._instance_list])
        return [x for x in cls._instance_list if x._lastfocustime == maxfocustime][0]

    def set_exposure(self, exposure):
        self._plot.set_exposure(exposure)

    def get_axes(self):
        return self._plot.get_axes()

    def get_exposure(self):
        return self._plot.get_exposure()

    def zoom(self, ax):
        return self._plot.zoom(ax)

    def get_zoom(self):
        return self._plot.get_zoom()


class SASImageStatisticsWindow(Gtk.Window):
    _stats = [('npix', 'Number of pixels'), ('mean', 'Mean'), ('std', 'Std.Dev.'),
              ('median', 'Median'), ('min', 'Minimum'), ('max', 'Maximum'), ('sum', 'Sum')]

    def __init__(self):
        Gtk.Window.__init__(self, Gtk.WindowType.TOPLEVEL)
        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(vb)
        self._maskedcb = Gtk.CheckButton(label='Do not count masked pixels')
        self._maskedcb.connect(
            'toggled', lambda cb: self.update_statistics(None))
        vb.pack_start(self._maskedcb, False, False, 0)
#         self._zoomedcb = Gtk.CheckButton(label='Only in current zoom')
#         vb.pack_start(self._zoomedcb, False,False,0)
        self._statlist = Gtk.ListStore(
            GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_STRING)
        for sname, slabel in self._stats:
            self._statlist.append([sname, slabel, ''])
        self._statview = Gtk.TreeView(self._statlist)
        cr = Gtk.CellRendererText()
        self._statview.append_column(Gtk.TreeViewColumn('Stat', cr, text=1))
        cr = Gtk.CellRendererText()
        self._statview.append_column(Gtk.TreeViewColumn('Value', cr, text=2))
        vb.pack_start(self._statview, True, True, 0)
        self.set_title('Image statistics')
        vb.show_all()

    def update_statistics(self, exposure=None):
        if exposure is None:
            if not hasattr(self, '_lastexposure'):
                return True
            exposure = self._lastexposure
        if isinstance(exposure, sastool.classes.SASExposure):
            for row in self._statlist:
                if row[0] == 'mean':
                    row[2] = str(
                        float(exposure.mean(masked=self._maskedcb.get_active())))
                elif row[0] == 'std':
                    row[2] = str(
                        float(exposure.std(masked=self._maskedcb.get_active())))
                elif row[0] == 'npix':
                    if self._maskedcb.get_active():
                        row[2] = str(exposure.mask.mask.sum())
                    else:
                        row[2] = str(exposure.size)
                elif row[0] == 'min':
                    row[2] = str(
                        float(exposure.min(masked=self._maskedcb.get_active())))
                elif row[0] == 'max':
                    row[2] = str(
                        float(exposure.max(masked=self._maskedcb.get_active())))
                elif row[0] == 'median':
                    row[2] = str(
                        float(exposure.median(masked=self._maskedcb.get_active())))
                elif row[0] == 'sum':
                    row[2] = str(
                        float(exposure.sum(masked=self._maskedcb.get_active())))
        else:
            for row in self._statlist:
                if row[0] == 'mean':
                    row[2] = str(np.mean(exposure))
                elif row[0] == 'std':
                    row[2] = str(np.std(exposure))
                elif row[0] == 'npix':
                    row[2] = str(exposure.size)
                elif row[0] == 'min':
                    row[2] = str(np.min(exposure))
                elif row[0] == 'max':
                    row[2] = str(np.max(exposure))
                elif row[0] == 'median':
                    row[2] = str(np.median(exposure))
                elif row[0] == 'sum':
                    row[2] = str(np.sum(exposure))
        self._lastexposure = exposure
        return
