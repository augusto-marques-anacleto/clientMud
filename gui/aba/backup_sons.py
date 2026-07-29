from pathlib import Path

import wx

from core.backup import GerenciadorBackup
from core.importer import SoundImporter
from gui.dialogs.import_sounds import DialogoPedeURL, JanelaProgresso

class BackupSonsMixin:
    """Controle de volume e importação/download de pacotes de sons desta aba,
    além da exportação de backup (configurações e personagens)."""

    def alteraVolume(self, tipo, valor):
        if not self.msp.alteraVolume(tipo, valor):
            self.app.fale(f"Volume de {tipo} chegou no limite.")

    def iniciarDownloadSons(self):
        dlg = DialogoPedeURL(self)
        if dlg.ShowModal() == wx.ID_OK:
            url = dlg.campo_url.GetValue().strip()
            if url:
                importer = SoundImporter(self.pasta_sons)
                JanelaProgresso(self, importer, url=url)
        dlg.Destroy()

    def iniciarImportacaoLocal(self):
        estilo = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        dlg = wx.FileDialog(self, "Selecione o arquivo ZIP com os sons", wildcard="Arquivos ZIP (*.zip)|*.zip", style=estilo)
        if dlg.ShowModal() == wx.ID_OK:
            caminho_zip = dlg.GetPath()
            importer = SoundImporter(self.pasta_sons)
            JanelaProgresso(self, importer, caminho_local=caminho_zip)
        dlg.Destroy()

    def ao_exportar_backup(self):
        estilo = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        dlg = wx.FileDialog(self, "Salvar arquivo de Backup", wildcard="Backup MUD (*.mudbak)|*.mudbak", defaultFile="backup.mudbak", style=estilo)
        if dlg.ShowModal() == wx.ID_OK:
            caminho = dlg.GetPath()
            if not caminho.endswith('.mudbak'):
                caminho += '.mudbak'
            gerenciador = GerenciadorBackup(Path.cwd())
            sucesso, mensagem = gerenciador.exportar(caminho)
            icone = wx.ICON_INFORMATION if sucesso else wx.ICON_ERROR
            titulo = "Sucesso" if sucesso else "Erro"
            if sucesso:
                try:
                    self.app.fale("Backup exportado com sucesso!")
                except Exception:
                    pass
            wx.MessageBox(mensagem, titulo, icone)
        dlg.Destroy()
