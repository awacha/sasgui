'''
Created on Sep 6, 2012

@author: andris
'''
from gi.repository import Gtk
from gi.repository import GObject
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
            refs = [Gtk.TreeRowReference(model, p) for p in paths]
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

def qfrompix(pix, pixsize, beampos, alpha, wavelength, dist):
    pixsizedivdist = pixsize / dist
    catethus_near = 1 + pixsizedivdist * (pix - beampos) * np.cos(alpha)
    catethus_opposite = pixsizedivdist * (pix - beampos) * np.sin(alpha)
    twotheta = np.arctan2(catethus_opposite, catethus_near)
    return 4 * np.pi * np.sin(0.5 * twotheta) / wavelength

def pixfromq(q, pixsize, beampos, alpha, wavelength, dist):
    twotheta = (2 * np.arcsin(q / (4 * np.pi) * wavelength))
    return dist * np.sin(twotheta) / np.sin(alpha - twotheta) / pixsize + beampos

class QCalibrator(Calibrator):
    _title = 'Q calibration'
    _fileextension = '.qcalib'
    def __init__(self, *args, **kwargs):
        Calibrator.__init__(self, *args, **kwargs)
        tab = Gtk.Table()
        self.extended_param_area.pack_start(tab, True, True, 0)
        self.dist_checkbutton = Gtk.CheckButton('Sample-detector distance:')

        tab.attach(self.dist_checkbutton, 0, 1, 0, 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.dist_entry = Gtk.Entry()
        tab.attach(self.dist_entry, 1, 2, 0, 1)
        self.dist_checkbutton.connect('toggled', self.on_checkbutton_toggled, self.dist_entry)
        self.dist_entry.set_text('216.13')

        self.wavelength_checkbutton = Gtk.CheckButton('Wavelength:')
        tab.attach(self.wavelength_checkbutton, 0, 1, 1, 2, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.wavelength_entry = Gtk.Entry()
        tab.attach(self.wavelength_entry, 1, 2, 1, 2)
        self.wavelength_checkbutton.connect('toggled', self.on_checkbutton_toggled, self.wavelength_entry)
        self.wavelength_entry.set_text('1.542')

        self.pixelsize_checkbutton = Gtk.CheckButton('Pixel size:')
        tab.attach(self.pixelsize_checkbutton, 0, 1, 2, 3, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.pixelsize_entry = Gtk.Entry()
        tab.attach(self.pixelsize_entry, 1, 2, 2, 3)
        self.pixelsize_checkbutton.connect('toggled', self.on_checkbutton_toggled, self.pixelsize_entry)
        self.pixelsize_entry.set_text('50e-3')

        self.beampos_checkbutton = Gtk.CheckButton('q=0 pixel:')
        tab.attach(self.beampos_checkbutton, 0, 1, 3, 4, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.beampos_entry = Gtk.Entry()
        tab.attach(self.beampos_entry, 1, 2, 3, 4)
        self.beampos_checkbutton.connect('toggled', self.on_checkbutton_toggled, self.beampos_entry)
        self.beampos_entry.set_text('0')

        self.alpha_checkbutton = Gtk.CheckButton('Detector angle:')
        tab.attach(self.alpha_checkbutton, 0, 1, 4, 5, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.alpha_entry = Gtk.Entry()
        tab.attach(self.alpha_entry, 1, 2, 4, 5)
        self.alpha_checkbutton.connect('toggled', self.on_checkbutton_toggled, self.alpha_entry)
        self.alpha_entry.set_text('90')

        b = Gtk.Button('Determine all unchecked')
        tab.attach(b, 0, 2, 5, 6)
        b.connect('clicked', self.on_fit)
        self.update_extended_params()
        self.extended_param_area.show_all()
    def on_checkbutton_toggled(self, checkbutton, corresponding_entry):
        corresponding_entry.set_sensitive(checkbutton.get_active())
        return True
    def update_extended_params(self):
        for n in ['alpha', 'dist', 'beampos', 'pixelsize', 'wavelength']:
            self.on_checkbutton_toggled(getattr(self, n + '_checkbutton'), getattr(self, n + '_entry'))
    def on_fit(self, button):
        x = self.get_uncal()
        y = self.get_cal()
        if not (isinstance(self.dist, FixedParameter) or isinstance(self.pixsize, FixedParameter)):
            dlg = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                  Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE,
                                  message_format='Either the sample-to-detector distance or the pixel size should be fixed!')
            dlg.run()
            dlg.destroy()
            return True
        try:
            pixsize, beampos, alpha, wavelength, dist, stat = \
                nonlinear_leastsquares(x, y, None, qfrompix, (self.pixsize,
                                                              self.beampos,
                                                              self.alpha,
                                                              self.wavelength,
                                                              self.dist))
        except TypeError:
            dlg = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                  Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE,
                                  message_format='Not enough datasets')
            dlg.run()
            dlg.destroy()
            return True
        if not isinstance(dist, FixedParameter):
            self.dist = dist
        if not isinstance(pixsize, FixedParameter):
            self.pixsize = pixsize
        if not isinstance(wavelength, FixedParameter):
            self.wavelength = wavelength
        if not isinstance(beampos, FixedParameter):
            self.beampos = beampos
        if not isinstance(alpha, FixedParameter):
            self.alpha = alpha
        return True
    def get_alpha(self):
        a = float(self.alpha_entry.get_text()) * np.pi / 180.0
        if self.alpha_checkbutton.get_active():
            return FixedParameter(a)
        else:
            return float(a)
    def set_alpha(self, value):
        self.alpha_entry.set_text('%.2f' % (value * 180.0 / np.pi))
    def get_beampos(self):
        a = self.beampos_entry.get_text()
        if self.beampos_checkbutton.get_active():
            return FixedParameter(a)
        else:
            return float(a)
    def set_beampos(self, value):
        self.beampos_entry.set_text('%g' % value)
    def get_dist(self):
        a = self.dist_entry.get_text()
        if self.dist_checkbutton.get_active():
            return FixedParameter(a)
        else:
            return float(a)
    def set_dist(self, value):
        self.dist_entry.set_text('%g' % value)
    def get_pixsize(self):
        a = self.pixelsize_entry.get_text()
        if self.pixelsize_checkbutton.get_active():
            return FixedParameter(a)
        else:
            return float(a)
    def set_pixsize(self, value):
        self.pixelsize_entry.set_text('%g' % value)
    def get_wavelength(self):
        a = self.wavelength_entry.get_text()
        if self.wavelength_checkbutton.get_active():
            return FixedParameter(a)
        else:
            return float(a)
    def set_wavelength(self, value):
        self.wavelength_entry.set_text('%g' % value)
    alpha = property(get_alpha, set_alpha)
    beampos = property(get_beampos, set_beampos)
    dist = property(get_dist, set_dist)
    pixsize = property(get_pixsize, set_pixsize)
    wavelength = property(get_wavelength, set_wavelength)
    def calibrate(self, value):
        self.on_fit(None)
        return qfrompix(value, self.pixsize, self.beampos, self.alpha,
                        self.wavelength, self.dist)
    def uncalibrate(self, value):
        self.on_fit(None)
        return pixfromq(value, self.pixsize, self.beampos, self.alpha,
                        self.wavelength, self.dist)
    def write_header(self, f):
        Calibrator.write_header(self, f)
        f.write('#Q calibration\n')
        f.write('#alpha: %g; %d\n' % (self.alpha, self.alpha_checkbutton.get_active()))
        f.write('#beampos: %g; %d\n' % (self.beampos, self.beampos_checkbutton.get_active()))
        f.write('#dist: %g; %d\n' % (self.dist, self.dist_checkbutton.get_active()))
        f.write('#pixsize: %g; %d\n' % (self.pixsize, self.pixelsize_checkbutton.get_active()))
        f.write('#wavelength: %g; %d\n' % (self.wavelength, self.wavelength_checkbutton.get_active()))
    def read_from_header(self, line):
        line = line.strip()
        print line
        for name, cb in zip(['alpha', 'beampos', 'dist', 'pixsize', 'wavelength'],
                            [self.alpha_checkbutton, self.beampos_checkbutton,
                             self.dist_checkbutton, self.pixelsize_checkbutton,
                             self.wavelength_checkbutton]):
            if line.startswith('#' + name):
                t = line.split(':', 1)[1]
                print name + ' found'
                try:
                    setattr(self, name, float(t.split(';')[0]))
                    val = bool(int(t.split(';')[1]))
                    print name, val
                    cb.set_active(val)
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
