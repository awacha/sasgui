from gi.repository import Gtk
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg
from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3
from matplotlib.lines import Line2D
import itertools
import sastool
import time
import numpy as np
__all__ = ['PlotSASCurve', 'PlotSASCurveWindow']
import libconfig

COLORS = 'bgrcmyk'
MARKERS = ['', '.', ',', 'o', 'v', 's', '*', '+', 'D', '^', 'x']
LINESTYLES = ['-', '--', '-.', ':']

itertools.product(MARKERS, COLORS, LINESTYLES)

class PlotSASCurve(Gtk.Box):
    __gtype_name__ = 'SASGUI_PlotSASCurve'
    _curvestyles = [{'marker':m, 'color':c, 'linestyle':ls} for ls, m, c in itertools.product(LINESTYLES, MARKERS, COLORS)  ]
    def __init__(self, orientation=Gtk.Orientation.HORIZONTAL):
        Gtk.Box.__init__(self, orientation=orientation)
        self._curves = []
        vbox_fig = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.pack_start(vbox_fig, True, True, 0)
        
        settingsexpander = Gtk.Expander(label='Plot properties')
        vbox_fig.pack_start(settingsexpander, False, True, 0)
        
        grid = Gtk.Grid()
        settingsexpander.add(grid)
        row = 0
        col = 0
        
        l = Gtk.Label(label='Plot type:'); l.set_alignment(0, 0.5)
        grid.attach(l, 2 * col, row, 1, 1)
        self._plottype_combo = Gtk.ComboBoxText()
        grid.attach(self._plottype_combo, 2 * col + 1, row, 1, 1)
        self._plottype_combo.append_text('Double linear')
        self._plottype_combo.append_text('Logarithmic x')
        self._plottype_combo.append_text('Logarithmic y')
        self._plottype_combo.append_text('Double logarithmic')
        self._plottype_combo.append_text('Guinier')
        self._plottype_combo.set_active(3)
        self._plottype_combo.set_hexpand(True)
        self._plottype_combo.connect('changed', self._on_plottype_changed)
        row += 1
        
        l = Gtk.Label(label='X axis title:'); l.set_alignment(0, 0.5)
        grid.attach(l, 2 * col, row, 1, 1)
        self._xtitle_entry = Gtk.ComboBoxText.new_with_entry()
        self._xtitle_entry.append_text(u'q ('+libconfig.qunit()+')'.encode('utf-8'))
        self._xtitle_entry.append_text('Pixel')
        self._xtitle_entry.connect('editing-done', lambda cb:self.set_xlabel(cb.get_active_text().decode('utf-8')))
        self._xtitle_entry.connect('changed', lambda cb:self.set_xlabel(cb.get_active_text().decode('utf-8')))
        self._xtitle_entry.set_hexpand(True)
        grid.attach(self._xtitle_entry, 2 * col + 1, row, 1, 1)
        row += 1

        l = Gtk.Label(label='Y axis title:'); l.set_alignment(0, 0.5)
        grid.attach(l, 2 * col, row, 1, 1)
        self._ytitle_entry = Gtk.ComboBoxText.new_with_entry()
        self._ytitle_entry.append_text(u'Intensity (1/cm)'.encode('utf-8'))
        self._ytitle_entry.append_text('Relative intensity (arb. units)')
        self._ytitle_entry.append_text(r'$d\sigma/d\Omega$ (1/cm)')
        self._ytitle_entry.connect('editing-done', lambda cb:self.set_ylabel(cb.get_active_text().decode('utf-8')))
        self._ytitle_entry.connect('changed', lambda cb:self.set_ylabel(cb.get_active_text().decode('utf-8')))
        self._ytitle_entry.set_hexpand(True)
        grid.attach(self._ytitle_entry, 2 * col + 1, row, 1, 1)
        row += 1

        
        l = Gtk.Label(label='Title:'); l.set_alignment(0, 0.5)
        grid.attach(l, 2 * col, row, 1, 1)
        self._title_entry = Gtk.Entry()
        self._title_entry.connect('changed', lambda cb:self.set_title(cb.get_active_text().decode('utf-8')))
        grid.attach(self._title_entry, 2 * col + 1, row, 1, 1)
        row = 0
        col += 1

        self._hold_cb = Gtk.CheckButton(label='Hold mode')
        grid.attach(self._hold_cb, 2 * col, row, 2, 1)
        row += 1
        
        self._errorbars_cb = Gtk.CheckButton(label='Error bars')
        grid.attach(self._errorbars_cb, 2 * col, row, 2, 1)
        self._errorbars_cb.connect('toggled', lambda cb: self._replot_curves())
        row += 1
        
        self._legend_cb = Gtk.CheckButton(label='Show legend')
        grid.attach(self._legend_cb, 2 * col, row, 2, 1)
        self._legend_cb.connect('toggled', lambda cb: self._replot_curves())
        row += 1
        
        self._majorgrid_cb = Gtk.CheckButton(label='Major grid')
        grid.attach(self._majorgrid_cb, 2 * col, row, 2, 1)
        self._majorgrid_cb.connect('toggled', lambda cb:(self.gca().grid(cb.get_active(), 'major'), self.draw()))
        row += 1

        self._minorgrid_cb = Gtk.CheckButton(label='Minor grid')
        grid.attach(self._minorgrid_cb, 2 * col, row, 2, 1)
        self._minorgrid_cb.connect('toggled', lambda cb:(self.gca().grid(cb.get_active(), 'minor'), self.draw()))
        row += 1

        
        self.fig = Figure(figsize=(0.2, 0.2), dpi=72)
        self.canvas = FigureCanvasGTK3Agg(self.fig)
        vbox_fig.pack_start(self.canvas, True, True, 0)
        tb = NavigationToolbar2GTK3(self.canvas, None)
        vbox_fig.pack_start(tb, False, True, 0)

        tbutton = Gtk.ToolButton(Gtk.STOCK_CLEAR)
        tbutton.connect('clicked', lambda tbutton:self.cla())
        tb.insert(tbutton, 0)
        tbutton = Gtk.ToolButton(Gtk.STOCK_REFRESH)
        tbutton.connect('clicked', lambda tbutton:self._replot_curves())
        tb.insert(tbutton, 0)
        
    def _on_plottype_changed(self, combo):
        if combo.get_active_text() == 'Double linear':
            self.gca().set_xscale('linear')
            self.gca().set_yscale('linear')
        elif combo.get_active_text() == 'Logarithmic x':
            self.gca().set_xscale('log')
            self.gca().set_yscale('linear')
        elif combo.get_active_text() == 'Logarithmic y':
            self.gca().set_xscale('linear')
            self.gca().set_yscale('log')
        elif combo.get_active_text() == 'Double logarithmic':
            self.gca().set_xscale('log')
            self.gca().set_yscale('log')
        elif combo.get_active_text() == 'Guinier':
            self.gca().set_xscale('power', exponent=2)
            self.gca().set_yscale('log')
        else:
            raise NotImplementedError("*" + str(combo.get_active_text()) + "*")
        self.draw()
        return False
    
    def gca(self):
        return self.fig.gca()
    def add_curve(self, *args, **kwargs):
        if not self._hold_cb.get_active():
            self.cla()
        kwargs.update(self._curvestyles[len(self._curves)])
        if args and isinstance(args[0], sastool.classes.GeneralCurve):
            if self._errorbars_cb.get_active():
                return self.add_curve_with_errorbar(*args, **kwargs)
            kwargs['axes'] = self.gca()
            ret = args[0].plot(*args[1:], **kwargs)
            self._curves.append(args[0])
        else:
            ret = self.gca().plot(*args, **kwargs)
            self._curves.extend([sastool.classes.GeneralCurve(x.get_xdata(), x.get_ydata()) for x in ret if isinstance(x, Line2D)])
        if self._legend_cb.get_active():
            self.legend()
        self._on_plottype_changed(self._plottype_combo)
        return ret
    def plot(self, *args, **kwargs):
        self._plottype_combo.set_active(0)
        self.add_curve(*args, **kwargs)
    def loglog(self, *args, **kwargs):
        self._plottype_combo.set_active(3)
        self.add_curve(*args, **kwargs)
    def guinier(self, *args, **kwargs):
        self._plottype_combo.set_active(4)
        self.add_curve(*args, **kwargs)
    def add_curve_with_errorbar(self, *args, **kwargs):
        if not self._hold_cb.get_active():
            self.cla()
        kwargs.update(self._curvestyles[len(self._curves)])
        if args and isinstance(args[0], sastool.classes.GeneralCurve):
            if not self._errorbars_cb.get_active():
                return self.add_curve(*args, **kwargs)
            kwargs['axes'] = self.gca()
            ret = args[0].errorbar(*args[1:], **kwargs)
            self._curves.append(args[0])
        else:
            ret = self.gca().errorbar(*args, **kwargs)
            x = ret[0].get_xdata()
            y = ret[0].get_ydata()
            if len(ret[1]) == 4:
                # both x and y error bars were given
                xerr = 0.5 * (ret[1][1].get_xdata() - ret[1][0].get_xdata())
                yerr = 0.5 * (ret[1][3].get_ydata() - ret[1][2].get_ydata())
            elif len(ret[1]) == 2:
                xerr = 0.5 * (ret[1][1].get_xdata() - ret[1][0].get_xdata())
                yerr = 0.5 * (ret[1][1].get_ydata() - ret[1][0].get_ydata())
            else:
                xerr = np.zeros_like(x)
                yerr = np.zeros_like(y)
            self._curves.append(sastool.classes.GeneralCurve(x, y, dx=xerr, dy=yerr))
        if self._legend_cb.get_active():
            self.legend()
        self._on_plottype_changed(self._plottype_combo)
        return ret
    def errorbar(self, *args, **kwargs):
        self.add_curve_with_errorbar(*args, **kwargs)
    def semilogy(self, *args, **kwargs):
        self._plottype_combo.set_active(2)
        self.add_curve(*args, **kwargs)
    def semilogx(self, *args, **kwargs):
        self._plottype_combo.set_active(1)
        self.add_curve(*args, **kwargs)
    def draw(self):
        return self.canvas.draw()
    def cla(self, *args, **kwargs):
        self._curves = []
        self.gca().clear(*args, **kwargs)
        self.gca().grid(self._majorgrid_cb.get_active(), 'major')
        self.gca().grid(self._minorgrid_cb.get_active(), 'minor')
        self.draw()
    def legend(self, *args, **kwargs):
        self.gca().legend(*args, **kwargs)
        self.draw()
    def text(self, *args, **kwargs):
        self.gca().text(*args, **kwargs)
        self.draw()
    def figtext(self, *args, **kwargs):
        self.figure.text(*args, **kwargs)
        self.draw()
    def set_title(self, *args, **kwargs):
        self.gca().title(*args, **kwargs)
        self.draw()
    def set_xlabel(self, *args, **kwargs):
        self.gca().set_xlabel(*args, **kwargs)
        self.draw()
    def set_ylabel(self, *args, **kwargs):
        self.gca().set_ylabel(*args, **kwargs)
        self.draw()
    def axis(self, *args, **kwargs):
        return self.gca().axis(*args, **kwargs)
    def _replot_curves(self):
        curves = self._curves[:]
        self.cla()
        hold_before = self._hold_cb.get_active()
        self._hold_cb.set_active(True)
        try:
            for c in curves:
                if self._errorbars_cb.get_active():
                    self.add_curve_with_errorbar(c)
                else:
                    self.add_curve(c)
        finally:
            self._hold_cb.set_active(hold_before)
        if self._legend_cb.get_active():
            self.legend()
        self._on_plottype_changed(self._plottype_combo)
        
class PlotSASCurveWindow(Gtk.Dialog):
    __gtype_name__ = 'SASGUI_PlotSASCurveWindow'
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
    def add_curve(self, *args, **kwargs):
        return self.plotsascurve.add_curve(*args, **kwargs)
    def add_curve_with_errorbar(self, *args, **kwargs):
        return self.plotsascurve.add_curve_with_errorbar(*args, **kwargs)
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
        return self.plotsascurve.set_title(*args, **kwargs)
    def set_xlabel(self, *args, **kwargs):
        return self.plotsascurve.set_xlabel(*args, **kwargs)
    def set_ylabel(self, *args, **kwargs):
        return self.plotsascurve.set_ylabel(*args, **kwargs)
    def axis(self, *args, **kwargs):
        return self.plotsascurve.axis(*args, **kwargs)
