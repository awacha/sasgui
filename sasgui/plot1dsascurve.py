from gi.repository import Gtk
from gi.repository import GObject
from .fitter import Fitter
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg
from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3
import itertools
import sastool
import time
__all__ = ['PlotSASCurve', 'PlotSASCurveWindow']


class PlotSASCurve(Gtk.Box):
    def __init__(self, orientation=Gtk.Orientation.HORIZONTAL):
        Gtk.Box.__init__(self, orientation=orientation)
        ex = Gtk.Expander(label='Fitting...')
        ex.get_label_widget().set_angle(90)
        self.pack_start(ex, False, True, 0)
        vbox_fig = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.pack_start(vbox_fig, True, True, 0)
        
        settingsexpander = Gtk.Expander(label='Plot properties')
        vbox_fig.pack_start(settingsexpander, False, True, 0)
        
        tab = Gtk.Table()
        settingsexpander.add(tab)
        row = 0
        col = 0
        
        l = Gtk.Label(label='Plot type:'); l.set_alignment(0, 0.5)
        tab.attach(l, 2 * col, 2 * col + 1, row, row + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.plottype_combo = Gtk.ComboBoxText()
        tab.attach(self.plottype_combo, 2 * col + 1, 2 * col + 2, row, row + 1)
        self.plottype_combo.append_text('Lin-lin')
        self.plottype_combo.append_text('Lin-log')
        self.plottype_combo.append_text('Log-lin')
        self.plottype_combo.append_text('Log-log')
        self.plottype_combo.set_active(3)
        self.plottype_combo.connect('changed', self.on_plottype_changed)
        row += 1
        
        l = Gtk.Label(label='X axis title:'); l.set_alignment(0, 0.5)
        tab.attach(l, 2 * col, 2 * col + 1, row, row + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.xtitle_entry = Gtk.Entry()
        self.xtitle_entry.connect('changed', self.on_textentry_changed)
        tab.attach(self.xtitle_entry, 2 * col + 1, 2 * col + 2, row, row + 1)
        row += 1

        l = Gtk.Label(label='Y axis title:'); l.set_alignment(0, 0.5)
        tab.attach(l, 2 * col, 2 * col + 1, row, row + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.ytitle_entry = Gtk.Entry()
        self.ytitle_entry.connect('changed', self.on_textentry_changed)
        tab.attach(self.ytitle_entry, 2 * col + 1, 2 * col + 2, row, row + 1)
        row += 1
        
        l = Gtk.Label(label='Title:'); l.set_alignment(0, 0.5)
        tab.attach(l, 2 * col, 2 * col + 1, row, row + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.title_entry = Gtk.Entry()
        self.title_entry.connect('changed', self.on_textentry_changed)
        tab.attach(self.title_entry, 2 * col + 1, 2 * col + 2, row, row + 1)
        row = 0
        col += 1

        self.xmin_cb = Gtk.CheckButton(label='X min:'); self.xmin_cb.set_alignment(0, 0.5)
        tab.attach(self.xmin_cb, 2 * col, 2 * col + 1, row, row + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.xmin_entry = Gtk.Entry()
        tab.attach(self.xmin_entry, 2 * col + 1, 2 * col + 2, row, row + 1)
        self.xmin_cb.connect('toggled', self.on_checkbutton_with_entry, self.xmin_entry)
        row += 1
        
        self.xmax_cb = Gtk.CheckButton(label='X max:'); self.xmax_cb.set_alignment(0, 0.5)
        tab.attach(self.xmax_cb, 2 * col, 2 * col + 1, row, row + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.xmax_entry = Gtk.Entry()
        tab.attach(self.xmax_entry, 2 * col + 1, 2 * col + 2, row, row + 1)
        self.xmax_cb.connect('toggled', self.on_checkbutton_with_entry, self.xmax_entry)
        row += 1

        self.ymin_cb = Gtk.CheckButton(label='Y min:'); self.ymin_cb.set_alignment(0, 0.5)
        tab.attach(self.ymin_cb, 2 * col, 2 * col + 1, row, row + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.ymin_entry = Gtk.Entry()
        tab.attach(self.ymin_entry, 2 * col + 1, 2 * col + 2, row, row + 1)
        self.ymin_cb.connect('toggled', self.on_checkbutton_with_entry, self.ymin_entry)
        row += 1
        
        self.ymax_cb = Gtk.CheckButton(label='Y max:'); self.ymax_cb.set_alignment(0, 0.5)
        tab.attach(self.ymax_cb, 2 * col, 2 * col + 1, row, row + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.ymax_entry = Gtk.Entry()
        tab.attach(self.ymax_entry, 2 * col + 1, 2 * col + 2, row, row + 1)
        self.ymax_cb.connect('toggled', self.on_checkbutton_with_entry, self.ymax_entry)
        row += 1

        self.fig = Figure(figsize=(0.2, 0.2), dpi=72)
        self.canvas = FigureCanvasGTK3Agg(self.fig)
        # self.canvas.set_size_request(640, 480)
        vbox_fig.pack_start(self.canvas, True, True, 0)
        tb = NavigationToolbar2GTK3(self.canvas, None)
        vbox_fig.pack_start(tb, False, True, 0)

        tbutton = Gtk.ToolButton(Gtk.STOCK_CLEAR)
        tbutton.connect('clicked', lambda tbutton:self.cla())
        tb.insert(tbutton, 0)
        tbutton = Gtk.ToolButton(Gtk.STOCK_REFRESH)
        tbutton.connect('clicked', lambda tbutton:self.refresh_graph())
        tb.insert(tbutton, 0)
        
        
        self.fitter = Fitter(axes=self.gca())
        ex.add(self.fitter)
        ex.connect('notify::expanded', self.on_expand)
        self.on_checkbutton_with_entry(self.xmin_cb, self.xmin_entry)
        self.on_checkbutton_with_entry(self.xmax_cb, self.xmax_entry)
        self.on_checkbutton_with_entry(self.ymin_cb, self.ymin_entry)
        self.on_checkbutton_with_entry(self.ymax_cb, self.ymax_entry)

    def refresh_graph(self):
        axis = list(self.gca().axis())
        for i, cb, entry in zip(itertools.count(0), [self.xmin_cb, self.xmax_cb, self.ymin_cb, self.ymax_cb], [self.xmin_entry, self.xmax_entry, self.ymin_entry, self.ymax_entry]):
            if cb.get_active():
                try:
                    axis[i] = float(entry.get_text())
                except ValueError:
                    pass
        self.on_textentry_changed(None)
    def on_checkbutton_with_entry(self, cb, entry):
        entry.set_sensitive(cb.get_active())
        if cb == self.xmin_cb:
            self.xmin_entry.set_text(str(self.gca().get_xlim()[0]))
        elif cb == self.xmax_cb:
            self.xmax_entry.set_text(str(self.gca().get_xlim()[1]))
        elif cb == self.ymin_cb:
            self.ymin_entry.set_text(str(self.gca().get_ylim()[0]))
        elif cb == self.ymax_cb:
            self.ymax_entry.set_text(str(self.gca().get_ylim()[1]))
        return True
    def on_textentry_changed(self, entry=None):
        if entry == self.xtitle_entry or entry is None:
            self.gca().set_xlabel(self.xtitle_entry.get_text())
        if entry == self.ytitle_entry or entry is None:
            self.gca().set_ylabel(self.ytitle_entry.get_text())
        if entry == self.title_entry or entry is None:
            self.gca().set_title(self.title_entry.get_text())
    def on_plottype_changed(self, combo):
        xscale, yscale = [x.lower().replace('lin', 'linear') for x in combo.get_active_text().split('-')]
        self.gca().set_xscale(xscale)
        self.gca().set_yscale(yscale)
        self.draw()
        return False
    def on_expand(self, expander, *args):
        if expander.get_expanded():
            expander.get_label_widget().set_angle(0)
        else:
            expander.get_label_widget().set_angle(90)
        return True
    def gca(self):
        return self.fig.gca()
    def plot(self, *args, **kwargs):
        try:
            if args and isinstance(args[0], sastool.classes.GeneralCurve):
                kwargs['axes'] = self
                args[0].plot(*args[1:], **kwargs)
            else:
                ret = self.gca().plot(*args, **kwargs)
                return ret
        finally:
            self.draw()
    def loglog(self, *args, **kwargs):
        try:
            if args and isinstance(args[0], sastool.classes.GeneralCurve):
                kwargs['axes'] = self
                args[0].loglog(*args[1:], **kwargs)
            else:
                ret = self.gca().loglog(*args, **kwargs)
                return ret
        finally:
            self.draw()
    def errorbar(self, *args, **kwargs):
        try:
            if args and isinstance(args[0], sastool.classes.GeneralCurve):
                kwargs['axes'] = self
                args[0].errorbar(*args[1:], **kwargs)
            else:
                ret = self.gca().errorbar(*args, **kwargs)
                return ret
        finally:
            self.draw()
    def semilogy(self, *args, **kwargs):
        try:
            if args and isinstance(args[0], sastool.classes.GeneralCurve):
                kwargs['axes'] = self
                args[0].semilogy(*args[1:], **kwargs)
            else:
                ret = self.gca().semilogy(*args, **kwargs)
                return ret
        finally:
            self.draw()
    def semilogx(self, *args, **kwargs):
        try:
            if args and isinstance(args[0], sastool.classes.GeneralCurve):
                kwargs['axes'] = self
                args[0].semilogx(*args[1:], **kwargs)
            else:
                ret = self.gca().semilogx(*args, **kwargs)
                return ret
        finally:
            self.draw()
    def draw(self):
        self.refresh_graph()
        return self.canvas.draw()
    def cla(self, *args, **kwargs):
        return self.gca().clear(*args, **kwargs)
    def legend(self, *args, **kwargs):
        return self.gca().legend(*args, **kwargs)
    def text(self, *args, **kwargs):
        return self.gca().text(*args, **kwargs)
    def figtext(self, *args, **kwargs):
        return self.figure.text(*args, **kwargs)
    def title(self, *args, **kwargs):
        return self.gca().title(*args, **kwargs)
    def xlabel(self, *args, **kwargs):
        return self.gca().set_xlabel(*args, **kwargs)
    def ylabel(self, *args, **kwargs):
        return self.gca().set_ylabel(*args, **kwargs)
    def axis(self, *args, **kwargs):
        return self.gca().axis(*args, **kwargs)
    
class PlotSASCurveWindow(Gtk.Dialog):
    __gsignals__ = {'delete-event':'override'}
    _instance_list = []
    def __init__(self, title='Curve', parent=None, flags=Gtk.DialogFlags.DESTROY_WITH_PARENT, buttons=()):
        Gtk.Dialog.__init__(self, title, parent, flags, buttons)
        self.set_default_response(Gtk.ResponseType.OK)
        vb = self.get_content_area()
        self.plotsascurve = PlotSASCurve()
        self.plotsascurve.set_size_request(640, 480)
        vb.pack_start(self.plotsascurve, True, True, 0)
        PlotSASCurveWindow._instance_list.append(self)
        self._lastfocustime = time.time()
        self.connect('delete-event', self.on_delete)
        self.connect('focus-in-event', self.on_focus)
        vb.show_all()
    def on_delete(self, *args, **kwargs):
        self.plotsascurve.destroy()
        self.destroy()
        PlotSASCurveWindow._instance_list.remove(self)
        return True
    def on_focus(self, *args, **kwargs):
        self._lastfocustime = time.time()
    @classmethod
    def get_current_plot(cls):
        if not cls._instance_list:
            return cls()
        maxfocustime = max([x._lastfocustime for x in cls._instance_list])
        return [x for x in cls._instance_list if x._lastfocustime == maxfocustime][0]
    def gca(self):
        return self.plotsascurvesascurve.gca()
    def plot(self, *args, **kwargs):
        return self.plotsascurve.plot(*args, **kwargs)
    def loglog(self, *args, **kwargs):
        return self.plotsascurve.loglog(*args, **kwargs)
    def errorbar(self, *args, **kwargs):
        return self.plotsascurve.errorbar(*args, **kwargs)
    def semilogy(self, *args, **kwargs):
        return self.plotsascurve.semilogy(*args, **kwargs)
    def semilogx(self, *args, **kwargs):
        return self.plotsascurve.semilogx(*args, **kwargs)
    def cla(self, *args, **kwargs):
        return self.plotsascurve.clear(*args, **kwargs)
    def legend(self, *args, **kwargs):
        return self.plotsascurve.legend(*args, **kwargs)
    def text(self, *args, **kwargs):
        return self.plotsascurve.text(*args, **kwargs)
    def figtext(self, *args, **kwargs):
        return self.figure.text(*args, **kwargs)
    def title(self, *args, **kwargs):
        return self.plotsascurve.title(*args, **kwargs)
    def xlabel(self, *args, **kwargs):
        return self.plotsascurve.set_xlabel(*args, **kwargs)
    def ylabel(self, *args, **kwargs):
        return self.plotsascurve.set_ylabel(*args, **kwargs)
    def axis(self, *args, **kwargs):
        return self.plotsascurve.axis(*args, **kwargs)
