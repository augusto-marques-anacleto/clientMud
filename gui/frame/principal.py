import wx

from gui.theme import aplica_tema_se_ativo

from gui.frame.abas import AbasMixin
from gui.frame.backup_sons import BackupSonsMixin
from gui.frame.gerenciadores import GerenciadoresMixin
from gui.frame.menu import MenuMixin
from gui.frame.teclas import TeclasMixin

class FramePrincipal(
    MenuMixin,
    AbasMixin,
    TeclasMixin,
    GerenciadoresMixin,
    BackupSonsMixin,
    wx.Frame,
):
    """Janela principal do cliente MUD: hospeda o notebook com as abas de
    conexão e a barra de menus compartilhada. A implementação é dividida em
    mixins por responsabilidade (menu, gestão de abas, teclas, ajuda/sobre e
    backup); esta classe cuida da construção da interface."""

    def __init__(self):
        super().__init__(parent=None, title="ClientMUD")
        self.app = wx.GetApp()
        self.abas_abertas = []

        painel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.notebook = wx.Notebook(painel)
        sizer.Add(self.notebook, 1, wx.EXPAND)
        painel.SetSizer(sizer)

        self.menuBar()

        self.Bind(wx.EVT_CLOSE, self.fechaApp)
        self.Bind(wx.EVT_CHAR_HOOK, self.teclasPressionadas)
        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.aoTrocarAba)
        aplica_tema_se_ativo(self)

        self.SetSize(800, 600)
