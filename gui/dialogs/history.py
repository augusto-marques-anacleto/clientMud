import wx
from gui.theme import aplica_tema_se_ativo
from gui.busca import BuscaEmTexto

class DialogoHistorico(wx.Dialog):
    def __init__(self, parent, title, nome_historico):
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.nome_historico = nome_historico
        painel = wx.Panel(self)

        self.texto_ctrl = wx.TextCtrl(painel, style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_DONTWRAP)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down)
        self._busca = BuscaEmTexto(self.texto_ctrl, self)

        conteudo = "\n".join(parent.historicos_customizados.get(self.nome_historico, []))
        self.texto_ctrl.SetValue(conteudo)
        self.texto_ctrl.SetInsertionPointEnd()
        aplica_tema_se_ativo(self)

    def on_key_down(self, event):
        codigo = event.GetKeyCode()
        ctrl = event.ControlDown()
        shift = event.ShiftDown()

        if codigo == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
        elif ctrl and shift and codigo == ord('F'):
            self._busca.buscar_proximo()
        elif ctrl and codigo == ord('F'):
            self._busca.abrir_busca()
        else:
            event.Skip()

    def adiciona_linha(self, linha):
        pos_atual = self.texto_ctrl.GetInsertionPoint()
        estava_no_fim = pos_atual >= self.texto_ctrl.GetLastPosition()

        self.texto_ctrl.Freeze()
        try:
            self.texto_ctrl.AppendText(linha + '\n')
            if estava_no_fim:
                self.texto_ctrl.SetInsertionPointEnd()
            else:
                self.texto_ctrl.SetInsertionPoint(pos_atual)
                self.texto_ctrl.ShowPosition(pos_atual)
        finally:
            self.texto_ctrl.Thaw()
