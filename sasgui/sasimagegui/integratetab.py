from gi.repository import Gtk
from gi.repository import GObject
import numpy as np

class IntegrateTab(Gtk.HBox):
    __gsignals__ = {'integration-done':(GObject.SignalFlags.RUN_FIRST, None, (object, object, str, bool)),
                    'error':(GObject.SignalFlags.RUN_FIRST, None, (object,)),
                   }
    def __init__(self):
        Gtk.HBox.__init__(self)
        tb = Gtk.Toolbar()
        tb.set_show_arrow(False)
        tb.set_style(Gtk.ToolbarStyle.BOTH)
        self.pack_start(tb, False, True, 0)

        b = Gtk.ToolButton('Execute')
        tb.insert(b, -1)
        b.connect('clicked', self.on_button_clicked, 'execute')

        b = Gtk.ToolButton(Gtk.STOCK_REFRESH)
        tb.insert(b, -1)
        b.connect('clicked', self.on_button_clicked, 'refresh')

        frame = Gtk.Frame()
        self.pack_start(frame, False, True, 0)
        tab = Gtk.Table()
        frame.add(tab)

        l = Gtk.Label(label='Method:'); l.set_alignment(0, 0.5)
        tab.attach(l, 0, 1, 0, 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.intmethod_combo = Gtk.ComboBoxText()
        tab.attach(self.intmethod_combo, 1, 2, 0, 1)
        self.intmethod_combo.append_text('Full radial')
        self.intmethod_combo.append_text('Sector')
        self.intmethod_combo.append_text('Slice')
        self.intmethod_combo.append_text('Azimuthal')
        self.intmethod_combo.connect('changed', self.on_intmethod_changed)

        l = Gtk.Label(label='Abscissa:'); l.set_alignment(0, 0.5)
        tab.attach(l, 0, 1, 1, 2, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.abscissa_combo = Gtk.ComboBoxText()
        tab.attach(self.abscissa_combo, 1, 2, 1, 2)
        self.abscissa_combo.append_text('q')
        self.abscissa_combo.append_text('pixel')
        self.abscissa_combo.set_active(0)

        self.Nbins_checkbutton = Gtk.CheckButton('Nr of bins:')
        tab.attach(self.Nbins_checkbutton, 0, 1, 2, 3, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.Nbins_entry = Gtk.Entry()
        self.Nbins_checkbutton.connect('toggled', self.on_checkbutton_changed, self.Nbins_entry)
        tab.attach(self.Nbins_entry, 1, 2, 2, 3)
        self.on_checkbutton_changed(self.Nbins_checkbutton, self.Nbins_entry)

        self.minabscissa_checkbutton = Gtk.CheckButton('Min. abscissa:')
        tab.attach(self.minabscissa_checkbutton, 2, 3, 0, 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.minabscissa_entry = Gtk.Entry()
        self.minabscissa_entry.set_text('0.001')
        self.minabscissa_checkbutton.connect('toggled', self.on_checkbutton_changed, self.minabscissa_entry)
        tab.attach(self.minabscissa_entry, 3, 4, 0, 1)
        self.on_checkbutton_changed(self.minabscissa_checkbutton, self.minabscissa_entry)

        self.maxabscissa_checkbutton = Gtk.CheckButton('Max. abscissa:')
        tab.attach(self.maxabscissa_checkbutton, 2, 3, 1, 2, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.maxabscissa_entry = Gtk.Entry()
        self.maxabscissa_entry.set_text('100')
        self.maxabscissa_checkbutton.connect('toggled', self.on_checkbutton_changed, self.maxabscissa_entry)
        tab.attach(self.maxabscissa_entry, 3, 4, 1, 2)
        self.on_checkbutton_changed(self.maxabscissa_checkbutton, self.maxabscissa_entry)

        l = Gtk.Label(label='Abscissa spacing:'); l.set_alignment(0, 0.5)
        tab.attach(l, 2, 3, 2, 3, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        self.abscissascaling_combo = Gtk.ComboBoxText()
        tab.attach(self.abscissascaling_combo, 3, 4, 2, 3)
        self.abscissascaling_combo.append_text('linear')
        self.abscissascaling_combo.append_text('logarithmic')

        self.extralabels = []
        self.extraentries = []
        for i in range(2):
            self.extralabels.append(Gtk.Label())
            self.extralabels[-1].set_alignment(0, 0.5)
            tab.attach(self.extralabels[-1], 4, 5, i, i + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
            self.extraentries.append(Gtk.Entry())
            tab.attach(self.extraentries[-1], 5, 6, i, i + 1)
        self.extracb = Gtk.CheckButton()
        self.extracb.set_alignment(0, 0.5)
        self.extracb.connect('toggled', self.on_extracb_toggled)
        tab.attach(self.extracb, 4, 6, 2, 3)

        self.intmethod_combo.set_active(0)
    def on_extracb_toggled(self, cb):
        if self.intmethod_combo.get_active_text() != 'Azimuthal':
            return False
        try:
            minradius = float(self.extraentries[0].get_text())
            maxradius = float(self.extraentries[1].get_text())
        except ValueError:
            return False
        if cb.get_active():
            minradius = self.get_toplevel().data.pixeltoq_radius(minradius)
            maxradius = self.get_toplevel().data.pixeltoq_radius(maxradius)
        else:
            minradius = self.get_toplevel().data.qtopixel_radius(minradius)
            maxradius = self.get_toplevel().data.qtopixel_radius(maxradius)
        self.extraentries[0].set_text(str(minradius))
        self.extraentries[1].set_text(str(maxradius))
        return True
    def on_intmethod_changed(self, combo):
        if combo.get_active_text() == 'Full radial':
            for i in range(2):
                self.extralabels[i].set_label('')
                self.extralabels[i].set_sensitive(False)
                self.extraentries[i].set_text('')
                self.extraentries[i].set_sensitive(False)
            self.extracb.set_label('')
            self.extracb.set_sensitive(False)
        elif combo.get_active_text() == 'Sector':
            for i, name in zip(list(range(2)), ['Phi0 (deg):', 'dPhi (deg):']):
                self.extralabels[i].set_label(name)
                self.extralabels[i].set_sensitive(True)
                self.extraentries[i].set_text('')
                self.extraentries[i].set_sensitive(True)
            self.extracb.set_label('Centrosymmetric?')
            self.extracb.set_sensitive(True)
        elif combo.get_active_text() == 'Slice':
            for i, name in zip(list(range(2)), ['Phi0 (deg):', 'width (pixel):']):
                self.extralabels[i].set_label(name)
                self.extralabels[i].set_sensitive(True)
                self.extraentries[i].set_text('')
                self.extraentries[i].set_sensitive(True)
            self.extracb.set_label('')
            self.extracb.set_sensitive(False)
        elif combo.get_active_text() == 'Azimuthal':
            for i, name in zip(list(range(2)), ['Min. radius:', 'Max. radius:']):
                self.extralabels[i].set_label(name)
                self.extralabels[i].set_sensitive(True)
                self.extraentries[i].set_text('')
                self.extraentries[i].set_sensitive(True)
            self.extracb.set_label('Radii in q?')
            self.extracb.set_sensitive(True)
        if combo.get_active_text() == 'Azimuthal':
            self.abscissascaling_combo.set_active(-1)
            self.abscissa_combo.set_active(-1)
        else:
            self.abscissa_combo.set_active(0)
            self.abscissascaling_combo.set_active(0)

        for widget in [self.abscissa_combo, self.abscissascaling_combo,
                       self.minabscissa_checkbutton, self.minabscissa_entry,
                       self.maxabscissa_checkbutton, self.maxabscissa_entry]:
            widget.set_sensitive(combo.get_active_text() != 'Azimuthal')
        if combo.get_active_text() != 'Azimuthal':
            self.on_checkbutton_changed(self.minabscissa_checkbutton, self.minabscissa_entry)
            self.on_checkbutton_changed(self.maxabscissa_checkbutton, self.maxabscissa_entry)
        try:
            self.update_from_data(self.get_toplevel().data)
        except AttributeError:
            pass
        return True
    def on_checkbutton_changed(self, cb, entry):
        entry.set_sensitive(cb.get_active())
        return True
    def on_button_clicked(self, button, argument):  # IGNORE:W0613
        data = self.get_toplevel().data
        if data is None:
            return False
        if argument == 'refresh':
            self.update_from_data(data)
        if argument == 'execute':
            if self.intmethod_combo.get_active_text() == 'Azimuthal':
                minradius = float(self.extraentries[0].get_text())
                maxradius = float(self.extraentries[1].get_text())
                radii_in_q = self.extracb.get_active()
                Nbins = int(self.Nbins_entry.get_text())
                curve, retmask = data.azimuthal_average(minradius, maxradius, Nbins, not radii_in_q,
                                                       returnmask=True)
            else:
                minval = float(self.minabscissa_entry.get_text())
                maxval = float(self.maxabscissa_entry.get_text())
                Nbins = int(self.Nbins_entry.get_text())
                spacing = self.abscissascaling_combo.get_active_text()
                if spacing == 'linear':
                    abscissa = np.linspace(minval, maxval, Nbins)
                else:
                    abscissa = np.logspace(np.log10(minval), np.log10(maxval), Nbins)
                radii_in_q = self.abscissa_combo.get_active_text() == 'q'
                if self.intmethod_combo.get_active_text() == 'Full radial':
                    curve, retmask = data.radial_average(abscissa, not radii_in_q, returnmask=True)
                elif self.intmethod_combo.get_active_text() == 'Sector':
                    phi0 = float(self.extraentries[0].get_text()) * np.pi / 180.0
                    dphi = float(self.extraentries[1].get_text()) * np.pi / 180.0
                    curve, retmask = data.sector_average(phi0, dphi, abscissa, not radii_in_q,
                                                symmetric_sector=self.extracb.get_active(), returnmask=True)
                elif self.intmethod_combo.get_active_text() == 'Slice':
                    phi0 = float(self.extraentries[0].get_text()) * np.pi / 180.0
                    width = float(self.extraentries[1].get_text())
                    curve, retmask = data.slice_average(phi0, width, abscissa, not radii_in_q,
                                               symmetric_slice=self.extracb.get_active(), returnmask=True)
            self.emit('integration-done', curve, retmask, self.intmethod_combo.get_active_text(),
                      radii_in_q)
        return True
    def update_from_data(self, data=None):
        if data is None:
            return False
        if self.intmethod_combo.get_active_text() == 'Azimuthal':
            radiiinq = self.extracb.get_active()
            if radiiinq:
                qrange = data.get_qrange()
            else:
                qrange = data.get_pixrange()
            self.extraentries[0].set_text(str(qrange.min()))
            self.extraentries[1].set_text(str(qrange.max()))
            if not self.Nbins_checkbutton.get_active():
                self.Nbins_entry.set_text('100')
        else:
            abscissatype = self.abscissa_combo.get_active_text()
            if abscissatype == 'q':
                absrange = data.get_qrange()
            else:
                absrange = data.get_pixrange()
            if not self.minabscissa_checkbutton.get_active():
                self.minabscissa_entry.set_text(str(absrange.min()))
            if not self.maxabscissa_checkbutton.get_active():
                self.maxabscissa_entry.set_text(str(absrange.max()))
            if not self.Nbins_checkbutton.get_active():
                self.Nbins_entry.set_text(str(len(absrange)))


