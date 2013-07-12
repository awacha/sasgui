'''
Created on Sep 6, 2012

@author: andris
'''
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import Pango
import numpy as np
import os
from sastool.fitting import FixedParameter, nonlinear_leastsquares
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg 
from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3

__all__ = ['EnergyCalibrator', 'DistCalibrator', 'QCalibrator', 'run_energycalibrator', 'run_qcalibrator']

class Calibrator(Gtk.Dialog):
    '''
    A specialized Gtk.Dialog for configuring interpolation-like calibration.
    '''
    _xcolumnname = 'Uncalibrated'
    _ycolumnname = 'Calibrated'
    _title = 'Calibration'
    _fileextension = '.calib'
    _redrawing = False
    def __init__(self, title=None, parent=None, flags=0, buttons=None):
        '''
        Constructor
        '''
        if title is None:
            title = self._title
        Gtk.Dialog.__init__(self, title, parent, flags, buttons)
        uber_vbox = self.get_content_area()
        uber_hbox = Gtk.HBox()
        uber_vbox.pack_start(uber_hbox, True, True, 0)
        vbox = Gtk.VBox()
        uber_hbox.pack_start(vbox, False, True, 0)
        vbox_fig = Gtk.VBox()
        uber_hbox.pack_start(vbox_fig, True, True, 0)
        self.fig = Figure(figsize=(0.2, 0.2), dpi=72)
        self.canvas = FigureCanvasGTK3Agg(self.fig)
        self.canvas.set_size_request(300, 200)
        vbox_fig.pack_start(self.canvas, True, True, 0)
        tb = NavigationToolbar2GTK3(self.canvas, vbox_fig)
        vbox_fig.pack_start(tb, False, True, 0)

        hbox = Gtk.HBox()
        vbox.pack_start(hbox, True, True, 0)
        self.calibrationpairs = Gtk.ListStore(GObject.TYPE_DOUBLE, GObject.TYPE_DOUBLE)
        self.calibview = Gtk.TreeView(self.calibrationpairs)
        self.calibview.set_headers_visible(True)
        self.calibview.set_rules_hint(True)

        # self.calibview.set_fixed_height_mode(True)
        self.calibview.set_rubber_banding(True)

        uncrenderer = Gtk.CellRendererText()
        uncrenderer.set_property('editable', True)
        uncrenderer.connect('edited', self.on_cell_edited, 0)
        tvc = Gtk.TreeViewColumn(self._xcolumnname, uncrenderer, text=0)
        self.calibview.append_column(tvc)

        crenderer = Gtk.CellRendererText()
        crenderer.set_property('editable', True)
        crenderer.connect('edited', self.on_cell_edited, 1)
        tvc = Gtk.TreeViewColumn(self._ycolumnname, crenderer, text=1)
        self.calibview.append_column(tvc)
        self.calibview.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        sw = Gtk.ScrolledWindow()
        sw.add(self.calibview)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_size_request(*self.calibview.get_size_request())
        hbox.pack_start(sw, True, True, 0)
        buttonbox = Gtk.VButtonBox()
        hbox.pack_start(buttonbox, False, True, 0)
        b = Gtk.Button(stock=Gtk.STOCK_ADD)
        buttonbox.add(b)
        b.connect('clicked', self.on_buttonbox_clicked, 'add')
        b = Gtk.Button(stock=Gtk.STOCK_DELETE)
        buttonbox.add(b)
        b.connect('clicked', self.on_buttonbox_clicked, 'delete')
        b = Gtk.Button(stock=Gtk.STOCK_CLEAR)
        buttonbox.add(b)
        b.connect('clicked', self.on_buttonbox_clicked, 'clear')
        b = Gtk.Button(stock=Gtk.STOCK_SAVE_AS)
        buttonbox.add(b)
        b.connect('clicked', self.on_buttonbox_clicked, 'save')
        b = Gtk.Button(stock=Gtk.STOCK_OPEN)
        buttonbox.add(b)
        b.connect('clicked', self.on_buttonbox_clicked, 'open')
        b = Gtk.Button(stock=Gtk.STOCK_REFRESH)
        buttonbox.add(b)
        b.connect('clicked', self.on_buttonbox_clicked, 'redraw')
        self.extended_param_area = Gtk.VBox()
        vbox.pack_start(self.extended_param_area, True, True, 0)
        self.show_all()
        self.hide()
    def redraw(self):
        if self._redrawing:
            return False
        try:
            self._redrawing = True
            x = self.get_uncal()
            y = self.get_cal()
            self.fig.clf()
            if len(x) < 1 or len(y) < 1:
                return False
            xrange = np.linspace(min(x), max(x), 1000)
            ax = self.fig.add_subplot(1, 1, 1)
            ax.plot(x, y, 'bo')
            try:
                ax.plot(xrange, self.calibrate(xrange), 'r-')
            except:
                pass
            ax.set_xlabel('Uncalibrated')
            ax.set_ylabel('Calibrated')
        finally:
            self.canvas.draw()
            self._redrawing = False
    def update_extended_params(self):
        return True
    def on_cell_edited(self, cellrenderertext, path, new_text, val):
        try:
            self.calibrationpairs[path][val] = float(new_text)
        except ValueError:
            pass
        return True
    def on_buttonbox_clicked(self, button, whattodo):
        if whattodo == 'add':
            self.calibrationpairs.append((0., 0.))
        elif whattodo == 'clear':
            self.calibrationpairs.clear()
        elif whattodo == 'delete':
            sel = self.calibview.get_selection()
            model, paths = sel.get_selected_rows()
            refs = [Gtk.TreeRowReference.new(model, p) for p in paths]
            for r in refs:
                model.remove(model.get_iter(r.get_path()))
        elif whattodo == 'save':
            fcd = Gtk.FileChooserDialog('Save calibration data to...', self,
                                      Gtk.FileChooserAction.SAVE,
                                      buttons=(Gtk.STOCK_OK, Gtk.ResponseType.OK,
                                               Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
            ff = Gtk.FileFilter()
            ff.set_name('All files')
            ff.add_pattern('*')
            fcd.add_filter(ff)
            ff = Gtk.FileFilter()
            ff.set_name('Text and data files')
            ff.add_pattern('*.txt')
            ff.add_pattern('*.dat')
            fcd.add_filter(ff)
            ff = Gtk.FileFilter()
            ff.set_name('Calibration files')
            ff.add_pattern('*' + self._fileextension)
            fcd.add_filter(ff)
            fcd.set_filter(ff)
            fcd.set_do_overwrite_confirmation(True)
            try:
                if fcd.run() == Gtk.ResponseType.OK:
                    filename = fcd.get_filename()
                    if (not filename.lower().endswith(self._fileextension.lower())) \
                        and ('.' not in os.path.split(filename)[-1]):
                        filename = filename + self._fileextension
                    with open(filename, 'wt') as f:
                        self.write_header(f)
                        for i in self.calibrationpairs:
                            f.write('%16g\t%16g\n' % (i[0], i[1]))
            finally:
                fcd.destroy()
                del fcd
        elif whattodo == 'open':
            fcd = Gtk.FileChooserDialog('Load calibration data from...', self,
                                      Gtk.FileChooserAction.OPEN,
                                      buttons=(Gtk.STOCK_OK, Gtk.ResponseType.OK,
                                               Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
            ff = Gtk.FileFilter()
            ff.set_name('All files')
            ff.add_pattern('*')
            fcd.add_filter(ff)
            ff = Gtk.FileFilter()
            ff.set_name('Text and data files')
            ff.add_pattern('*.txt')
            ff.add_pattern('*.dat')
            fcd.add_filter(ff)
            ff = Gtk.FileFilter()
            ff.set_name('Calibration files')
            ff.add_pattern('*' + self._fileextension)
            fcd.add_filter(ff)
            fcd.set_filter(ff)
            try:
                if fcd.run() == Gtk.ResponseType.OK:
                    with open(fcd.get_filename(), 'rt') as f:
                        for l in f:
                            if not self.read_from_header(l):
                                try:
                                    self.calibrationpairs.append([float(x) for x in l.strip().split()])
                                except ValueError:
                                    pass
            finally:
                fcd.destroy()
                del fcd
        elif whattodo == 'redraw':
            pass  # do nothing, a redraw will occur anyway.
        self.update_extended_params()
        self.redraw()
        return True
    def get_uncal(self):
        return np.array([x[0] for x in self.calibrationpairs])
    def get_cal(self):
        return np.array([x[1] for x in self.calibrationpairs])
    def calibrate(self, value):
        x = self.get_uncal()
        y = self.get_cal()
        return self._calibrate(x, y, value)
    def uncalibrate(self, value):
        x = self.get_cal()
        y = self.get_uncal()
        return self._calibrate(x, y, value)
    def _calibrate(self, x, y, value):
        raise NotImplementedError
    def write_header(self, f):
        f.write('#Calibration file')
    def read_from_header(self, line):
        return False

class CalibratorPolynomial(Calibrator):
    def __init__(self, *args, **kwargs):
        Calibrator.__init__(self, *args, **kwargs)
        hbox = Gtk.HBox()
        self.extended_param_area.pack_start(hbox, True, True, 0)
        l = Gtk.Label(label='Degree of polynomial:')
        l.set_alignment(0, 0.5)
        hbox.pack_start(l, False, True, 0)
        self.degree = Gtk.SpinButton()
        hbox.pack_start(self.degree, True, True, 0)
        self.degree.set_increments(1, 10)
        self.extended_param_area.show_all()
        self.update_extended_params()
    def update_extended_params(self):
        self.degree.set_range(0, max(len(self.calibrationpairs) - 1, 0))
    def get_degree(self):
        return self.degree.get_value_as_int()
    def set_degree(self, value):
        self.degree.set_value(value)
    def write_header(self, f):
        Calibrator.write_header(self, f)
        f.write('#Degree: %d\n' % self.get_degree())
    def read_from_header(self, line):
        line = line.strip()
        if line.startswith('#Degree'):
            try:
                self.set_degree(float(line.split(':', 1)[1].strip()))
                return True
            except ValueError:
                return False
        return False
    def _calibrate(self, x, y, value):
        deg = self.get_degree()
        if deg == 0:
            y = y - x
            p = np.array([1, y.mean()])
        else:
            p = np.polyfit(x, y, deg)
        return np.polyval(p, value)


class EnergyCalibrator(CalibratorPolynomial):
    _title = 'Energy calibration'
    _fileextension = '.energycalib'

class DistCalibrator(CalibratorPolynomial):
    _title = 'Distance calibration'
    _fileextension = '.distcalib'

def qfrompix(pix, pixelsize, beampos, alpha, wavelength, dist):
    pixsizedivdist = pixelsize / dist
    catethus_near = 1 + pixsizedivdist * (pix - beampos) * np.cos(alpha)
    catethus_opposite = pixsizedivdist * (pix - beampos) * np.sin(alpha)
    twotheta = np.arctan2(catethus_opposite, catethus_near)
    return 4 * np.pi * np.sin(0.5 * twotheta) / wavelength

def pixfromq(q, pixelsize, beampos, alpha, wavelength, dist):
    twotheta = (2 * np.arcsin(q / (4 * np.pi) * wavelength))
    return dist * np.sin(twotheta) / np.sin(alpha - twotheta) / pixelsize + beampos

class EntryNeedingFinalization(Gtk.Entry):
    __gsignals__ = {'finalized':(GObject.SignalFlags.RUN_FIRST, None, ()),
                    'activate':'override',
                    'icon-release':'override',
                    'editing-done':'override',
                  }
    def __init__(self, *args, **kwargs):
        Gtk.Entry.__init__(self, *args, **kwargs)
        self.connect('insert-text', lambda obj, newtext, newtextlen, pos:self.mark_changed())
        self.connect('delete-text', lambda obj, startpos, endpos:self.mark_changed())
    def do_editing_done(self):
        self.mark_changed()
        return
    def mark_changed(self):
        self.set_icon_from_stock(Gtk.EntryIconPosition.SECONDARY, Gtk.STOCK_OK)
        self.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, True)
    def do_activate(self):
        self.finalize()
        return Gtk.Entry.do_activate(self)
    def do_icon_release(self, pos, event):
        if pos == Gtk.EntryIconPosition.SECONDARY:
            self.finalize()
    def finalize(self):
        self.set_icon_from_stock(Gtk.EntryIconPosition.SECONDARY, None)
        self.emit('finalized')
    def set_text_finalized(self, newtext):
        self.set_text(newtext)
        self.set_icon_from_stock(Gtk.EntryIconPosition.SECONDARY, None)
    
class QCalibrator(Calibrator):
    _title = 'Q calibration'
    _fileextension = '.qcalib'
    dist = GObject.property(type=float, default=216.13)
    wavelength = GObject.property(type=float, default=1.5418)
    pixelsize = GObject.property(type=float, default=50e-3)
    beampos = GObject.property(type=float, default=0)
    alpha = GObject.property(type=float, default=90)
    def __init__(self, *args, **kwargs):
        Calibrator.__init__(self, *args, **kwargs)
        tab = Gtk.Table()
        self.extended_param_area.pack_start(tab, True, True, 0)
        
        self.entries = {}
        self.checkbuttons = {}
        row = 0
        for label, propname in [('Sample-detector distance:', 'dist'),
                                ('Wavelength:', 'wavelength'),
                                ('Pixel size:', 'pixelsize'),
                                ('q = 0 pixel:', 'beampos'),
                                ('Detector angle:', 'alpha')]:
            self.checkbuttons[propname] = Gtk.CheckButton(label)
            tab.attach(self.checkbuttons[propname], 0, 1, row, row + 1, Gtk.AttachOptions.FILL)
            self.entries[propname] = EntryNeedingFinalization()
            self.entries[propname].connect('finalized', self.on_entry_changed, propname)
            tab.attach(self.entries[propname], 1, 2, row, row + 1)
            self.checkbuttons[propname].connect('toggled', self.on_checkbutton_toggled, self.entries[propname])
            self.connect('notify::' + propname, self.on_prop_changed_notify, self.entries[propname])
            row += 1
            self.on_checkbutton_toggled(self.checkbuttons[propname], self.entries[propname])
        
        for par in ['dist', 'wavelength', 'pixelsize', 'beampos', 'alpha']:
            self.notify(par)

        b = Gtk.Button('Determine all unchecked')
        tab.attach(b, 0, 2, row, row + 1)
        b.connect('clicked', self.on_fit)
        self.update_extended_params()
        self.extended_param_area.show_all()
    def on_entry_changed(self, entry, propname):
        with self.freeze_notify():
            self.set_property(propname, float(entry.get_text()))
    def on_prop_changed_notify(self, object, prop, entrywidget):
        if prop.name == 'alpha':
            value = self.get_property(prop.name) * 180.0 / np.pi
        else:
            value = self.get_property(prop.name)
        entrywidget.set_text_finalized(str(value))
    def on_checkbutton_toggled(self, checkbutton, corresponding_entry):
        if checkbutton.get_sensitive():
            corresponding_entry.set_sensitive(checkbutton.get_active())
        return True
    def update_extended_params(self):
        for n in self.checkbuttons:
            self.on_checkbutton_toggled(self.checkbuttons[n], self.entries[n])
    def set_fixed(self, propname, fixed=True):
        self.checkbuttons[propname].set_active(fixed)
    def on_fit(self, button):
        x = self.get_uncal()
        y = self.get_cal()
        if not (isinstance(self.get_dist(), FixedParameter) or isinstance(self.get_pixelsize(), FixedParameter)):
            dlg = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                  Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE,
                                  message_format='Either the sample-to-detector distance or the pixel size should be fixed!')
            dlg.run()
            dlg.destroy()
            return True
        try:
            pixelsize, beampos, alpha, wavelength, dist, stat = \
                nonlinear_leastsquares(x, y, None, qfrompix, (self.get_pixelsize(),
                                                              self.get_beampos(),
                                                              self.get_alpha(),
                                                              self.get_wavelength(),
                                                              self.get_dist()))
        except TypeError:
            dlg = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                  Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE,
                                  message_format='Not enough datasets')
            dlg.run()
            dlg.destroy()
            return True
        if not isinstance(dist, FixedParameter):
            self.dist = dist
        if not isinstance(pixelsize, FixedParameter):
            self.pixelsize = pixelsize
        if not isinstance(wavelength, FixedParameter):
            self.wavelength = wavelength
        if not isinstance(beampos, FixedParameter):
            self.beampos = beampos
        if not isinstance(alpha, FixedParameter):
            self.alpha = alpha
        return True
    def _get_myprop(self, name):
        if self.checkbuttons[name].get_active():
            return FixedParameter(self.entries[name].get_text())
        else:
            return float(self.entries[name].get_text())
    def get_alpha(self):
        a = self._get_myprop('alpha')
        return a.__class__(a * np.pi / 180.0)
    def set_alpha(self, value):
        self.alpha = value
    def get_beampos(self):
        return self._get_myprop('beampos')
    def set_beampos(self, value):
        self.beampos = value
    def get_dist(self):
        return self._get_myprop('dist')
    def set_dist(self, value):
        self.dist = value
    def get_pixelsize(self):
        return self._get_myprop('pixelsize')
    def set_pixelsize(self, value):
        self.pixelsize = value
    def get_wavelength(self):
        return self._get_myprop('wavelength')
    def set_wavelength(self, value):
        self.wavelength = value
    def calibrate(self, value):
        self.on_fit(None)
        return qfrompix(value, self.pixelsize, self.beampos, self.alpha,
                        self.wavelength, self.dist)
    def uncalibrate(self, value):
        self.on_fit(None)
        return pixfromq(value, self.pixelsize, self.beampos, self.alpha,
                        self.wavelength, self.dist)
    def write_header(self, f):
        Calibrator.write_header(self, f)
        f.write('#Q calibration\n')
        for prop in sorted(self.checkbuttons):
            f.write('#%s: %g; %d\n' % (prop, self.get_property(prop), self.checkbuttons[prop].get_active()))
    def read_from_header(self, line):
        line = line.strip()
        print line
        for name in sorted(self.checkbuttons):
            if line.startswith('#' + name + ': '):
                t = line.split(':', 1)[1]
                try:
                    self.set_property(name, float(t.split(';')[0]))
                    val = bool(int(t.split(';')[1]))
                    self.checkbuttons[name].set_active(val)
                except:
                    raise
                return True
        return False

def run_energycalibrator():
    c = EnergyCalibrator(flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT, buttons=(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))
    c.run()
    c.hide()
    return c

def run_qcalibrator():
    c = QCalibrator(flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT, buttons=(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))
    c.run()
    c.hide()
    return c
