import wx

class DialogoHistorico(wx.Dialog):
    def __init__(self, parent, title, nome_historico):
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.nome_historico = nome_historico
        painel = wx.Panel(self)
        
        self.texto_ctrl = wx.TextCtrl(painel, style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_DONTWRAP)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down)
        
        conteudo = "\n".join(parent.historicos_customizados.get(self.nome_historico, []))
        self.texto_ctrl.SetValue(conteudo)
        self.texto_ctrl.SetInsertionPointEnd()

    def on_key_down(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
        else:
            event.Skip()

    def adiciona_linha(self, linha):
        self.texto_ctrl.AppendText(linha + '\n')
        self.texto_ctrl.SetInsertionPointEnd()