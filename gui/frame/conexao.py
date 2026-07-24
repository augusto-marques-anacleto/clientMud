import wx
import threading
from gui.dialogs.connection import ThreadIniciaConexao

class ConexaoMixin:
    """Ciclo de conexão/reconexão com o MUD e login automático."""

    def realizaLogin(self):
        self.app.client.enviaComando(self.json_personagem.get('nome'))
        self.app.client.enviaComando(self.json_personagem.get('senha'))

    def _iniciarConexaoThread(self, endereco, porta, usar_ssl=False):
        if self._aguardando_conexao: return
        self._aguardando_conexao = True
        try:
            self.app.client.terminaCliente()
        except Exception:
            pass
        self.processor.reiniciaFilas()
        self.saida.Clear()
        self.comandos.clear()
        self.indexComandos = len(self.comandos)
        self.saida.AppendText(f"Conectando em {endereco}:{porta}...\n")
        self.app.fale("Conectando")
        ThreadIniciaConexao(self, (endereco, porta, usar_ssl), self.app, self.json_personagem).start()

    def _onResultadoConexao(self, evento):
        self._aguardando_conexao = False
        if evento.tentativa_conexao:
            if not self.thread_mostra_mud or not self.thread_mostra_mud.is_alive():
                self.thread_mostra_mud = threading.Thread(
                    target=self.processor.mostraMud,
                    daemon=True
                )
                self.thread_mostra_mud.start()
            self.inicia_gerenciador_timers()
            self.inicia_scripts_externos()
            if self.login:
                self.realizaLogin()
            self.entrada.SetFocus()
        else:
            self.saida.AppendText("Falha ao reconectar.\n")
            self.app.fale("Falha ao reconectar")

    def reconecta(self):
        endereco = self.app.client.endereco
        porta = self.app.client.porta
        usar_ssl = self.app.client.ssl_ativo
        if not endereco or not porta:
            if self.json_personagem:
                endereco = self.json_personagem.get('endereço')
                porta = self.json_personagem.get('porta')
                usar_ssl = self.json_personagem.get('conexao_segura', False)
            elif self.app.config.config['gerais'].get('ultima-conexao'):
                ultima = self.app.config.config['gerais']['ultima-conexao']
                endereco, porta = ultima[0], ultima[1]
                usar_ssl = bool(ultima[2]) if len(ultima) > 2 else False
        if endereco and porta:
            self._iniciarConexaoThread(endereco, porta, usar_ssl)

    def perguntaReconexao(self):
        if self.janelaFechada: return
        dlg = wx.MessageDialog(self, 'Deseja se reconectar?', 'Conexão finalizada', wx.YES_NO | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_YES:
            self.reconecta()
        else:
            self.focaSaida()
        dlg.Destroy()

    def verificaConexao(self, evento):
        if evento.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and not self.app.client.conexao_ativa:
            self.perguntaReconexao()
            return
        evento.Skip()
