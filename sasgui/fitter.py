from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from sastool.classes import ErrorValue
from sastool.misc.easylsq import FixedParameter, nonlinear_leastsquares
import itertools
import collections
import types
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import time
import sastool
import traceback

__all__ = ['Fitter', 'FitParam', 'FitParamList']

class Fitter(Gtk.Notebook):
    __gsignals__ = {'fitting-done':(GObject.SignalFlags.RUN_FIRST, None, (object,)),
                  }
    
    def __init__(self, axes=None, loadfuncs=sastool.fitting.fitfunctions):
        Gtk.Notebook.__init__(self)
        if axes is None:
            axes = plt.gca()
        self.axes = axes
        inputpage = Gtk.VBox()
        self.append_page(inputpage, Gtk.Label(label='Input data'))
        self.lineselector = LineSelector()
        self.lineselector.connect('line-selected', self.on_linechanged)
        self.lineselector.update_lines(self.axes)
        inputpage.pack_start(self.lineselector, True, True, 0)
        self.datarangeselector = DataRangeSelector()
        self.datarangeselector.set_axes(self.axes)
        inputpage.pack_start(self.datarangeselector, False, True, 0)
        
        modelpage = Gtk.VBox()
        self.append_page(modelpage, Gtk.Label(label='Model'))
        self.fitfunctionlist = FitFunctionList()
        self.fitfunctionlist.connect('func-changed', self.on_func_changed)
        modelpage.pack_start(self.fitfunctionlist, True, True, 0)
        
        fittingpage = Gtk.VPaned()
        self.append_page(fittingpage, Gtk.Label(label='Control'))
        self.fitparamlist = FitParamList()
        self.fitparamlist.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.fitparamlist.connect('params-changed', self.on_params_changed)
        fittingpage.add1(self.fitparamlist)
        vb = Gtk.VBox()
        fittingpage.add2(vb)
        bb = Gtk.HButtonBox()
        vb.pack_start(bb, False, True, 0)
        self.backbutton = Gtk.Button(stock=Gtk.STOCK_GO_BACK)
        bb.add(self.backbutton)
        self.backbutton.connect('clicked', self.on_button, 'Back')
        self.backbutton.set_sensitive(False)
        self.forwardbutton = Gtk.Button(stock=Gtk.STOCK_GO_FORWARD)
        bb.add(self.forwardbutton)
        self.forwardbutton.connect('clicked', self.on_button, 'Forward')
        self.forwardbutton.set_sensitive(False)
        self.execbutton = Gtk.Button(stock=Gtk.STOCK_EXECUTE)
        bb.add(self.execbutton)
        self.execbutton.connect('clicked', self.on_button, 'Fit')
        self.execbutton.set_sensitive(False)
        self.plotbutton = Gtk.Button('Plot model')
        bb.add(self.plotbutton)
        self.plotbutton.connect('clicked', self.on_button, 'plot')
        self.plotbutton.set_sensitive(False)
        
        self.during_fitting = Gtk.HBox()
        vb.pack_start(self.during_fitting, False, True, 0)
        self.fitting_progress = Gtk.ProgressBar()
        self.during_fitting.pack_start(self.fitting_progress, True, True, 0)
        self.stopfitting_button = Gtk.Button(stock=Gtk.STOCK_STOP)
        self.stopfitting_button.connect('clicked', self._stopfitting)
        self.during_fitting.pack_start(self.stopfitting_button, False, True, 0)
        self.during_fitting.set_no_show_all(True)
        
        self.resultslog = Gtk.TextView()
        self.resultslog_sw = Gtk.ScrolledWindow()
        vb.pack_start(self.resultslog_sw, True, True, 0)
        self.resultslog_sw.add(self.resultslog)
        self.resultslog.set_editable(False)
        
        outputpage = Gtk.VBox()
        self.append_page(outputpage, Gtk.Label(label='Output'))
        self.plot_fitted_checkbox = Gtk.CheckButton('Plot fitted curve?')
        self.plot_fitted_checkbox.set_active(True)
        self.plot_fitted_checkbox.connect('toggled', self.on_button, 'plotfitted')
        self.outputparams_table = Gtk.Table()
        outputpage.pack_start(self.outputparams_table, False, True, 0)
        l = Gtk.Label(label='Marker:'); l.set_alignment(0, 0.5)
        self.outputparams_table.attach(l, 0, 1, 0, 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.output_marker = Gtk.ComboBoxText()
        for m in ['None'] + list('.,ov^<>1234sp*hH+xDd|_'):
            self.output_marker.append_text(m)
        self.output_marker.set_active(0)
        self.outputparams_table.attach(self.output_marker, 1, 2, 0, 1)
        
        l = Gtk.Label(label='Line style:'); l.set_alignment(0, 0.5)
        self.outputparams_table.attach(l, 0, 1, 1, 2, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.output_linestyle = Gtk.ComboBoxText()
        for l in ['None', '-', '--', '-.', ':', ' ', "''"]:
            self.output_linestyle.append_text(l)
        self.output_linestyle.set_active(1)
        self.outputparams_table.attach(self.output_linestyle, 1, 2, 1, 2)
        
        l = Gtk.Label(label='Line width:'); l.set_alignment(0, 0.5)
        self.outputparams_table.attach(l, 0, 1, 2, 3, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.output_linewidth = Gtk.SpinButton()
        self.output_linewidth.set_digits(1)
        self.output_linewidth.set_range(0, 100)
        self.output_linewidth.set_increments(0.1, 1)
        self.output_linewidth.set_value(1)
        self.output_linewidth.set_numeric(True)
        self.outputparams_table.attach(self.output_linewidth, 1, 2, 2, 3)
        
        l = Gtk.Label(label='Marker size:'); l.set_alignment(0, 0.5)
        self.outputparams_table.attach(l, 0, 1, 3, 4, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.output_markersize = Gtk.SpinButton()
        self.output_markersize.set_digits(1)
        self.output_markersize.set_range(0, 100)
        self.output_markersize.set_increments(0.1, 1)
        self.output_markersize.set_value(1)
        self.output_markersize.set_numeric(True)
        self.outputparams_table.attach(self.output_markersize, 1, 2, 3, 4)

        l = Gtk.Label(label='Color:'); l.set_alignment(0, 0.5)
        self.outputparams_table.attach(l, 0, 1, 4, 5, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.output_color = Gtk.ColorButton(Gdk.color_parse('red'))
        self.outputparams_table.attach(self.output_color, 1, 2, 4, 5)
        
        self.singleton_fittedcurve = Gtk.CheckButton('Keep only one fitted curve?')
        self.singleton_fittedcurve.set_active(True)
        outputpage.pack_start(self.singleton_fittedcurve, False, True, 0)
        
        hbb = Gtk.HButtonBox()
        b = Gtk.Button('Remove plots of fitted curves')
        hbb.add(b)
        b.connect('clicked', self.on_button, 'clearfitted')
        self.axes.figure.canvas.mpl_connect('draw_event', self.on_drawevent)
        if loadfuncs is not None:
            self.fitfunctionlist.load_functions(loadfuncs)
        self.show_all()
    def _stopfitting(self, button):
        self._stop_fitting_requested = True
    def _scrolldown(self):
        va = self.resultslog_sw.get_vadjustment()
        va.set_value(va.get_upper() - va.get_page_size())
        return False
    def on_button(self, b, whattodo):
        if whattodo == 'Back':
            self.fitparamlist.history_move(-1)
            self.backbutton.set_sensitive(self.fitparamlist.history_canback())
        elif whattodo == 'Forward':
            self.fitparamlist.history_move(1)
            self.forwardbutton.set_sensitive(self.fitparamlist.history_canforward())
        elif whattodo == 'Fit':
            starttime = time.time()
            params = self.fitparamlist.get_params()
            min_ = self.datarangeselector.get_min()
            max_ = self.datarangeselector.get_max()
            data = self.lineselector.get_active_data()
            idx = np.logical_and(data[0] <= max_, data[0] >= min_)
            x = data[0][idx]
            y = data[1][idx]
            if data[2] is not None:
                dx = data[2][idx]
            else:
                dx = None
            if data[3] is not None:
                dy = data[3][idx]
            else:
                dy = None
            func = self.fitfunctionlist.get_function()
            try:
                self.during_fitting.set_no_show_all(False)
                self.fitting_progress.set_text('Fitting, please wait...')
                self.during_fitting.show_all()
                self._stop_fitting_requested = False
                def func1(*args, **kwargs):
                    self.fitting_progress.pulse()
                    while Gtk.events_pending():
                        Gtk.main_iteration_do(False)
                    if hasattr(self, '_stop_fitting_requested') and self._stop_fitting_requested:
                        raise StopIteration
                    return func(*args, **kwargs)
                ret = nonlinear_leastsquares(x, y, dy, func1, params)
            except Exception as ex:
                if isinstance(ex, StopIteration):
                    dialog = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.INFO, Gtk.ButtonsType.OK,
                                               'User break')
                    dialog.set_title('User break')
                else:
                    dialog = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK,
                                               str(ex.message))
                    # dialog.format_secondary_text('Traceback:')
                    msgarea = dialog.get_message_area()
                    expander = Gtk.Expander(label='Traceback')
                    expander.set_expanded(False)
                    msgarea.pack_start(expander, True, True, 0)
                    sw = Gtk.ScrolledWindow()
                    sw.set_size_request(200, 300)
                    expander.add(sw)
                    tv = Gtk.TextView()
                    sw.add(tv)
                    tv.get_buffer().set_text(traceback.format_exc())
                    tv.set_editable(False)
                    tv.set_wrap_mode(Gtk.WrapMode.WORD)
                    # tv.get_default_attributes().font = Pango.FontDescription('serif,monospace')
                    tv.set_justification(Gtk.Justification.LEFT)
                    msgarea.show_all()
                    dialog.set_title('Error!')
                dialog.run()
                dialog.destroy()
                return False
            finally:
                self.during_fitting.hide()
            endtime = time.time()
            buf = self.resultslog.get_buffer()
            buf.insert(buf.get_end_iter(), 'Results of fitting:\n')
            buf.insert(buf.get_end_iter(), '-------------------\n')
            buf.insert(buf.get_end_iter(), 'Start time: ' + time.ctime(starttime) + '\n')
            buf.insert(buf.get_end_iter(), 'End time: ' + time.ctime(endtime) + '\n')
            buf.insert(buf.get_end_iter(), 'Duration: ' + str(endtime - starttime) + ' secs\n')
            buf.insert(buf.get_end_iter(), 'Model: ' + func.name + '\n')
            buf.insert(buf.get_end_iter(), 'Dataset: ' + self.lineselector.active_line.get_label() + '\n')
            buf.insert(buf.get_end_iter(), 'X min: ' + str(x.min()) + '\n')
            buf.insert(buf.get_end_iter(), 'X max: ' + str(x.max()) + '\n')
            buf.insert(buf.get_end_iter(), 'Number of function evaluations: ' + str(ret[-1]['num_func_eval']) + '\n')
            buf.insert(buf.get_end_iter(), 'Error flag: ' + str(ret[-1]['error_flag']) + '\n')
            buf.insert(buf.get_end_iter(), 'Message from fitting routine: ' + ret[-1]['message'] + '\n')
            if dy is not None:
                buf.insert(buf.get_end_iter(), 'Errorbars: used\n')
            else:
                buf.insert(buf.get_end_iter(), 'Errorbars: absent\n')
            buf.insert(buf.get_end_iter(), 'Reduced Chi^2: ' + str(ret[-1]['Chi2_reduced']) + '\n')
            buf.insert(buf.get_end_iter(), 'R^2: ' + str(ret[-1]['R2']) + '\n')
            buf.insert(buf.get_end_iter(), 'DoF: ' + str(ret[-1]['DoF']) + '\n')
            buf.insert(buf.get_end_iter(), 'Fitted values of parameters:\n')
            for p, n in zip(ret[:-1], func.indepvars):
                if isinstance(p, FixedParameter):
                    buf.insert(buf.get_end_iter(), '  %s : %g (fixed)\n' % (n, float(p)))
                elif isinstance(p, ErrorValue):
                    buf.insert(buf.get_end_iter(), '  %s : %g +- %g \n' % (n, p.val, p.err))
            buf.insert(buf.get_end_iter(), 'Covariance: \n')
            buf.insert(buf.get_end_iter(), str(ret[-1]['Covariance']) + '\n')
            buf.insert(buf.get_end_iter(), 'Correlation coefficients: \n')
            buf.insert(buf.get_end_iter(), str(ret[-1]['Correlation_coeffs']) + '\n')
            GObject.idle_add(self._scrolldown)
            self.fitparamlist.update_params(ret[:-1])
            if self.singleton_fittedcurve.get_active():
                self.on_button(None, 'clearfitted')
            linestyle = self.output_linestyle.get_active_text()
            linewidth = self.output_linewidth.get_value()
            marker = self.output_marker.get_active_text()
            color = tuple([getattr(self.output_color.get_color(), '%s_float' % a) for a in ['red', 'green', 'blue']])
            self.axes.plot(x, ret[-1]['func_value'], marker=marker, lw=linewidth, color=color, ls=linestyle, label='__fitted_curve__')
            self.axes.figure.canvas.draw()
            stat = ret[-1]
            stat['func'] = func
            stat['starttime'] = starttime
            stat['endtime'] = endtime
            stat['dataset_name'] = self.lineselector.active_line.get_label()
            stat['x_min'] = x.min()
            stat['x_max'] = x.max()
            self.emit('fitting-done', ret)
        elif whattodo == 'plotfitted':
            self.outputparams_table.set_sensitive(b.get_active())
        elif whattodo == 'clearfitted':
            for l in self.axes.get_lines()[:]:
                if l.get_label() == '__fitted_curve__':
                    l.remove()
        elif whattodo == 'plot':
            min_ = self.datarangeselector.get_min()
            max_ = self.datarangeselector.get_max()
            data = self.lineselector.get_active_data()
            idx = np.logical_and(data[0] <= max_, data[0] >= min_)
            x = data[0][idx]
            func = self.fitfunctionlist.get_function()
            params = self.fitparamlist.get_params()
            y = func(x, *[float(p) for p in params])
            if self.singleton_fittedcurve.get_active():
                self.on_button(None, 'clearfitted')
            linestyle = self.output_linestyle.get_active_text()
            linewidth = self.output_linewidth.get_value()
            markersize = self.output_markersize.get_value()
            marker = self.output_marker.get_active_text()
            color = tuple([getattr(self.output_color.get_color(), '%s_float' % a) for a in ['red', 'green', 'blue']])
            self.axes.plot(x, y, marker=marker, lw=linewidth, markersize=markersize, color=color, ls=linestyle, label='__fitted_curve__')
            self.axes.figure.canvas.draw()
            
            self.axes.figure.canvas.draw()
        return False
    def on_params_changed(self, paramlist):
        self.forwardbutton.set_sensitive(self.fitparamlist.history_canforward())
        self.backbutton.set_sensitive(self.fitparamlist.history_canback())
    def on_func_changed(self, funclist, func):
        self.set_fitfunction(func)
        return True
    def set_fitfunction(self, func):
        self.fitparamlist.update_model(itertools.imap(FitParam,
                                           func.indepvars,
                                           itertools.repeat(False),
                                           itertools.repeat(0),
                                           itertools.repeat(0),
                                           ))
        self.fitparamlist.history_nuke()
    def on_drawevent(self, event):
        self.lineselector.update_lines(self.axes)
        return False
    def on_linechanged(self, lineselector, activeline):
        self.datarangeselector.set_curve(activeline)
        self.execbutton.set_sensitive(activeline is not None)
        self.plotbutton.set_sensitive(activeline is not None)
        return True
    def load_function(self, *args, **kwargs):
        return self.fitfunctionlist.load_functions(*args, **kwargs)
    
class FitterDialog(Gtk.Dialog):
    def __init__(self, title='Fitting...', parent=None,
                 flags=Gtk.DialogFlags.DESTROY_WITH_PARENT,
                 buttons=(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE),
                 axes=None, loadfuncs=sastool.fitting.fitfunctions):
        Gtk.Dialog.__init__(self, title, parent, flags, buttons)
        self.fitter = Fitter(axes, loadfuncs)
        self.get_content_area().pack_start(self.fitter, True, True, 0)
        self.fitter.show_all()
    def load_functions(self, *args, **kwargs):
        return self.fitter.load_functions(*args, **kwargs)

class DataRangeSelector(Gtk.VBox):
    def __init__(self):
        Gtk.VBox.__init__(self)
        self.axes = None
        self.curve = None
        tab = Gtk.Table()
        self.pack_start(tab, False, True, 0)
        self.min_checkbutton = Gtk.CheckButton('Min:')
        tab.attach(self.min_checkbutton, 0, 1, 0, 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.minentry = Gtk.Entry()
        tab.attach(self.minentry, 1, 2, 0, 1)
        self.mingetbutton = Gtk.Button('From zoom')
        tab.attach(self.mingetbutton, 2, 3, 0, 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.mingetbutton.connect('clicked', self.on_getbutton)
        self.min_checkbutton.connect('toggled', self.on_checkbutton, self.minentry, self.mingetbutton)
        
        self.max_checkbutton = Gtk.CheckButton('Max')
        tab.attach(self.max_checkbutton, 0, 1, 1, 2, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.maxentry = Gtk.Entry()
        tab.attach(self.maxentry, 1, 2, 1, 2)
        self.maxgetbutton = Gtk.Button('From zoom')
        tab.attach(self.maxgetbutton, 2, 3, 1, 2, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.maxgetbutton.connect('clicked', self.on_getbutton)
        self.max_checkbutton.connect('toggled', self.on_checkbutton, self.maxentry, self.maxgetbutton)
        self.set_curve(None)
    def on_getbutton(self, button):
        if button is self.mingetbutton and self.min_checkbutton.get_active():
            self.minentry.set_text(str(self.axes.axis()[0]))
        elif button is self.maxgetbutton and self.max_checkbutton.get_active():
            self.maxentry.set_text(str(self.axes.axis()[1]))
        return True
    def set_curve(self, curve):
        self.curve = curve
        self.on_checkbutton(self.min_checkbutton, self.minentry, self.mingetbutton)
        self.on_checkbutton(self.max_checkbutton, self.maxentry, self.maxgetbutton)
    def set_axes(self, axes):
        self.axes = axes
    def on_checkbutton(self, cb, entry, button):
        if cb.get_active():
            entry.set_sensitive(True)
            button.set_sensitive(True)
        else:
            entry.set_sensitive(False)
            button.set_sensitive(False)
            if self.curve is not None:
                if entry is self.minentry:
                    entry.set_text(str(self.curve.get_xdata().min()))
                elif entry is self.maxentry:
                    entry.set_text(str(self.curve.get_xdata().max()))
        return True
    def get_min(self):
        if self.min_checkbutton.get_active():
            return float(self.minentry.get_text())
        else:
            return -np.inf
    def get_max(self):
        if self.max_checkbutton.get_active():
            return float(self.maxentry.get_text())
        else:
            return np.inf
        
class LineSelector(Gtk.ScrolledWindow):
    __gsignals__ = {'line-selected':(GObject.SignalFlags.RUN_FIRST, None, (object,)),
                  }
    def __init__(self):
        Gtk.ScrolledWindow.__init__(self)
        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        # list of lines: label, marker, linestyle, color pixbuf, line2d object, active?, xdata, ydata, xerror, yerror, xerror present, yerror present
        self.liststore = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING,
                                       GObject.TYPE_STRING, GObject.TYPE_OBJECT,
                                       GObject.TYPE_PYOBJECT, GObject.TYPE_BOOLEAN,
                                       GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT,
                                       GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT,
                                       GObject.TYPE_BOOLEAN, GObject.TYPE_BOOLEAN)
        self.treeview = Gtk.TreeView(self.liststore)
        self.treeview.set_rules_hint(True)
        self.treeview.set_headers_clickable(True)
        self.add(self.treeview)
        crt = Gtk.CellRendererToggle()
        crt.set_radio(True)
        crt.set_activatable(True)
        crt.connect('toggled', self.on_set_active_line)
        tvc = Gtk.TreeViewColumn('Active?', crt, active=5)
        self.treeview.append_column(tvc)
        tvc = Gtk.TreeViewColumn('Legend', Gtk.CellRendererText(), text=0)
        self.treeview.append_column(tvc)
        tvc = Gtk.TreeViewColumn('Marker', Gtk.CellRendererText(), text=1)
        self.treeview.append_column(tvc)
        tvc = Gtk.TreeViewColumn('Line style', Gtk.CellRendererText(), text=2)
        self.treeview.append_column(tvc)
        tvc = Gtk.TreeViewColumn('Color', Gtk.CellRendererPixbuf(), pixbuf=3)
        self.treeview.append_column(tvc)
        crt = Gtk.CellRendererToggle()
        crt.set_activatable(False)
        tvc = Gtk.TreeViewColumn('X error', crt, active=10)
        self.treeview.append_column(tvc)
        crt = Gtk.CellRendererToggle()
        crt.set_activatable(False)
        tvc = Gtk.TreeViewColumn('Y error', crt, active=11)
        self.treeview.append_column(tvc)
        self.active_line = None
    def on_set_active_line(self, cb, path):
        it = self.liststore.get_iter(path)
        self.active_line = self.liststore[it][4]
        for l in self.liststore:
            l[5] = False
        self.liststore[it][5] = True
        self.emit('line-selected', self.active_line)
    def update_lines(self, axes):
        self.liststore.clear()
        errorbar_suspicious_lines = []
        for l in axes.lines:
            if l.get_label() == '_nolegend_' and l.get_marker() in ['|', '_']:
                errorbar_suspicious_lines.append(l)
                continue
            if l.get_label().startswith('__'):
                continue
            horizerrorbars = [x for x in errorbar_suspicious_lines if x.get_marker() == '|']
            verterrorbars = [x for x in errorbar_suspicious_lines if x.get_marker() == '_']
            if horizerrorbars:
                if (len(horizerrorbars) == 2 and all([x.get_xdata().shape == l.get_xdata().shape for x in horizerrorbars])
                    and all([(x.get_ydata() == l.get_ydata()).all() for x in horizerrorbars])):
                    eb = np.vstack([x.get_xdata() for x in horizerrorbars])
                    xerr = (eb.max(axis=0) - eb.min(axis=0)) * 0.5
                else:
                    pass
            else:
                xerr = None
            if verterrorbars:
                if (len(verterrorbars) == 2 and all([x.get_xdata().shape == l.get_xdata().shape for x in verterrorbars])
                    and all([(x.get_xdata() == l.get_xdata()).all() for x in verterrorbars])):
                    eb = np.vstack([x.get_ydata() for x in verterrorbars])
                    yerr = (eb.max(axis=0) - eb.min(axis=0)) * 0.5
                else:
                    pass
            else:
                yerr = None
            errorbar_suspicious_lines = []
            color = matplotlib.colors.colorConverter.to_rgb(l.get_color())
            colorint = int(color[0] * 0xff000000) + int(color[1] * 0x00ff0000) + int(color[2] * 0x0000ff00) + 0xff
            pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, 24, 8)
            pb.fill(colorint)
            self.liststore.append((l.get_label(), l.get_marker(), l.get_linestyle(), pb, l, l is self.active_line, l.get_xdata(), l.get_ydata(), xerr, yerr, xerr is not None, yerr is not None))
        if not any([l is self.active_line for l in axes.lines]):
            self.active_line = None
    def get_active_data(self):
        l = [x for x in self.liststore if x[4] is self.active_line]
        if not l:
            raise ValueError('No active dataset')
        return tuple([l[0][i] for i in range(6, 10)])
    
class FitFunction(object):
    def __new__(cls, func):
        if isinstance(func, collections.Sequence):
            lis = []
            for x in func:
                if not isinstance(x, types.FunctionType):
                    continue
                try:
                    obj = cls.__new__(cls, x)
                    obj.__init__(x)
                except ValueError:
                    pass
                else:
                    lis.append(obj)
            return lis
        elif isinstance(func, types.ModuleType):
            return cls.__new__(cls, [func.__getattribute__(x) for x in dir(func) if not x.startswith('_')])
        return object.__new__(cls)
    def __init__(self, func):
        if not all([hasattr(func, x) for x in ('func_name', 'func_doc', 'func_code')]):
            raise ValueError('Object is not a function!')
        self.func = func
    def __call__(self, *args, **kwargs):
        return self.func.__call__(*args, **kwargs)
    @property
    def name(self):
        return self.func.func_name
    @property
    def helptext(self):
        return self.func.func_doc
    @property
    def indepvars(self):
        return self.func.func_code.co_varnames[1:self.func.func_code.co_argcount]
    def get_params(self):
        lis = [FitParam(x) for x in self.indepvars]
        defs = self.func.func_defaults
        if defs is not None:
            for i, d in enumerate(defs):
                lis[len(lis) - len(defs) + i].value = d
                lis[len(lis) - len(defs) + i].fixed = True
        return lis
    
class FitFunctionList(Gtk.VBox):
    __gsignals__ = {'func-changed':(GObject.SignalFlags.RUN_FIRST, None, (object,)), }
    def __init__(self):
        Gtk.VBox.__init__(self)
        self.funcs = []
        hb = Gtk.HBox()
        self.pack_start(hb, False, True, 0)
        l = Gtk.Label(label='Function:')
        l.set_alignment(0, 0.5)
        hb.pack_start(l, True, True, 0)
        self.combo = Gtk.ComboBoxText()
        hb.pack_start(self.combo, True, True, 0)
        self.combo.connect('changed', self.on_func_selected)
        frame = Gtk.Frame(label='Description:')
        self.pack_start(frame, True, True, 0)
        sw = Gtk.ScrolledWindow()
        frame.add(sw)
        self.helptext = Gtk.TextView()
        self.helptext.set_editable(False)
        self.helptext.set_cursor_visible(False)
        sw.add(self.helptext)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.show_all()
    def load_functions(self, module=None, clear_before=True):
        if clear_before:
            self.funcs = []
            self.combo.get_model().clear()
        if module is not None:
            self.funcs = FitFunction(module)
        for f in self.funcs:
            self.combo.append_text(f.name)
        self.combo.set_active(0)
        self.on_func_selected(self.combo)
    def on_func_selected(self, combobox):
        self.helptext.get_buffer().set_text(self.funcs[combobox.get_active()].helptext)
        self.emit('func-changed', self.funcs[combobox.get_active()])
    def get_function(self):
        return self.funcs[self.combo.get_active()]
    
class FitParam(object):
    def __init__(self, name='<unnamed>', fixed=False, value=0, error=0):
        self.name = name
        self.fixed = fixed
        if isinstance(value, ErrorValue):
            self.value = value
        else:
            self.value = ErrorValue(value, error)

class FitParamList(Gtk.ScrolledWindow):
    __gsignals__ = {'params-changed':(GObject.SignalFlags.RUN_FIRST, None, ()),
                  }
    
    def __init__(self, params=None):
        self._history = []
        self._histposition = -1
        self._committed = True
        Gtk.ScrolledWindow.__init__(self)
        self.model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_BOOLEAN, GObject.TYPE_STRING, GObject.TYPE_STRING)
        
        self.treeview = Gtk.TreeView(self.model)
        self.add(self.treeview)
        self.treeview.set_headers_visible(True)
        self.treeview.set_rules_hint(True)
        tvc = Gtk.TreeViewColumn('Parameter', Gtk.CellRendererText(), text=0)
        self.treeview.append_column(tvc)
        crt = Gtk.CellRendererToggle()
        crt.set_radio(False)
        crt.connect('toggled', self.on_fixed_changed)
        tvc = Gtk.TreeViewColumn('Fixed', crt, active=1)
        self.treeview.append_column(tvc)
        crt = Gtk.CellRendererText()
        crt.set_property('editable', True)
        crt.connect('edited', self.on_value_changed)
        tvc = Gtk.TreeViewColumn('Value', crt, text=2)
        self.treeview.append_column(tvc)
        tvc = Gtk.TreeViewColumn('Error', Gtk.CellRendererText(), text=3)
        self.treeview.append_column(tvc)
        
        self.update_model(params)
        self.show_all()
    def on_value_changed(self, cellrenderer, path, new_text):
        try:
            self.model.set_value(self.model.get_iter(path), 2, new_text)
            self._committed = False
        except:
            raise 
            # TODO: notify user
    def on_fixed_changed(self, cellrenderer, path):
        self._committed = False
        it = self.model.get_iter(path)
        self.model.set_value(it, 1, not self.model.get_value(it, 1))
        self.model.set_value(it, 3, 0)
    def update_model(self, params=None, clear_before=True):
        if clear_before:
            self.model.clear()
        if params is not None:
            for p in params:
                self.model.append((p.name, p.fixed, '%g' % (p.value.val), '%g' % (p.value.err)))
        self._committed = False
    def update_params(self, params=None):
        for p, row in zip(params, self.model):
            if isinstance(p, ErrorValue):
                row[2] = '%g' % (p.val)
                row[3] = '%g' % (p.err)
            else:
                row[2] = '%g' % p
                row[3] = '0'
    def get_params(self):
        lis = []
        for p in self.model:
            if p[1]:
                lis.append(FixedParameter(float(p[2])))
            else:
                lis.append(ErrorValue(float(p[2]), float(p[3])))
        self.history_checkin()
        return lis
    def history_checkin(self):
        if self._committed:
            return
        if self._histposition < len(self._history) - 1:
            self._history = self._history[:self._histposition + 1]
        self._history.append([tuple(x) for x in self.model])
        self._histposition += 1
        self._committed = True
        self.emit('params-changed')
    def history_move(self, amount=1):
        if (self._histposition + amount >= 0 and self._histposition + amount < len(self._history)):
            self._histposition += amount
            self.model.clear()
            for h in self._history[self._histposition]:
                self.model.append(h)
        self.emit('params-changed')
    def history_canforward(self):
        return self._histposition < len(self._history) - 1
    def history_canback(self):
        return self._histposition > 0
    def history_nuke(self):
        self._history = []
        self._histposition = -1
        self.emit('params-changed')
