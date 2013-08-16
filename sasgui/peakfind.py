from gi.repository import Gtk
import sastool
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3
import numpy as np

__all__ = ['PeakFind', 'PeakFindDialog']

class PeakFind(Gtk.Paned):
    __gtype_name__ = 'SASGUI_PeakFind'
    def __init__(self):
        Gtk.Paned.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)
        self.xdata = None
        self.ydata = None
        self.dydata = None
        paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.add1(paned)
        vbfig = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add2(vbfig)
        self.fig = Figure()
        self.figcanvas = FigureCanvasGTK3Agg(self.fig)
        vbfig.pack_start(self.figcanvas, True, True, 0)
        self.figtoolbar = NavigationToolbar2GTK3(self.figcanvas, None)
        vbfig.pack_start(self.figtoolbar, False, True, 0)
        self.figcanvas.set_size_request(640, 480)
        f = Gtk.Expander(label='Peaks')
        f.set_expanded(True)
        paned.add1(f)
        vb1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        f.add(vb1)
        sw = Gtk.ScrolledWindow()
        sw.set_size_request(200, 100)
        vb1.pack_start(sw, True, True, 0)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        # columns in peaks_list: peak and fit data, pos, dpos, height, dheight, is_autoadded, relative_pos_to_first
        self.peaks_list = Gtk.ListStore(object, float, float, float, float, bool, float)
        self.peaks_view = Gtk.TreeView(self.peaks_list)
        sw.add(self.peaks_view)
        self.peaks_view.set_rules_hint(True)
        self.peaks_view.get_selection().set_mode(Gtk.SelectionMode.BROWSE)
        self.peaks_view.append_column(Gtk.TreeViewColumn('Pos.', Gtk.CellRendererText(), text=1))
        self.peaks_view.append_column(Gtk.TreeViewColumn('DPos.', Gtk.CellRendererText(), text=2))
        self.peaks_view.append_column(Gtk.TreeViewColumn('Height.', Gtk.CellRendererText(), text=3))
        self.peaks_view.append_column(Gtk.TreeViewColumn('DHeight.', Gtk.CellRendererText(), text=4))
        self.peaks_view.append_column(Gtk.TreeViewColumn('Rel. pos.', Gtk.CellRendererText(), text=6))
        hbb = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        vb1.pack_start(hbb, False, True, 0)
        b = Gtk.Button(stock=Gtk.STOCK_REMOVE)
        hbb.add(b)
        b.connect('clicked', lambda button:self.remove_peak())
        b = Gtk.Button(stock=Gtk.STOCK_CLEAR)
        hbb.add(b)
        b.connect('clicked', lambda button:self.clear_peaklist())
        
        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        paned.add2(vb)
        f = Gtk.Expander(label='Fit single peak')
        vb.pack_start(f, False, False, 0)
        vb1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        f.add(vb1)
        tab = Gtk.Table()
        vb1.pack_start(tab, False, False, 0)
        row = 0
        l = Gtk.Label('Peak function:'); l.set_alignment(Gtk.Align.START, Gtk.Align.CENTER)
        tab.attach(l, 0, 1, row, row + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.fit_function_combo = Gtk.ComboBoxText()
        self.fit_function_combo.append_text('Gaussian')
        self.fit_function_combo.append_text('Lorentzian')
        self.fit_function_combo.set_active(1)
        tab.attach(self.fit_function_combo, 1, 2, row, row + 1)
        row += 1
        self.fit_position_cb = Gtk.CheckButton(label='Position:')
        self.fit_position_cb.set_alignment(Gtk.Align.START, Gtk.Align.CENTER)
        tab.attach(self.fit_position_cb, 0, 1, row, row + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.fit_position_entry = Gtk.Entry()
        tab.attach(self.fit_position_entry, 1, 2, row, row + 1)
        row += 1
        self.fit_hwhm_cb = Gtk.CheckButton(label='Sigma:')
        self.fit_hwhm_cb.set_alignment(Gtk.Align.START, Gtk.Align.CENTER)
        tab.attach(self.fit_hwhm_cb, 0, 1, row, row + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.fit_hwhm_entry = Gtk.Entry()
        tab.attach(self.fit_hwhm_entry, 1, 2, row, row + 1)
        row += 1
        self.fit_amplitude_cb = Gtk.CheckButton(label='Amplitude:')
        self.fit_amplitude_cb.set_alignment(Gtk.Align.START, Gtk.Align.CENTER)
        tab.attach(self.fit_amplitude_cb, 0, 1, row, row + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.fit_amplitude_entry = Gtk.Entry()
        tab.attach(self.fit_amplitude_entry, 1, 2, row, row + 1)
        row += 1
        self.fit_baseline_cb = Gtk.CheckButton(label='Baseline:')
        self.fit_baseline_cb.set_alignment(Gtk.Align.START, Gtk.Align.CENTER)
        tab.attach(self.fit_baseline_cb, 0, 1, row, row + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.fit_baseline_entry = Gtk.Entry()
        tab.attach(self.fit_baseline_entry, 1, 2, row, row + 1)
        row += 1
        b = Gtk.Button(stock=Gtk.STOCK_EXECUTE)
        vb1.pack_start(b, False, True, 0)
        b.connect('clicked', lambda button:self.autofind_single())
        for cb, entry in [(self.fit_amplitude_cb, self.fit_amplitude_entry),
                         (self.fit_baseline_cb, self.fit_baseline_entry),
                         (self.fit_position_cb, self.fit_position_entry),
                         (self.fit_hwhm_cb, self.fit_hwhm_entry)]:
            cb.connect('toggled', self.on_paired_cb_entry, entry)
            self.on_paired_cb_entry(cb, entry)

        f = Gtk.Expander(label='Find multiple peaks')
        vb.pack_start(f, False, False, 0)
        vb1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        f.add(vb1)
        tab = Gtk.Table()
        vb1.pack_start(tab, False, False, 0)
        row = 0
        l = Gtk.Label('Peak function:'); l.set_alignment(Gtk.Align.START, Gtk.Align.CENTER)
        tab.attach(l, 0, 1, row, row + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.multi_function_combo = Gtk.ComboBoxText()
        self.multi_function_combo.append_text('Gaussian')
        self.multi_function_combo.append_text('Lorentzian')
        self.multi_function_combo.set_active(1)
        tab.attach(self.multi_function_combo, 1, 2, row, row + 1)
        row += 1
        l = Gtk.Label('# of neighbours on each side:'); l.set_alignment(Gtk.Align.START, Gtk.Align.CENTER)
        tab.attach(l, 0, 1, row, row + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.multi_N_entry = Gtk.SpinButton(adjustment=Gtk.Adjustment(5, 2, 1e6, 1, 10), digits=0)
        tab.attach(self.multi_N_entry, 1, 2, row, row + 1)
        row += 1
        l = Gtk.Label('# of tolerated outliers:'); l.set_alignment(Gtk.Align.START, Gtk.Align.CENTER)
        tab.attach(l, 0, 1, row, row + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.multi_Ntol_entry = Gtk.SpinButton(adjustment=Gtk.Adjustment(0, 0, 1e6, 1, 10), digits=0)
        tab.attach(self.multi_Ntol_entry, 1, 2, row, row + 1)
        row += 1
        l = Gtk.Label('# of neighbours for LSQ fit:'); l.set_alignment(Gtk.Align.START, Gtk.Align.CENTER)
        tab.attach(l, 0, 1, row, row + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.multi_Nfit_entry = Gtk.SpinButton(adjustment=Gtk.Adjustment(5, 2, 1e6, 1, 10), digits=0)
        tab.attach(self.multi_Nfit_entry, 1, 2, row, row + 1)
        row += 1
        b = Gtk.Button(stock=Gtk.STOCK_EXECUTE)
        vb1.pack_start(b, False, True, 0)
        b.connect('clicked', lambda button:self.autofind_multiple())
        
        f = Gtk.Expander(label='Plotting')
        vb.pack_start(f, False, False, 0)
        vb1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        f.add(vb1)
        tab = Gtk.Table()
        vb1.pack_start(tab, False, False, 0)
        row = 0
        self.xscale_log = Gtk.CheckButton(label='Logarithmic X-scale')
        self.xscale_log.set_alignment(Gtk.Align.START, Gtk.Align.CENTER)
        tab.attach(self.xscale_log, 0, 1, row, row + 1)
        row += 1
        self.yscale_log = Gtk.CheckButton(label='Logarithmic Y-scale')
        self.yscale_log.set_alignment(Gtk.Align.START, Gtk.Align.CENTER)
        tab.attach(self.yscale_log, 0, 1, row, row + 1)
        row += 1
        self.xscale_log.connect('toggled', self.redraw_curves)
        self.yscale_log.connect('toggled', self.redraw_curves)
        self.show_all()
    def redraw_curves(self, checkbutton=None):
        if checkbutton is not None:
            scale = ['linear', 'log'][int(checkbutton.get_active())]
            if checkbutton == self.xscale_log:
                self.fig.gca().set_xscale(scale)
            elif checkbutton == self.yscale_log:
                self.fig.gca().set_yscale(scale)
            self.figcanvas.draw()
            return
        self.fig.gca().clear()
        self.fig.gca().errorbar(self.xdata, self.ydata, self.dydata, None, 'b-')
        for row in self.peaks_list:
            self.fig.gca().plot(row[0]['x'], row[0]['y'], 'r-')
        if self.xscale_log.get_active():
            self.fig.gca().set_xscale('log')
        if self.yscale_log.get_active():
            self.fig.gca().set_yscale('log')
        self.figcanvas.draw()
        
    def on_paired_cb_entry(self, checkbutton, entry):
        entry.set_sensitive(checkbutton.get_active())
    def autofind_multiple(self):
        if any(x is None for x in (self.xdata, self.ydata)):
            return
        ax = self.fig.gca().axis()
        xmin = min(ax[:2]); xmax = max(ax[:2])
        ymin = min(ax[2:]); ymax = max(ax[2:])
        idx = (self.xdata >= xmin) & (self.ydata >= ymin) & (self.xdata <= xmax) & (self.ydata <= ymax)
        x = self.xdata[idx]; y = self.ydata[idx];
        if self.dydata is not None:
            dy = self.dydata[idx]
        else:
            dy = None
        for pos, hwhm, baseline, ampl in zip(*sastool.misc.basicfit.findpeak_multi(x, y, dy, self.multi_N_entry.get_value_as_int(),
                                             self.multi_Ntol_entry.get_value_as_int(),
                                             self.multi_Nfit_entry.get_value_as_int(),
                                             self.multi_function_combo.get_active_text())):
            height = baseline + ampl
            peakidx = np.absolute(x - pos.val).argmin()
            peakx = x[max(0, peakidx - self.multi_Nfit_entry.get_value_as_int()):min(peakidx + self.multi_Nfit_entry.get_value_as_int(), len(x))]
            if self.multi_function_combo.get_active_text() == 'Gaussian':
                peaky = sastool.fitting.Gaussian(peakx, ampl, pos, hwhm, baseline)
            else:
                peaky = sastool.fitting.Lorentzian(peakx, ampl, pos, hwhm, baseline)
            peakdata = {'pos':pos, 'hwhm':hwhm, 'baseline':baseline, 'ampl':ampl, 'x':peakx, 'y':peaky}
            self.peaks_list.append((peakdata, pos.val, pos.err, height.val, height.err, True, 0.0))
        self.reorder_peaks()
        self.redraw_curves()
    def autofind_single(self):
        if any(x is None for x in (self.xdata, self.ydata)):
            return
        ax = self.fig.gca().axis()
        xmin = min(ax[:2]); xmax = max(ax[:2])
        ymin = min(ax[2:]); ymax = max(ax[2:])
        idx = (self.xdata >= xmin) & (self.ydata >= ymin) & (self.xdata <= xmax) & (self.ydata <= ymax)
        x = self.xdata[idx]; y = self.ydata[idx];
        if self.dydata is not None:
            dy = self.dydata[idx]
        else:
            dy = None
        kwargs_to_findpeak = {'curve':self.fit_function_combo.get_active_text()}
        for name in ['position', 'hwhm', 'baseline', 'amplitude']:
            if self.__getattribute__('fit_' + name + '_cb').get_active():
                kwargs_to_findpeak[name] = sastool.fitting.FixedParameter(self.__getattribute__('fit_' + name + '_entry'))
        pos, hwhm, baseline, ampl = sastool.misc.basicfit.findpeak_single(x, y, dy, **kwargs_to_findpeak)
        height = baseline + ampl
        if self.fit_function_combo.get_active_text() == 'Gaussian':
            peaky = sastool.fitting.Gaussian(x, ampl, pos, hwhm, baseline)
        else:
            peaky = sastool.fitting.Lorentzian(x, ampl, pos, hwhm, baseline)
        peakdata = {'pos':pos, 'hwhm':hwhm, 'baseline':baseline, 'ampl':ampl, 'x':x, 'y':peaky}
        self.peaks_view.get_selection().select_iter(self.peaks_list.append((peakdata, pos.val, pos.err, height.val, height.err, False, 0.0)))
        self.reorder_peaks()
        self.fit_amplitude_entry.set_text(str(ampl.val))
        self.fit_baseline_entry.set_text(str(baseline.val))
        self.fit_hwhm_entry.set_text(str(hwhm.val))
        self.fit_position_entry.set_text(str(pos.val))
        self.redraw_curves()
    def remove_peak(self):
        model, it = self.peaks_view.get_selection().get_selected()
        if it is not None:
            model.remove(it)
        self.reorder_peaks()
        self.redraw_curves()
    def clear_peaklist(self):
        self.peaks_list.clear()
        self.redraw_curves()
    def reorder_peaks(self):
        peaks = []
        model, selected = self.peaks_view.get_selection().get_selected()
        it = self.peaks_list.get_iter_first()
        while True:
            peaks.append(tuple(self.peaks_list[it]) + (it == selected,))
            it = self.peaks_list.iter_next(it)
            if it is None:
                break
        peaks = sorted(peaks, key=lambda x:x[1])
        self.peaks_list.clear()
        for p in peaks:
            it = self.peaks_list.append(p[:-1])
            self.peaks_list[-1][-1] = self.peaks_list[-1][1] / self.peaks_list[0][1]
            if p[-1]:
                self.peaks_view.get_selection().select_iter(it)
        return True
    def set_data(self, x, y, dy=None):
        x = np.array(x)
        y = np.array(y)
        if not len(x) == len(y):
            raise ValueError('Length discrepancy between x and y data.')
        if dy is not None:
            dy = np.array(dy)
            if not len(dy) == len(x):
                raise ValueError('Length discrepancy between x and dy data.')
        self.xdata = x
        self.ydata = y
        self.dydata = dy
        self.peaks_list.clear()
        self.redraw_curves()
        
class PeakFindDialog(Gtk.Dialog):
    __gtype_name__ = 'SASGUI_PeakFindDialog'
    def __init__(self, title='Find peaks...', parent=None, flags=Gtk.DialogFlags.DESTROY_WITH_PARENT, buttons=(Gtk.STOCK_OK, Gtk.ResponseType.OK)):
        Gtk.Dialog.__init__(self, title, parent, flags, buttons)
        ca = self.get_content_area()
        self.peakfind = PeakFind()
        ca.pack_start(self.peakfind, True, True, 0)
        ca.show_all()
    def set_data(self, x, y, dy=None):
        return self.peakfind.set_data(x, y, dy)
