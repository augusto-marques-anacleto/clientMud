import wx

class TeclasMixin:
    """Atalhos globais da janela principal e encerramento do aplicativo."""

    def teclasPressionadas(self, evento):
        codigo = evento.GetKeyCode()
        ctrl = evento.ControlDown()
        shift = evento.ShiftDown()
        alt = evento.AltDown()

        if ctrl and not shift and not alt and codigo == ord('N'):
            self.app.mostraDialogoEntrada()
            return

        evento.Skip()

    def fechaApp(self, evento):
        self.fechando_tudo = True
        for aba in self.abas_abertas:
            aba.aoFecharAba(wx.CloseEvent())

        self.Destroy()
        self.app.ExitMainLoop()
