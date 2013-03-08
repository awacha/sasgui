'''
Created on Sep 10, 2012

@author: andris
'''
import gtk
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg, NavigationToolbar2GTKAgg
import matplotlib
import numpy as np
import itertools
import gc
import time

from sastool.classes import SASExposure, SASMask

default_palette = 'jet'

__all__ = ['PlotSASImage', 'PlotSASImageWindow']

class PlotSASImage(gtk.VBox):
    _exposure = None
    __gsignals__ = {'delete-event':'override'}
    def __init__(self, exposure=None, after_draw_cb=None):
        gtk.VBox.__init__(self)
        self.after_draw_cb = after_draw_cb
        self.properties_frame = gtk.Expander()
        self.properties_frame.set_label('Plot properties')
        self.pack_start(self.properties_frame, False)
        tab = gtk.Table()
        self.properties_frame.add(tab)
        l = gtk.Label('Palette:')
        l.set_alignment(0, 0.5)
        tab.attach(l, 0, 1, 0, 1, gtk.FILL, gtk.FILL)
        self.palette_combo = gtk.combo_box_new_text()
        tab.attach(self.palette_combo, 1, 2, 0, 1)
        self.palette_combo.connect('changed', self.draw_image, 'force')
        [self.palette_combo.append_text(m) for m in dir(matplotlib.cm) if eval('isinstance(matplotlib.cm.%s,matplotlib.colors.Colormap)' % m) and not m.endswith('_r')]
        self.palette_combo.set_active([i for i, l in itertools.izip(itertools.count(0), self.palette_combo.get_model()) if l[0] == default_palette][0])

        l = gtk.Label('Color scale:')
        l.set_alignment(0, 0.5)
        tab.attach(l, 0, 1, 1, 2, gtk.FILL, gtk.FILL)
        self.zscale_combo = gtk.combo_box_new_text()
        tab.attach(self.zscale_combo, 1, 2, 1, 2)
        for n in ['linear', 'log', 'sqrt']:
            self.zscale_combo.append_text(n)
        self.zscale_combo.set_active(0)
        self.zscale_combo.connect('changed', self.draw_image, 'force')

        self.lowclip_checkbutton = gtk.CheckButton('Lower clip:')
        tab.attach(self.lowclip_checkbutton, 2, 3, 0, 1, gtk.FILL, gtk.FILL)
        self.lowclip_entry = gtk.Entry()
        tab.attach(self.lowclip_entry, 3, 4, 0, 1)
        self.lowclip_checkbutton.connect('toggled', self.on_clipcheckbutton_toggled, self.lowclip_entry)

        self.highclip_checkbutton = gtk.CheckButton('Upper clip:')
        tab.attach(self.highclip_checkbutton, 2, 3, 1, 2, gtk.FILL, gtk.FILL)
        self.highclip_entry = gtk.Entry()
        tab.attach(self.highclip_entry, 3, 4, 1, 2)
        self.highclip_checkbutton.connect('toggled', self.on_clipcheckbutton_toggled, self.highclip_entry)


        hb = gtk.HBox()
        tab.attach(hb, 0, 4, 2, 3)
        self.palette_reversed_checkbutton = gtk.CheckButton('Reversed palette')
        hb.pack_start(self.palette_reversed_checkbutton)
        self.palette_reversed_checkbutton.connect('toggled', self.draw_image, 'force')

        self.qorpixel_toggle = gtk.ToggleButton('Q / pixel')
        hb.pack_start(self.qorpixel_toggle)
        self.qorpixel_toggle.connect('toggled', self.on_qorpixel_toggled)

        self.plotmask_checkbutton = gtk.CheckButton('Plot mask')
        hb.pack_start(self.plotmask_checkbutton)
        self.plotmask_checkbutton.connect('toggled', self.draw_image, 'plotmask')

        self.beampos_checkbutton = gtk.CheckButton('Beam position')
        hb.pack_start(self.beampos_checkbutton)
        self.beampos_checkbutton.connect('toggled', self.draw_image, 'beampos')

        self.colorbar_checkbutton = gtk.CheckButton('Color bar')
        hb.pack_start(self.colorbar_checkbutton)
        self.colorbar_checkbutton.connect('toggled', self.draw_image, 'colorbar')

        self.fig = Figure(figsize=(3.75, 2.5), dpi=80)
        self.canvas = FigureCanvasGTKAgg(self.fig)
        self.canvas.set_size_request(640, 480)
        self.pack_start(self.canvas)
        self.connect('parent-set', self.on_parent_set)
        self.exposure = exposure
        self.show_all()
        self.hide()
        self.connect('destroy', self.on_delete)
    def on_delete(self, *args, **kwargs):
        del self._exposure
        self.fig.clf()
        del self.fig
        del self.canvas
        gc.collect()
    def get_axes(self):
        if len(self.fig.axes) == 0:
            self.fig.add_subplot(1, 1, 1)
        return self.fig.axes[0]
    axes = property(get_axes)
    def gca(self, *args, **kwargs):
        return self.fig.gca(*args, **kwargs)
    def on_parent_set(self, widget, oldparent):
        self.figure_toolbar = NavigationToolbar2GTKAgg(self.canvas, self.get_toplevel())
        self.pack_start(self.figure_toolbar, False)
        tbutton = gtk.ToolButton(gtk.STOCK_CLEAR)
        tbutton.connect('clicked', self.draw_image, 'clear')
        self.figure_toolbar.insert(tbutton, 0)
        tbutton = gtk.ToolButton(gtk.STOCK_REFRESH)
        tbutton.connect('clicked', self.draw_image, 'uberforce')
        self.figure_toolbar.insert(tbutton, 0)
    def on_clipcheckbutton_toggled(self, cb, entry):
        entry.set_sensitive(cb.get_active())
        return True
    def on_qorpixel_toggled(self, button):
        if not button.get_active():
            button.set_label('Pixel / q')
        else:
            button.set_label('Q / pixel')
        self.draw_image(button, 'axes')
    def set_exposure(self, exposure):
        if self._exposure is not None:
            del self._exposure
        self._exposure = exposure
        if isinstance(exposure, SASExposure):
            self.plotmask_checkbutton.set_active(exposure.check_for_mask(False))
            self.beampos_checkbutton.set_active(('BeamPosX' in exposure.header) and ('BeamPosY' in exposure.header))
        self.update_properties_tools()
        self.draw_image(what='uberforce')
    def update_properties_tools(self):
        if not isinstance(self.exposure, SASExposure):
            self.palette_combo.set_sensitive(False)
            self.palette_reversed_checkbutton.set_sensitive(False)
            self.colorbar_checkbutton.set_sensitive(False)
            self.zscale_combo.set_sensitive(False)
            self.qorpixel_toggle.set_sensitive(False)
            self.plotmask_checkbutton.set_sensitive(False)
            self.beampos_checkbutton.set_sensitive(False)
            self.lowclip_checkbutton.set_sensitive(False)
            self.highclip_checkbutton.set_sensitive(False)
            self.lowclip_entry.set_sensitive(False)
            self.highclip_entry.set_sensitive(False)
        else:
            self.palette_combo.set_sensitive(True)
            self.zscale_combo.set_sensitive(True)
            self.palette_reversed_checkbutton.set_sensitive(True)
            self.lowclip_checkbutton.set_sensitive(True)
            self.on_clipcheckbutton_toggled(self.lowclip_checkbutton, self.lowclip_entry)
            self.highclip_checkbutton.set_sensitive(True)
            self.on_clipcheckbutton_toggled(self.highclip_checkbutton, self.highclip_entry)
            self.colorbar_checkbutton.set_sensitive(True)
            self.plotmask_checkbutton.set_sensitive(isinstance(self.exposure.mask, SASMask))
            if not isinstance(self.exposure.mask, SASMask):
                self.plotmask_checkbutton.set_active(False)
            if ('BeamPosX' in self.exposure.header) and ('BeamPosY' in self.exposure.header):
                self.beampos_checkbutton.set_sensitive(True)
            else:
                self.beampos_checkbutton.set_sensitive(False)
                self.beampos_checkbutton.set_active(False)
            if len(self.exposure.check_for_q(False)) == 0:
                self.qorpixel_toggle.set_sensitive(True)
            else:
                self.qorpixel_toggle.set_sensitive(False)
                self.qorpixel_toggle.set_active(False)
        return True
    def get_exposure(self):
        return self._exposure
    exposure = property(get_exposure, set_exposure)
    def get_palette(self):
        palname = self.palette_combo.get_active_text()
        if self.palette_reversed_checkbutton.get_active():
            palname = palname + '_r'
        return eval('matplotlib.cm.%s' % palname)
    def get_zscale(self):
        return self.zscale_combo.get_active_text()
    def draw_image(self, widget=None, what='uberforce'):
        if what == 'clear':
            self.fig.clf()
            self.canvas.draw()
            return
        if what == 'uberforce':
            self.fig.clf()
            what = 'force'
        if not isinstance(self.exposure, SASExposure):
            return
        if len(self.fig.axes) == 0:
            self.fig.add_subplot(1, 1, 1)
            what = 'force'
        plot_axes = self.fig.axes[0]
        draw_colorbar = self.colorbar_checkbutton.get_active()
        if draw_colorbar:
            what = 'force'
        if (what == 'beampos' or what == 'force') and (len(plot_axes.get_lines()) >= 2):
            for l in plot_axes.get_lines():
                l.remove()
        if (what == 'plotmask' or what == 'force') and (len(plot_axes.get_images()) >= 2):
            plot_axes.get_images()[1].remove()
        if what == 'force':
            matrixtoplot = 'Intensity'
            for l in plot_axes.get_images():
                l.remove()
            for l in plot_axes.get_lines():
                l.remove()
        else:
            matrixtoplot = None

        if draw_colorbar and len(self.fig.axes) > 1:
            draw_colorbar = self.fig.axes[1]
        if not draw_colorbar and len(self.fig.axes) > 1:
            self.fig.delaxes(self.fig.axes[1])
        if self.lowclip_checkbutton.get_active():
            minvalue = float(self.lowclip_entry.get_text())
        else:
            minvalue = np.nanmin(self.exposure)
            self.lowclip_entry.set_text(str(minvalue))
        if self.highclip_checkbutton.get_active():
            maxvalue = float(self.highclip_entry.get_text())
        else:
            maxvalue = np.nanmax(self.exposure)
            self.highclip_entry.set_text(str(maxvalue))
        img, mat = self.exposure.plot2d(axes=plot_axes, return_matrix=True,
                                        drawcolorbar=draw_colorbar,
                                        matrix=matrixtoplot,
                                        zscale=self.get_zscale(),
                                        cmap=self.get_palette(),
                                        minvalue=minvalue,
                                        maxvalue=maxvalue,
                                        crosshair=self.beampos_checkbutton.get_active() and (what == 'beampos' or what == 'force'),
                                        drawmask=self.plotmask_checkbutton.get_active() and (what == 'force' or what == 'plotmask'),
                                        qrange_on_axis=self.qorpixel_toggle.get_active(),
                                        )
        # put beam center cross-hair lines to top.
        for l in plot_axes.get_lines():
            l.set_zorder(max([0] + [x.get_zorder() + 1 for x in plot_axes.get_images()]))
        if what == 'force' and callable(self.after_draw_cb):
            self.after_draw_cb(self.exposure, self.fig, plot_axes)
        self.canvas.draw()

class PlotSASImageWindow(gtk.Dialog):
    __gsignals__ = {'delete-event':'override'}
    _instance_list = []
    def __init__(self, exposure=None, title='Image', parent=None, flags=gtk.DIALOG_DESTROY_WITH_PARENT, buttons=()):
        gtk.Dialog.__init__(self, title, parent, flags, buttons)
        self.set_default_response(gtk.RESPONSE_OK)
        vb = self.get_content_area()
        self.plot = PlotSASImage(None)
        vb.pack_start(self.plot, True)
        PlotSASImageWindow._instance_list.append(self)
        self._lastfocustime = time.time()
        self.connect('delete-event', self.on_delete)
        self.connect('focus-in-event', self.on_focus)
        self.set_exposure(exposure)
    def on_delete(self, *args, **kwargs):
        self.plot.destroy()
        self.destroy()
        PlotSASImageWindow._instance_list.remove(self)
        return True
    def on_focus(self, *args, **kwargs):
        self._lastfocustime = time.time()
    @classmethod
    def get_current_plot(cls):
        if not cls._instance_list:
            return cls()
        maxfocustime = max([x._lastfocustime for x in cls._instance_list])
        return [x for x in cls._instance_list if x._lastfocustime == maxfocustime][0]
    def set_exposure(self, exposure):
        self.plot.set_exposure(exposure)
        if exposure is not None:
            self.set_title(unicode(exposure.header))
    def get_axes(self):
        return self.plot.get_axes()
    def get_exposure(self):
        return self.plot.get_exposure()
    
