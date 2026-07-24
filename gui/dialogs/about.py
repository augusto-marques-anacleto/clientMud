import wx
import webbrowser
from gui.theme import aplica_tema_se_ativo

class DialogoSobre(wx.Dialog):
    def __init__(self, parent, versao):
        super().__init__(parent, title="Sobre o ClientMUD")
        painel = wx.Panel(self)

        wx.StaticText(painel, label="ClientMUD")
        wx.StaticText(painel, label="Cliente de MUD de código aberto.")
        wx.StaticText(painel, label=f"Versão: {versao}")
        wx.StaticText(painel, label="Desenvolvido por: José Augusto")
        wx.StaticText(painel, label="Contribuições, revisões e suporte: Gustavo Barrios")

        btn_repo = wx.Button(painel, label="Abrir repositório no GitHub")
        btn_repo.Bind(wx.EVT_BUTTON, lambda e: webbrowser.open("https://github.com/augusto-marques-anacleto/clientmud/releases/"))

        btn_gustavo = wx.Button(painel, label="GitHub de Gustavo Barrios")
        btn_gustavo.Bind(wx.EVT_BUTTON, lambda e: webbrowser.open("https://github.com/gustavo-barrios2006"))

        btn_fechar = wx.Button(painel, wx.ID_CLOSE, label="Fechar")
        btn_fechar.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_CLOSE))
        self.Bind(wx.EVT_CHAR_HOOK, self._teclaPressionada)
        aplica_tema_se_ativo(self)
        btn_fechar.SetFocus()

    def _teclaPressionada(self, evento):
        if evento.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CLOSE)
        else:
            evento.Skip()
