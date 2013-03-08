from gi.repository import Gtk
from gi.repository import GObject
from .fitter import Fitter
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg
from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3
import sastool
import time
__all__ = ['PlotSASCurve', 'PlotSASCurveWindow']


class PlotSASCurve(Gtk.HBox):
    def __init__(self, *args, **kwargs):
        Gtk.HBox.__init__(self, *args, **kwargs)
        ex = Gtk.Expander(label='Fitting...')
        ex.get_label_widget().set_angle(90)
        self.pack_start(ex, False, True, 0)
        vbox_fig = Gtk.VBox()
        self.pack_start(vbox_fig, True, True, 0)
        self.fig = Figure(figsize=(0.2, 0.2), dpi=72)
        self.canvas = FigureCanvasGTK3Agg(self.fig)
        self.canvas.set_size_request(640, 480)
        vbox_fig.pack_start(self.canvas, True, True, 0)
        tb = NavigationToolbar2GTK3(self.canvas, None)
        vbox_fig.pack_start(tb, False, True, 0)
        self.fitter = Fitter(axes=self.gca())
        ex.add(self.fitter)
        ex.connect('notify::expanded', self.on_expand)
    def on_expand(self, expander, *args):
        if expander.get_expanded():
            expander.get_label_widget().set_angle(0)
        else:
            expander.get_label_widget().set_angle(90)
        return True
    def gca(self):
        return self.fig.gca()
    def plot(self, *args, **kwargs):
        if args and isinstance(args[0], sastool.classes.GeneralCurve):
            kwargs['axes'] = self
            args[0].plot(*args[1:], **kwargs)
        else:
            ret = self.gca().plot(*args, **kwargs)
            self.draw()
            return ret
    def loglog(self, *args, **kwargs):
        if args and isinstance(args[0], sastool.classes.GeneralCurve):
            kwargs['axes'] = self
            args[0].loglog(*args[1:], **kwargs)
        else:
            ret = self.gca().loglog(*args, **kwargs)
            self.draw()
            return ret
    def errorbar(self, *args, **kwargs):
        if args and isinstance(args[0], sastool.classes.GeneralCurve):
            kwargs['axes'] = self
            args[0].errorbar(*args[1:], **kwargs)
        else:
            ret = self.gca().errorbar(*args, **kwargs)
            self.draw()
            return ret
    def semilogy(self, *args, **kwargs):
        if args and isinstance(args[0], sastool.classes.GeneralCurve):
            kwargs['axes'] = self
            args[0].semilogy(*args[1:], **kwargs)
        else:
            ret = self.gca().semilogy(*args, **kwargs)
            self.draw()
            return ret
    def semilogx(self, *args, **kwargs):
        if args and isinstance(args[0], sastool.classes.GeneralCurve):
            kwargs['axes'] = self
            args[0].semilogx(*args[1:], **kwargs)
        else:
            ret = self.gca().semilogx(*args, **kwargs)
            self.draw()
            return ret
    def draw(self):
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
