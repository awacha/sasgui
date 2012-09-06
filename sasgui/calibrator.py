'''
Created on Sep 6, 2012

@author: andris
'''
import gtk
import gobject
import numpy as np
import os

class Calibrator(gtk.Dialog):
    '''
    A specialized gtk.Dialog for configuring interpolation-like calibration.
    '''
    _xcolumnname = 'Uncalibrated'
    _ycolumnname = 'Calibrated'
    _title = 'Calibration'
    _fileextension = '.calib'
    def __init__(self, title=None, parent=None, flags=0, buttons=None):
        '''
        Constructor
        '''
        if title is None:
            title = self._title
        gtk.Dialog.__init__(self, title, parent, flags, buttons)
        vbox = self.get_content_area()
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
        hbox = gtk.HBox()
        vbox.pack_start(hbox)
        l = gtk.Label('Degree of polynomial:')
        l.set_alignment(0, 0.5)
        hbox.pack_start(l, False)
        self.degree = gtk.SpinButton()
        hbox.pack_start(self.degree)
        self.degree.set_increments(1, 10)
        self.degree_spin_update()
        self.show_all()
        self.hide()
    def degree_spin_update(self):
        self.degree.set_range(0, max(len(self.calibrationpairs) - 1, 0))

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
                        f.write('#Calibration list\n#Degree: %d\n' % self.get_degree())
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
                            if l.strip().startswith('#Degree:'):
                                self.set_degree(float(l.strip().split(':', 1)[1].strip()))
                            else:
                                try:
                                    self.calibrationpairs.append([float(x) for x in l.strip().split()])
                                except ValueError:
                                    pass
            finally:
                fcd.destroy()
                del fcd
        self.degree_spin_update()
        return True
    def get_degree(self):
        return self.degree.get_value_as_int()
    def set_degree(self, value):
        self.degree.set_value(value)
    def get_uncal(self):
        return np.array([x[0] for x in self.calibrationpairs])
    def get_cal(self):
        return np.array([x[1] for x in self.calibrationpairs])
    def calibrate(self, value):
        deg = self.get_degree()
        x = self.get_uncal()
        y = self.get_cal()
        return self._calibrate(x, y, value, deg)
    def uncalibrate(self, value):
        deg = self.get_degree()
        x = self.get_cal()
        y = self.get_uncal()
        return self._calibrate(x, y, value, deg)
    def _calibrate(self, x, y, value, deg):
        if deg == 0:
            y = y - x
        p = np.polyfit(x, y, deg)
        if deg == 0:
            return value + p[0]
        else:
            return np.polyval(p, value)

class EnergyCalibrator(Calibrator):
    _title = 'Energy calibration'
    _fileextension = '.energycalib'

class DistCalibrator(Calibrator):
    _title = 'Distance calibration'
    _fileextension = '.distcalib'

def run_energycalibrator():
    c = EnergyCalibrator(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
    c.run()
    c.hide()
    return c
