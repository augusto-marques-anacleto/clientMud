from pathlib import Path

import wx

from core.backup import GerenciadorBackup
from gui.reinicio import reinicia_aplicativo

class BackupSonsMixin:
    """Importação de backup (configurações e personagens), que reinicia o
    aplicativo inteiro e por isso é tratada em nível de janela."""

    def ao_importar_backup(self, evento):
        estilo = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        dlg = wx.FileDialog(self, "Selecione o arquivo de Backup", wildcard="Backup MUD (*.mudbak)|*.mudbak", style=estilo)

        if dlg.ShowModal() == wx.ID_OK:
            caminho = dlg.GetPath()
            gerenciador = GerenciadorBackup(Path.cwd())
            sucesso, mensagem = gerenciador.importar(caminho)

            icone = wx.ICON_INFORMATION if sucesso else wx.ICON_ERROR
            titulo = "Sucesso" if sucesso else "Erro"

            if sucesso:
                wx.MessageBox("Backup restaurado com sucesso! O aplicativo será reiniciado automaticamente.", "Sucesso", wx.ICON_INFORMATION)
                reinicia_aplicativo()
            else:
                wx.MessageBox(mensagem, titulo, icone)
        dlg.Destroy()
