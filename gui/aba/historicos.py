import wx

from gui.dialogs.history import DialogoHistorico

class HistoricosMixin:
    """Históricos customizados alimentados por triggers/scripts e exibidos em
    janelas próprias, específicos desta aba."""

    def adiciona_ao_historico_customizado(self, nome_historico, linha):
        if nome_historico not in self.historicos_customizados:
            self.historicos_customizados[nome_historico] = []
        self.historicos_customizados[nome_historico].append(linha)
        if nome_historico in self.historicos_abertos:
            dlg = self.historicos_abertos[nome_historico]
            if dlg: wx.CallAfter(dlg.adiciona_linha, linha)

    def mostra_historico(self, nome_historico):
        if nome_historico in self.historicos_abertos:
            self.historicos_abertos[nome_historico].Raise()
            return
        dlg = DialogoHistorico(self, title=f"Histórico: {nome_historico}", nome_historico=nome_historico)
        self.historicos_abertos[nome_historico] = dlg
        dlg.ShowModal()
        if nome_historico in self.historicos_abertos:
            del self.historicos_abertos[nome_historico]
        dlg.Destroy()

    def _abre_historico_pelo_atalho(self):
        nomes = list(self.historicos_customizados.keys())
        if len(nomes) == 1:
            self.mostra_historico(nomes[0])
        elif len(nomes) > 1:
            dlg = wx.SingleChoiceDialog(self, "Escolha o histórico:", "Históricos", nomes)
            if dlg.ShowModal() == wx.ID_OK:
                self.mostra_historico(dlg.GetStringSelection())
            dlg.Destroy()
