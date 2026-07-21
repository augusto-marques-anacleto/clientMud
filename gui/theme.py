import sys
import wx

COR_FUNDO = wx.Colour(24, 24, 24)
COR_FUNDO_CAMPO = wx.Colour(45, 45, 45)
COR_TEXTO = wx.Colour(220, 220, 220)

_CONTROLES_CAMPO = (wx.TextCtrl, wx.ListBox, wx.ListCtrl, wx.Choice, wx.ComboBox, wx.SpinCtrl)


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
