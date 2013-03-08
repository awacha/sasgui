from gi.repository import Gtk
from gi.repository import GObject

from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg
from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3

from filetab import FileTab
from plottab import PlotTab
from masktab import MaskTab
from centeringtab import CenteringTab
from integratetab import IntegrateTab

from .. import maskmaker
from sastool.classes import SASMask

class GUIStopFittingException(Exception):
    pass

import sys
import traceback

class SASImageGuiExceptHook():
    oldexcepthook = None
    def __init__(self):
        if isinstance(sys.excepthook, self.__class__):
            raise RuntimeError('SASImageGuiExceptHook has already been installed.')
        self.oldexcepthook = sys.excepthook
        sys.excepthook = self
    def __call__(self, type_, value, traceback_):
        dialog = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK,
                                   str(type_) + ': ' + str(value))
        dialog.format_secondary_text('Traceback:')
        msgarea = dialog.get_message_area()
        sw = Gtk.ScrolledWindow()
        sw.set_size_request(200, 300)
        msgarea.pack_start(sw, True, True, 0)
        tv = Gtk.TextView()
        sw.add(tv)
        tv.get_buffer().set_text('\n'.join(traceback.format_tb(traceback_)))
        tv.set_editable(False)
        tv.set_wrap_mode(Gtk.WrapMode.WORD)
        # tv.get_default_attributes().font = Pango.FontDescription('serif,monospace')
        tv.set_justification(Gtk.Justification.LEFT)
        msgarea.show_all()
        dialog.set_title('Error!')
        dialog.run()
        dialog.destroy()
        return None
        # self.oldexcepthook(type_, value, traceback)
    def __del__(self):
        # THIS IS NOT QUITE OK: other excepthooks registered after SASImageGuieExceptHook will
        # be quietly removed.
        if self.oldexcepthook is not None:
            sys.excepthook = self.oldexcepthook

class SASImageGuiMain(Gtk.Window):
    _instances = []
    def __init__(self):
        SASImageGuiMain._instances.append(self)
        try:
            SASImageGuiMain._excepthook = SASImageGuiExceptHook()
        except RuntimeError:
            pass
        Gtk.Window.__init__(self, Gtk.WindowType.TOPLEVEL)

        self.connect('delete-event', self.on_delete)
        self.fig = Figure(figsize=(0.5, 0.4), dpi=72)
        self.axes = self.fig.add_subplot(111)

        vbox = Gtk.VBox()
        self.add(vbox)
        self.ribbon = Gtk.Notebook()
        vbox.pack_start(self.ribbon, False, True, 0)
        self.ribbon.set_scrollable(True)
        self.ribbon.popup_enable()

        self.ribbon_File = FileTab()
        self.ribbon.append_page(self.ribbon_File, Gtk.Label(label='File'))
        self.ribbon.set_tab_detachable(self.ribbon_File, True)
        self.ribbon_File.connect('new-clicked', self.on_file, 'newwindow')
        self.ribbon_File.connect('close-clicked', self.on_file, 'closewindow')
        self.ribbon_File.connect('quit-clicked', self.on_file, 'quitprogram')
        self.ribbon_File.connect('opened', self.on_file_opened)

        self.ribbon_Plot = PlotTab()
        self.ribbon.append_page(self.ribbon_Plot, Gtk.Label(label='Plot'))
        self.ribbon_Plot.connect('clear-graph', self.on_plot, 'clear-graph')
        self.ribbon_Plot.connect('refresh-graph', self.on_plot, 'refresh-graph')
        self.ribbon_Plot.connect('plotparams-changed', self.on_plot, 'refresh-graph')

        self.ribbon_Mask = MaskTab()
        self.ribbon.append_page(self.ribbon_Mask, Gtk.Label(label='Mask'))
        self.ribbon_Mask.connect('new-mask', self.on_mask, 'new-mask')
        self.ribbon_Mask.connect('edit-mask', self.on_mask, 'edit-mask')

        self.ribbon_Centering = CenteringTab()
        self.ribbon.append_page(self.ribbon_Centering, Gtk.Label(label='Centering'))
        self.ribbon_Centering.connect('crosshair', self.on_center)
        self.ribbon_Centering.connect('docentering', self.on_center)
        self.ribbon_Centering.connect('manual-beampos', self.on_center)

        self.ribbon_Integrate = IntegrateTab()
        self.ribbon.append_page(self.ribbon_Integrate, Gtk.Label(label='Integrate'))
        self.ribbon_Integrate.connect('integration-done', self.on_integration_done)

        for k in self.ribbon.get_children():
            self.ribbon.set_tab_detachable(k, True)
            self.ribbon.set_tab_reorderable(k, True)
            k.connect('error', self.on_error)

        self.canvas = FigureCanvasGTK3Agg(self.fig)
        self.canvas.set_size_request(800, 400)
        vbox.pack_start(self.canvas, True, True, 0)

        self.graphtoolbar = NavigationToolbar2GTK3(self.canvas, vbox)
        vbox.pack_start(self.graphtoolbar, False, True, 0)

        self.statusbar = Gtk.Statusbar()
        vbox.pack_start(self.statusbar, False, True, 0)
        self.show_all()
        self.hide()
        
    def on_file(self, widget, argument):  # IGNORE:W0613
        if argument == 'newwindow':
            newinstance = SASImageGuiMain()
            newinstance.show_all()
        elif argument == 'closewindow':
            self.destroy()
            self.on_delete(None, None)
        elif argument == 'quitprogram':
            Gtk.main_quit()
        return True
    def on_delete(self, widget, event, *args):  # IGNORE:W0613
        SASImageGuiMain._instances.remove(self)
        if not SASImageGuiMain._instances:
            Gtk.main_quit()
        return False
    def on_file_opened(self, widget, data):  # IGNORE:W0613
        self.statusbar.remove_all(self.statusbar.get_context_id('sastool'))
        self.statusbar.push(self.statusbar.get_context_id('sastool'), 'File opened.')
        self.ribbon_Plot.update_from_data(data)
        self.ribbon_Integrate.update_from_data(data)
        self.on_plot(None, 'refresh-graph')
        return True
    def on_error(self, widget, error):  # IGNORE:W0613
        self.statusbar.remove_all(self.statusbar.get_context_id('sastool'))
        self.statusbar.push(self.statusbar.get_context_id('sastool'), 'Error: ' + unicode(error))
        return True
    def on_plot(self, widget, argument):  # IGNORE:W0613
        if argument == 'clear-graph':
            self.fig.clf()
            self.axes = self.fig.add_subplot(1, 1, 1)
        if argument == 'refresh-graph':
            self.axes.cla()
            self.ribbon_Plot.plot2d(self.data, axes=self.axes)
        self.canvas.draw_idle()
        return True
    def get_data(self):
        return self.ribbon_File.data
    def on_mask(self, widget, argument):  # IGNORE:W0613
        if self.data is None:
            return False
        if argument == 'new-mask':
            self.data.set_mask(self.data.Intensity * 0 + 1)
        elif argument == 'edit-mask':
            mm = maskmaker.MaskMaker(parent=self, matrix=self.ribbon_Plot.lastplotraw, mask=self.data.mask)
            if mm.run() == Gtk.ResponseType.OK:
                self.data.set_mask(SASMask(mm.get_mask(), maskid=mm.maskid))
            mm.destroy()
        self.ribbon_Integrate.update_from_data(self.data)
        self.on_plot(None, 'refresh-graph')
    def on_center(self, widget, method, args):  # IGNORE:W0613
        if method == 'crosshair':
            ax = self.axes.axis()
            centercoords = (0.5 * (ax[2] + ax[3]), 0.5 * (ax[0] + ax[1]))
            if self.ribbon_Plot.get_axesunits() == 'q':
                centercoords = self.data.qtopixel(*centercoords)
            method = 'manual clicking'
        elif method == 'manual-beampos':
            centercoords = args[:2]
            method = 'manual setting'
        elif hasattr(self.data, 'find_beam_' + method):
            dialog = Gtk.Dialog('Finding beam center...', self.get_toplevel(), Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                              (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
            dialog.set_default_response(Gtk.ResponseType.CANCEL)
            l = Gtk.Label('Centering, please wait...'); l.set_alignment(0, 0.5)
            dialog.get_content_area().pack_start(l, True, True, 0)
            pb = Gtk.ProgressBar()
            dialog.get_content_area().pack_start(pb, True, True, 0)
            def closedialogfunction(*args, **kwargs):  # IGNORE:W0613
                dialog.hide()
            dialog.get_widget_for_response(Gtk.ResponseType.CANCEL).connect('clicked', closedialogfunction)
            dialog.connect('delete-event', closedialogfunction)
            dialog.show_all()
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)
            def callbackfunction():
                pb.pulse()
                while Gtk.events_pending():
                    Gtk.main_iteration_do(False)
                if not dialog.get_visible():
                    raise GUIStopFittingException
            try:
                centercoords = self.data.__getattribute__('find_beam_' + method).__call__(*args, callback=callbackfunction)
            except:
                if dialog.get_visible():
                    raise
                centercoords = None
            finally:
                dialog.destroy()
        else:
            raise ValueError('Invalid beam finding mode: ' + method)
        if centercoords is not None:
            self.data.update_beampos(centercoords, method)
            self.ribbon_Centering.set_beampos(centercoords)
            self.ribbon_Integrate.update_from_data(self.data)
            self.on_plot(None, 'refresh-graph')
    def on_integration_done(self, widget, curve, retmask, mode, radiustype):  # IGNORE:W0613
        self.fig.clf()
        self.axes = self.fig.add_subplot(1, 2, 1)
        mask1 = self.data.mask
        try:
            self.data.set_mask(retmask == 0)
            self.on_plot(None, 'refresh-graph')
            axes2 = self.fig.add_subplot(1, 2, 2)
            if mode == 'Azimuthal':
                curve.semilogy(axes=axes2)
                axes2.set_xlabel('Azimuth angle (deg.)')
                axes2.set_ylabel('Intensity')
            else:
                curve.loglog(axes=axes2)
                axes2.set_xlabel(u'q (\xc5$^{-1}$')
                axes2.set_ylabel('Intensity')
            self.fig.canvas.draw()
        finally:
            self.data.set_mask(mask1)
        return True

    data = property(get_data)
