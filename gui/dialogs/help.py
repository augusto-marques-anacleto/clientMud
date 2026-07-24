import wx
from pathlib import Path
from gui.theme import aplica_tema_se_ativo

class JanelaAjuda(wx.Frame):
    def __init__(self, parent):
        super().__init__(parent, title="Ajuda — ClientMUD")
        painel = wx.Panel(self)

        try:
            conteudo = Path('README.md').read_text(encoding='utf-8')
        except Exception:
            conteudo = "Arquivo de ajuda não encontrado."

        self.texto = wx.TextCtrl(painel, value=conteudo, style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_DONTWRAP)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.texto, 1, wx.EXPAND)
        painel.SetSizer(sizer)

        self.Bind(wx.EVT_CHAR_HOOK, self._teclaPressionada)
        self.Bind(wx.EVT_CLOSE, lambda e: self.Destroy())
        self.SetSize(700, 550)
        aplica_tema_se_ativo(self)
        self.texto.SetFocus()
        self.Show()

    def _teclaPressionada(self, evento):
        if evento.GetKeyCode() == wx.WXK_ESCAPE:
            self.Destroy()
        else:
            evento.Skip()
