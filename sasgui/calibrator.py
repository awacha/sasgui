'''
Created on Sep 6, 2012

@author: andris
'''
import gtk
import gobject
import numpy as np
import os
from sastool.fitting import FixedParameter, nonlinear_leastsquares
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg, NavigationToolbar2GTKAgg

class Calibrator(gtk.Dialog):
    '''
    A specialized gtk.Dialog for configuring interpolation-like calibration.
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
        gtk.Dialog.__init__(self, title, parent, flags, buttons)
        uber_vbox = self.get_content_area()
        uber_hbox = gtk.HBox()
        uber_vbox.pack_start(uber_hbox)
        vbox = gtk.VBox()
        uber_hbox.pack_start(vbox, False)
        vbox_fig = gtk.VBox()
        uber_hbox.pack_start(vbox_fig)
        self.fig = Figure(figsize=(0.2, 0.2), dpi=72)
        self.canvas = FigureCanvasGTKAgg(self.fig)
        self.canvas.set_size_request(300, 200)
        vbox_fig.pack_start(self.canvas)
        tb = NavigationToolbar2GTKAgg(self.canvas, vbox_fig)
        vbox_fig.pack_start(tb, False)

        hbox = gtk.HBox()
        vbox.pack_start(hbox)
        self.calibrationpairs = gtk.ListStore(gobject.TYPE_DOUBLE, gobject.TYPE_DOUBLE)
        self.calibview = gtk.TreeView(self.calibrationpairs)
        self.calibview.set_headers_visible(True)
        self.calibview.set_rules_hint(True)

        #self.calibview.set_fixed_height_mode(True)
        self.calibview.set_rubber_banding(True)

        uncrenderer = gtk.CellRendererText()
        uncrenderer.set_property('editable', True)
        uncrenderer.connect('edited', self.on_cell_edited, 0)
        tvc = gtk.TreeViewColumn(self._xcolumnname, uncrenderer, text=0)
        self.calibview.append_column(tvc)

        crenderer = gtk.CellRendererText()
        crenderer.set_property('editable', True)
        crenderer.connect('edited', self.on_cell_edited, 1)
        tvc = gtk.TreeViewColumn(self._ycolumnname, crenderer, text=1)
        self.calibview.append_column(tvc)
        self.calibview.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

        sw = gtk.ScrolledWindow()
        sw.add(self.calibview)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_size_request(*self.calibview.size_request())
        hbox.pack_start(sw)
        buttonbox = gtk.VButtonBox()
        hbox.pack_start(buttonbox, False)
        b = gtk.Button(stock=gtk.STOCK_ADD)
        buttonbox.add(b)
        b.connect('clicked', self.on_buttonbox_clicked, 'add')
        b = gtk.Button(stock=gtk.STOCK_DELETE)
        buttonbox.add(b)
        b.connect('clicked', self.on_buttonbox_clicked, 'delete')
        b = gtk.Button(stock=gtk.STOCK_CLEAR)
        buttonbox.add(b)
        b.connect('clicked', self.on_buttonbox_clicked, 'clear')
        b = gtk.Button(stock=gtk.STOCK_SAVE_AS)
        buttonbox.add(b)
        b.connect('clicked', self.on_buttonbox_clicked, 'save')
        b = gtk.Button(stock=gtk.STOCK_OPEN)
        buttonbox.add(b)
        b.connect('clicked', self.on_buttonbox_clicked, 'open')
        b = gtk.Button(stock=gtk.STOCK_REFRESH)
        buttonbox.add(b)
        b.connect('clicked', self.on_buttonbox_clicked, 'redraw')
        self.extended_param_area = gtk.VBox()
        vbox.pack_start(self.extended_param_area)
        self.show_all()
        self.hide()
    def redraw(self):
        if self._redrawing:
            return False
        try:
            self._redrawing = True
            x = self.get_uncal()
            y = self.get_cal()
            xrange = np.linspace(min(x), max(x), 1000)
            self.fig.clf()
            ax = self.fig.add_subplot(1, 1, 1)
            ax.plot(x, y, 'bo')
            try:
                ax.plot(xrange, self.calibrate(xrange), 'r-')
            except:
                pass
            ax.set_xlabel('Uncalibrated')
            ax.set_ylabel('Calibrated')
            self.canvas.draw()
        finally:
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
            self.calibrationpairs.append((0, 0))
        elif whattodo == 'clear':
            self.calibrationpairs.clear()
        elif whattodo == 'delete':
            sel = self.calibview.get_selection()
            model, paths = sel.get_selected_rows()
            refs = [gtk.TreeRowReference(model, p) for p in paths]
            for r in refs:
                model.remove(model.get_iter(r.get_path()))
        elif whattodo == 'save':
            fcd = gtk.FileChooserDialog('Save calibration data to...', self,
                                      gtk.FILE_CHOOSER_ACTION_SAVE,
                                      buttons=(gtk.STOCK_OK, gtk.RESPONSE_OK,
                                               gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
            ff = gtk.FileFilter()
            ff.set_name('All files')
            ff.add_pattern('*')
            fcd.add_filter(ff)
            ff = gtk.FileFilter()
            ff.set_name('Text and data files')
            ff.add_pattern('*.txt')
            ff.add_pattern('*.dat')
            fcd.add_filter(ff)
            ff = gtk.FileFilter()
            ff.set_name('Calibration files')
            ff.add_pattern('*' + self._fileextension)
            fcd.add_filter(ff)
            fcd.set_filter(ff)
            fcd.set_do_overwrite_confirmation(True)
            try:
                if fcd.run() == gtk.RESPONSE_OK:
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
            fcd = gtk.FileChooserDialog('Load calibration data from...', self,
                                      gtk.FILE_CHOOSER_ACTION_OPEN,
                                      buttons=(gtk.STOCK_OK, gtk.RESPONSE_OK,
                                               gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
            ff = gtk.FileFilter()
            ff.set_name('All files')
            ff.add_pattern('*')
            fcd.add_filter(ff)
            ff = gtk.FileFilter()
            ff.set_name('Text and data files')
            ff.add_pattern('*.txt')
            ff.add_pattern('*.dat')
            fcd.add_filter(ff)
            ff = gtk.FileFilter()
            ff.set_name('Calibration files')
            ff.add_pattern('*' + self._fileextension)
            fcd.add_filter(ff)
            fcd.set_filter(ff)
            try:
                if fcd.run() == gtk.RESPONSE_OK:
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
            pass #do nothing, a redraw will occur anyway.
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
        hbox = gtk.HBox()
        self.extended_param_area.pack_start(hbox)
        l = gtk.Label('Degree of polynomial:')
        l.set_alignment(0, 0.5)
        hbox.pack_start(l, False)
        self.degree = gtk.SpinButton()
        hbox.pack_start(self.degree)
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
        tab = gtk.Table()
        self.extended_param_area.pack_start(tab)
        self.dist_checkbutton = gtk.CheckButton('Sample-detector distance:')

        tab.attach(self.dist_checkbutton, 0, 1, 0, 1, gtk.FILL, gtk.FILL)
        self.dist_entry = gtk.Entry()
        tab.attach(self.dist_entry, 1, 2, 0, 1)
        self.dist_checkbutton.connect('toggled', self.on_checkbutton_toggled, self.dist_entry)
        self.dist_entry.set_text('216.13')

        self.wavelength_checkbutton = gtk.CheckButton('Wavelength:')
        tab.attach(self.wavelength_checkbutton, 0, 1, 1, 2, gtk.FILL, gtk.FILL)
        self.wavelength_entry = gtk.Entry()
        tab.attach(self.wavelength_entry, 1, 2, 1, 2)
        self.wavelength_checkbutton.connect('toggled', self.on_checkbutton_toggled, self.wavelength_entry)
        self.wavelength_entry.set_text('1.542')

        self.pixelsize_checkbutton = gtk.CheckButton('Pixel size:')
        tab.attach(self.pixelsize_checkbutton, 0, 1, 2, 3, gtk.FILL, gtk.FILL)
        self.pixelsize_entry = gtk.Entry()
        tab.attach(self.pixelsize_entry, 1, 2, 2, 3)
        self.pixelsize_checkbutton.connect('toggled', self.on_checkbutton_toggled, self.pixelsize_entry)
        self.pixelsize_entry.set_text('50e-3')

        self.beampos_checkbutton = gtk.CheckButton('q=0 pixel:')
        tab.attach(self.beampos_checkbutton, 0, 1, 3, 4, gtk.FILL, gtk.FILL)
        self.beampos_entry = gtk.Entry()
        tab.attach(self.beampos_entry, 1, 2, 3, 4)
        self.beampos_checkbutton.connect('toggled', self.on_checkbutton_toggled, self.beampos_entry)
        self.beampos_entry.set_text('0')

        self.alpha_checkbutton = gtk.CheckButton('Detector angle:')
        tab.attach(self.alpha_checkbutton, 0, 1, 4, 5, gtk.FILL, gtk.FILL)
        self.alpha_entry = gtk.Entry()
        tab.attach(self.alpha_entry, 1, 2, 4, 5)
        self.alpha_checkbutton.connect('toggled', self.on_checkbutton_toggled, self.alpha_entry)
        self.alpha_entry.set_text('90')

        b = gtk.Button('Determine all unchecked')
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
            dlg = gtk.MessageDialog(self, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                                  gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_CLOSE,
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
            dlg = gtk.MessageDialog(self, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                                  gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_CLOSE,
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
    c = EnergyCalibrator(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
    c.run()
    c.hide()
    return c

def run_qcalibrator():
    c = QCalibrator(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
    c.run()
    c.hide()
    return c
