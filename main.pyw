import wx
import sys
from gui.main import Aplicacao
from core.log import gravaErro

def excepthook_global(exctype, value, tb):
    import traceback
    mensagem = ''.join(traceback.format_exception(exctype, value, tb))
    gravaErro(mensagem)
    wx.MessageBox(f"Ocorreu um erro fatal:\n{mensagem}", "Erro Crítico", wx.ICON_ERROR)
    sys.exit(1)

if __name__ == '__main__':
    sys.excepthook = excepthook_global
    
    app = Aplicacao(redirect=False)
    app.MainLoop()