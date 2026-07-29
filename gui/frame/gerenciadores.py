import subprocess
from pathlib import Path

import wx

from gui.dialogs.about import DialogoSobre
from gui.dialogs.help import JanelaAjuda

class GerenciadoresMixin:
    """Janelas de ajuda/sobre e checagem de atualizações, compartilhadas por
    todas as abas."""

    def abrirAjuda(self, evento=None):
        if getattr(self, '_janela_ajuda', None):
            try:
                self._janela_ajuda.Raise()
                self._janela_ajuda.texto.SetFocus()
                return
            except Exception:
                pass
        self._janela_ajuda = JanelaAjuda(self)
        self._janela_ajuda.Bind(wx.EVT_CLOSE, self._fechaJanelaAjuda)

    def _fechaJanelaAjuda(self, evento):
        self._janela_ajuda = None
        evento.Skip()

    def checarAtualizacoes(self, evento):
        caminho_atualizador = Path('atualizador.exe')
        if caminho_atualizador.exists():
            subprocess.Popen(caminho_atualizador)
            self.app.fale("Verificando atualizações.")
        else:
            wx.MessageBox("O verificador de atualizações não foi encontrado.", "Aviso", wx.ICON_WARNING)
            self.app.fale("Verificador de atualizações não encontrado.")

    def abrirSobre(self, evento):
        try:
            versao = Path('version').read_text(encoding='utf-8').strip()
        except Exception:
            versao = "desconhecida"
        dlg = DialogoSobre(self, versao)
        dlg.ShowModal()
        dlg.Destroy()
