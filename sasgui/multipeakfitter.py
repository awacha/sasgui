import sastool
import os
from gi.repository import Gtk
from gi.repository import GObject
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg
from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3
from matplotlib.figure import Figure
from .fileentry import FileEntryWithButton
import numpy as np

__all__ = ['MultiPeakFitter']


class MultiPeakFitter(Gtk.Dialog):

    def __init__(self, title, parent=None, flags=Gtk.DialogFlags.DESTROY_WITH_PARENT, buttons=(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)):
        Gtk.Dialog.__init__(self, title, parent, flags, buttons)
        self._fig = Figure()
        self._figcanvas = FigureCanvasGTK3Agg(self._fig)
        self._figcanvas.set_size_request(640, 480)
        hb = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.get_content_area().pack_start(hb, True, True, 0)
        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hb.pack1(vb, True, False)
        vb.pack_start(self._figcanvas, True, True, 0)
        vb.pack_start(
            NavigationToolbar2GTK3(self._figcanvas, self), False, False, 0)

        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hb.pack2(vb, True, False)
        grid = Gtk.Grid()
        # grid.set_row_homogeneous(True)
        vb.pack_start(grid, False, False, 0)
        row = 0

        l = Gtk.Label('File name:')
        l.set_alignment(0, 0.5)
        grid.attach(l, 0, row, 1, 1)
        self._filename_entry = FileEntryWithButton(
            fileformats=[('ASCII Text files', '*.txt'), ('DAT files', '*.dat')])
        self._filename_entry.connect('changed', self._on_file_selected)
        grid.attach(self._filename_entry, 1, row, 1, 1)
        row += 1

        self._logx_checkbutton = Gtk.CheckButton(label='Logarithmic X')
        self._logx_checkbutton.set_alignment(0, 0.5)
        grid.attach(self._logx_checkbutton, 0, row, 2, 1)
        self._logx_checkbutton.connect(
            'toggled', lambda cb: self._plot_curve())
        row += 1

        self._logy_checkbutton = Gtk.CheckButton(label='Logarithmic Y')
        self._logy_checkbutton.set_alignment(0, 0.5)
        grid.attach(self._logy_checkbutton, 0, row, 2, 1)
        self._logy_checkbutton.connect(
            'toggled', lambda cb: self._plot_curve())
        row += 1

        l = Gtk.Label('Peak function:')
        l.set_alignment(0, 0.5)
        grid.attach(l, 0, row, 1, 1)
        self._peakfunc_combo = Gtk.ComboBoxText()
        grid.attach(self._peakfunc_combo, 1, row, 1, 1)
        self._peakfunc_combo.append_text('Lorentzian')
        self._peakfunc_combo.append_text('Gaussian')
        self._peakfunc_combo.set_active(0)
        row += 1

        l = Gtk.Label('# of increase & decrease:')
        l.set_alignment(0, 0.5)
        grid.attach(l, 0, row, 1, 1)
        self._N_spin = Gtk.SpinButton(
            adjustment=Gtk.Adjustment(10, 1, 1e6, 1, 10), digits=0)
        self._N_spin.set_value(10)
        grid.attach(self._N_spin, 1, row, 1, 1)
        row += 1

        l = Gtk.Label('# of tolerance:')
        l.set_alignment(0, 0.5)
        grid.attach(l, 0, row, 1, 1)
        self._Ntol_spin = Gtk.SpinButton(
            adjustment=Gtk.Adjustment(0, 0, 1e6, 1, 10), digits=0)
        self._Ntol_spin.set_value(0)
        grid.attach(self._Ntol_spin, 1, row, 1, 1)
        row += 1

        self._filter_R2_below_checkbutton = Gtk.CheckButton(
            label='Filter peaks where R2 is below:')
        self._filter_R2_below_checkbutton.set_alignment(0, 0.5)
        grid.attach(self._filter_R2_below_checkbutton, 0, row, 1, 1)
        self._filter_R2_below_spin = Gtk.SpinButton(
            adjustment=Gtk.Adjustment(0.9, 0, 1, 0.01, 0.1), digits=5)
        self._filter_R2_below_spin.set_value(0.9)
        self._filter_R2_below_checkbutton.connect(
            'toggled', lambda cb: self._filter_R2_below_spin.set_sensitive(cb.get_active()))
        self._filter_R2_below_spin.set_sensitive(
            self._filter_R2_below_checkbutton.get_active())
        grid.attach(self._filter_R2_below_spin, 1, row, 1, 1)
        row += 1

        self._fullprecision_checkbutton = Gtk.CheckButton(
            label='Give results in full precision')
        self._fullprecision_checkbutton.set_alignment(0, 0.5)
        grid.attach(self._fullprecision_checkbutton, 0, row, 2, 1)
        self._fullprecision_checkbutton.connect(
            'toggled', lambda cb: self._update_table())
        row += 1

        self._relativepos_checkbutton = Gtk.CheckButton(
            label='Display relative positions')
        self._relativepos_checkbutton.set_alignment(0, 0.5)
        grid.attach(self._relativepos_checkbutton, 0, row, 2, 1)
        self._relativepos_checkbutton.connect('toggled', lambda cb: self._realposition_checkbutton.set_active(
            False) or self._realposition_checkbutton.set_sensitive(not cb.get_active()) or self._update_table())
        row += 1

        self._relativeintensity_checkbutton = Gtk.CheckButton(
            label='Display relative intensities')
        self._relativeintensity_checkbutton.set_alignment(0, 0.5)
        grid.attach(self._relativeintensity_checkbutton, 0, row, 2, 1)
        self._relativeintensity_checkbutton.connect(
            'toggled', lambda cb: self._update_table())
        row += 1

        self._realposition_checkbutton = Gtk.CheckButton(
            label='Give position in real space')
        self._realposition_checkbutton.set_alignment(0, 0.5)
        grid.attach(self._realposition_checkbutton, 0, row, 2, 1)
        self._realposition_checkbutton.connect('toggled', lambda cb: self._peakview.get_column(
            0).set_title(['Position', '2pi/position'][cb.get_active()]) or self._update_table())
        row += 1

        bbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        grid.attach(bbox, 0, row, 2, 1)
        row += 1

        b = Gtk.Button('(Re)plot')
        bbox.pack_start(b, True, True, 0)
        b.connect('clicked', lambda b: self._plot_fitted())

        b = Gtk.Button('Find peaks')
        bbox.pack_start(b, True, True, 0)
        b.connect('clicked', self._on_find_peaks)

        b = Gtk.Button('Fit single')
        bbox.pack_start(b, True, True, 0)
        b.connect('clicked', lambda b: self._fit_single())

        b = Gtk.Button('Remove selected')
        bbox.pack_start(b, True, True, 0)
        b.connect('clicked', lambda b: self._remove_selected())

        b = Gtk.Button('Save peak data')
        bbox.pack_start(b, True, True, 0)
        b.connect('clicked', lambda b: self._save_peakdata(None))

        # peak data, position, full height, hwhm, baseline, amplitude, R2,
        # Chi2, DoF
        self._peakstore = Gtk.ListStore(GObject.TYPE_PYOBJECT, GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_STRING,
                                        GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_FLOAT, GObject.TYPE_FLOAT, GObject.TYPE_INT)
        self._peakview = Gtk.TreeView(self._peakstore)
        self._peakview.append_column(
            Gtk.TreeViewColumn('Position', Gtk.CellRendererText(), text=1))
        self._peakview.append_column(
            Gtk.TreeViewColumn('Full height', Gtk.CellRendererText(), text=2))
        self._peakview.append_column(
            Gtk.TreeViewColumn('HWHM', Gtk.CellRendererText(), text=3))
        self._peakview.append_column(
            Gtk.TreeViewColumn('Baseline', Gtk.CellRendererText(), text=4))
        self._peakview.append_column(
            Gtk.TreeViewColumn('Amplitude', Gtk.CellRendererText(), text=5))
        self._peakview.append_column(
            Gtk.TreeViewColumn('Adjusted R2', Gtk.CellRendererText(), text=6))
        self._peakview.append_column(
            Gtk.TreeViewColumn('Reduced Chi2', Gtk.CellRendererText(), text=7))
        self._peakview.append_column(
            Gtk.TreeViewColumn('DoF', Gtk.CellRendererText(), text=8))
        self._peakview.set_headers_visible(True)
        self._peakview.set_rules_hint(True)

        sw = Gtk.ScrolledWindow()
        vb.pack_start(sw, True, True, 0)
        sw.add(self._peakview)
        self.show_all()
        self.hide()

    def _fit_single(self):
        c = self._curve.trimzoomed()
        pos, hwhm, offset, amplitude, stat = sastool.misc.basicfit.findpeak_single(
            c.x, c.y, c.dy, curve=self._peakfunc_combo.get_active_text(), return_stat=True)
        it = self._peakstore.get_iter_first()
        while it is not None:
            if float(pos) < float(self._peakstore[it][0][0]):
                break
            it = self._peakstore.iter_next(it)
        self._peakstore.insert_before(
            it, [(pos, hwhm, offset, amplitude, c.x, stat), '', '', '', '', '', 0.0, 0.0, 0])
        self._update_table()
        self._plot_fitted()

    def _remove_selected(self):
        model, sel = self._peakview.get_selection().get_selected()
        if sel is not None:
            model.remove(sel)
        self._plot_fitted()

    def _on_find_peaks(self, button):
        c = self._curve.trimzoomed()
        self._findpeaks_data = {'N': self._N_spin.get_value_as_int(),
                                'Ntol': self._Ntol_spin.get_value_as_int(),
                                'curve': self._peakfunc_combo.get_active_text()
                                }

        pos, hwhm, offset, amplitude, xfit, stat = sastool.misc.basicfit.findpeak_multi(c.x, c.y, c.dy, self._N_spin.get_value_as_int(
        ), self._Ntol_spin.get_value_as_int(), curve=self._peakfunc_combo.get_active_text(), return_xfit=True, return_stat=True)
        self._peakstore.clear()
        if self._filter_R2_below_checkbutton.get_active():
            R2_min = self._filter_R2_below_spin.get_value()
        else:
            R2_min = 0
        for p, h, o, a, x, s in zip(pos, hwhm, offset, amplitude, xfit, stat):
            if s['R2'] >= R2_min:
                self._peakstore.append(
                    [(p, h, o, a, x, s), '', '', '', '', '', 0.0, 0.0, 0])
        self._update_table()
        self._plot_fitted()

    def _plot_fitted(self):
        self._plot_curve()
        for row in self._peakstore:
            p, h, o, a, x, s = row[0]
            x = np.linspace(x.min(), x.max(), 5 * len(x))
            if self._peakfunc_combo.get_active_text().startswith('Lorentz'):
                y = a * h ** 2 / (h ** 2 + (p - x) ** 2) + o
            else:
                y = a * np.exp(-0.5 * (x - p) ** 2 / h ** 2) + o
            self._fig.gca().plot(x, y, 'r-')
        self._figcanvas.draw()

    def _update_table(self):
        if self._fullprecision_checkbutton.get_active():
            tostrfunc = lambda x: ('%g \xb1 %g' % (x.val, x.err))
        else:
            tostrfunc = str(x, encoding='utf-8')
        first = True
        for row in self._peakstore:
            if self._relativepos_checkbutton.get_active():
                if first:
                    row[1] = '1'
                else:
                    row[1] = tostrfunc(row[0][0] / self._peakstore[0][0][0])
            elif self._realposition_checkbutton.get_active():
                row[1] = tostrfunc(2 * np.pi / row[0][0])
            else:
                row[1] = tostrfunc(row[0][0])
            if self._relativeintensity_checkbutton.get_active():
                if first:
                    row[2] = '1'
                else:
                    row[2] = tostrfunc(
                        (row[0][2] + row[0][3]) / (self._peakstore[0][0][2] + self._peakstore[0][0][3]))
            else:
                row[2] = tostrfunc(row[0][2] + row[0][3])
            row[3] = tostrfunc(row[0][1])
            row[4] = tostrfunc(row[0][2])
            row[5] = tostrfunc(row[0][3])
            row[6] = row[0][5]['R2']
            row[7] = row[0][5]['Chi2_reduced']
            row[8] = row[0][5]['DoF']
            first = False

    def _on_file_selected(self, fileentrywithbutton):
        datafile = fileentrywithbutton.get_filename()
        self._curve = sastool.classes.SASCurve(datafile)
        self._filename = datafile
        self._plot_curve()
        self._peakstore.clear()

    def _plot_curve(self):
        if not hasattr(self, '_curve'):
            return
        self._fig.clf()
        ax = self._fig.gca()
        self._curve.plot('b.-', axes=ax)
        if self._logx_checkbutton.get_active():
            ax.set_xscale('log')
        else:
            ax.set_xscale('linear')
        if self._logy_checkbutton.get_active():
            ax.set_yscale('log')
        else:
            ax.set_yscale('linear')
        ax.set_xlabel('q')
        ax.set_ylabel('Intensity')
        ax.set_title(self._filename)
        self._figcanvas.draw()

    def _save_peakdata(self, filename=None):
        if filename is None:
            filename = os.path.splitext(self._filename)[0] + '.peaks'
            with open(filename, 'wt') as f:
                f.write('# Peaks found for dataset %s\n' % self._filename)
                f.write(
                    '# N: %(N)d\n# Ntol: %(Ntol)d\n# Peak function: %(curve)s\n' % self._findpeaks_data)
                f.write('# Peak data follows.\n')
                f.write(
                    '# Position\tPosition error\tFull height\tFull height error\tHWHM\tHWHM error\tOffset\tOffset error\tAmplitude\tAmplitude error\tR2\tReduced Chi2\tDegrees of freedom\n')
                for row in self._peakstore:
                    p, h, o, a, x, s = row[0]
                    f.write('%g\t%g\t%g\t%g\t%g\t%g\t%g\t%g\t%g\t%g\t%g\t%g\t%d\n' %
                            (p.val, p.err, (o + a).val, (o + a).err, h.val, h.err, o.val, o.err, a.val, a.err, s['R2'], s['Chi2_reduced'], s['DoF']))


def multipeakfitter_main():
    mpf = MultiPeakFitter('SASGui::Multi-peak fitting')
    mpf.show_all()
    mpf.connect('response', lambda mpf, respid: Gtk.main_quit())
    Gtk.main()
