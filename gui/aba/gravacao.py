import wx

class GravacaoMixin:
    """Gravação de macros a partir dos comandos digitados durante a sessão."""

    def inicia_gravacao(self):
        self._gravando_macro = True
        self._macro_pausada = False
        self._comandos_gravados = []
        self.app.fale("Gravação iniciada. Todos os comandos serão registrados.")

    def pausa_retoma_gravacao(self):
        self._macro_pausada = not self._macro_pausada
        if self._macro_pausada:
            self.app.fale("Gravação pausada.")
        else:
            self.app.fale("Gravação retomada.")

    def ignora_ultimo_comando(self):
        if self._comandos_gravados:
            removido = self._comandos_gravados.pop()
            self.app.fale(f"Comando ignorado: {removido}")
        else:
            self.app.fale("Nenhum comando gravado para ignorar.")

    def interrompe_gravacao(self):
        self._gravando_macro = False
        if not self._comandos_gravados:
            self.app.fale("Gravação interrompida. Nenhum comando foi registrado.")
            return
        from gui.dialogs.macros import DialogoAcaoGravacao, DialogoEditaMacro
        dlg = DialogoAcaoGravacao(self, self._comandos_gravados)
        if dlg.ShowModal() == wx.ID_OK:
            acao = dlg.acao_escolhida
            if acao == 'adicionar':
                comandos_str = dlg.comandos_str_ponto_virgula
                dlg_edita = DialogoEditaMacro(self, comandos_iniciais=comandos_str)
                if dlg_edita.ShowModal() == wx.ID_OK:
                    self.macros.insert(0, dlg_edita.get_macro())
                    self.salvaConfiguracoesPersonagem()
                    self.app.fale("Macro adicionada com sucesso.")
                dlg_edita.Destroy()
        dlg.Destroy()
        self._comandos_gravados = []
