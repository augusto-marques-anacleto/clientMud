import sys
import wx

COR_FUNDO = wx.Colour(24, 24, 24)
COR_FUNDO_CAMPO = wx.Colour(45, 45, 45)
COR_TEXTO = wx.Colour(220, 220, 220)

_CONTROLES_CAMPO = (wx.TextCtrl, wx.ListBox, wx.ListCtrl, wx.Choice, wx.ComboBox, wx.SpinCtrl)


if wx.Platform == '__WXMSW__':
    class _AcessivelCaixaSelecao(wx.Accessible):
        """Restaura o papel de caixa de seleção para o leitor de tela.

        No Windows, ao aplicar cores personalizadas (modo escuro) em um
        wx.CheckBox, o wxWidgets passa a desenhá-lo por conta própria
        (owner-drawn). Nesse modo o controle é exposto ao leitor de tela como
        um botão comum, perdendo o papel de caixa de seleção e o anúncio
        automático de marcado/desmarcado. Esta classe informa novamente o
        papel e o estado corretos, sem alterar nada visualmente.
        """

        def GetRole(self, childId):
            return (wx.ACC_OK, wx.ROLE_SYSTEM_CHECKBUTTON)

        def GetState(self, childId):
            estado = wx.ACC_STATE_SYSTEM_FOCUSABLE
            caixa = self.GetWindow()
            if caixa:
                if caixa.HasFocus():
                    estado |= wx.ACC_STATE_SYSTEM_FOCUSED
                if caixa.Is3State() and caixa.Get3StateValue() == wx.CHK_UNDETERMINED:
                    estado |= wx.ACC_STATE_SYSTEM_MIXED
                elif caixa.IsChecked():
                    estado |= wx.ACC_STATE_SYSTEM_CHECKED
            return (wx.ACC_OK, estado)


def corrige_acessibilidade_checkbox(caixa):
    """Faz o leitor de tela ler a caixa de seleção como caixa, não como botão."""
    if wx.Platform != '__WXMSW__':
        return
    try:
        caixa.SetAccessible(_AcessivelCaixaSelecao())
    except Exception:
        pass


def modo_escuro_ativo():
    app = wx.GetApp()
    return bool(app) and bool(getattr(app, 'modo_escuro', False))


def aplica_tema_se_ativo(janela):
    if modo_escuro_ativo():
        aplica_tema_escuro(janela)


def aplica_tema_escuro(janela):
    _coloreControle(janela)
    for filho in janela.GetChildren():
        aplica_tema_escuro(filho)
    if isinstance(janela, (wx.Dialog, wx.Frame)):
        _escureceBarraTitulo(janela)
        janela.Refresh()


def _coloreControle(janela):
    try:
        if isinstance(janela, _CONTROLES_CAMPO):
            janela.SetBackgroundColour(COR_FUNDO_CAMPO)
            janela.SetForegroundColour(COR_TEXTO)
            if isinstance(janela, wx.ListCtrl):
                janela.SetTextColour(COR_TEXTO)
        else:
            janela.SetBackgroundColour(COR_FUNDO)
            janela.SetForegroundColour(COR_TEXTO)
            if isinstance(janela, wx.CheckBox):
                corrige_acessibilidade_checkbox(janela)
    except Exception:
        pass


def _escureceBarraTitulo(janela):
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        handle = janela.GetHandle()
        if not handle:
            return
        valor = ctypes.c_int(1)
        for atributo in (20, 19):
            resultado = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(handle), atributo, ctypes.byref(valor), ctypes.sizeof(valor)
            )
            if resultado == 0:
                break
    except Exception:
        pass
