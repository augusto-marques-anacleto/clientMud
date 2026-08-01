import threading
from collections import deque

import wx

from core.client import Cliente
from core.msp import Msp
from core.processor import Processor
from core.script_engine import ScriptEngine
from core.external_scripts import GerenciadorScriptsExternos
from gui.dialogs.connection import EVT_RESULTADO_CONEXAO
from gui.busca import BuscaEmTexto

from gui.aba.backup_sons import BackupSonsMixin
from gui.aba.comandos import ComandosMixin
from gui.aba.conexao import ConexaoMixin
from gui.aba.config import ConfigMixin
from gui.aba.gerenciadores import GerenciadoresMixin
from gui.aba.gravacao import GravacaoMixin
from gui.aba.historicos import HistoricosMixin
from gui.aba.teclas import TeclasMixin

class PainelSessaoMud(
    ConfigMixin,
    ConexaoMixin,
    ComandosMixin,
    TeclasMixin,
    GravacaoMixin,
    HistoricosMixin,
    GerenciadoresMixin,
    BackupSonsMixin,
    wx.Panel,
):
    """Uma aba do cliente MUD: uma conexão independente, com seu próprio
    client/msp/script_engine e configurações. A implementação é dividida em
    mixins por responsabilidade (config, conexão, comandos, teclas, gravação,
    históricos, gerenciadores e backup/sons); esta classe cuida da construção
    da interface e do ciclo de vida da aba."""

    def __init__(self, parent, frame_principal, endereco, json_data=None):
        super().__init__(parent)
        self.frame_principal = frame_principal
        self.app = wx.GetApp()
        self.json_personagem = json_data
        self.nome = endereco
        self.janelaFechada = False
        self.janelaAtivada = True
        self.saidaFoco = False
        self.triggers = []
        self.keys = []
        self.timers = []
        self.macros = []
        self.gerenciador_timers = None
        self.gerenciador_scripts_ext = GerenciadorScriptsExternos()
        self.historicos_customizados = {}
        self.historicos_abertos = {}
        self.comandos = deque(maxlen=99)
        self.indexComandos = len(self.comandos)
        self.rascunho = ''
        self._aguardando_conexao = False
        self._atualizando_entrada = False
        self._gravando_macro = False
        self._macro_pausada = False
        self._comandos_gravados = []

        self.client = Cliente(self.app.async_loop)
        self.msp = Msp()
        self.script_engine = ScriptEngine(self.app.async_loop)
        self.script_engine.set_app(self)
        self.processor = Processor(self)
        self.thread_mostra_mud = None

        self._defineVariaveis()

        self.msp.definePastaSons(self.pasta_sons)
        self.client.definePastaLog(str(self.pasta_logs), self.nome)

        self.Bind(wx.EVT_CHAR_HOOK, self.teclasPressionadas)
        # source=self é essencial aqui: EVT_WINDOW_DESTROY se propaga de janelas filhas para a
        # janela pai (ex.: o Frame de progresso do download de sons, que tem esta aba como parent).
        # Sem o filtro, destruir qualquer janela filha desta aba disparava aoFecharAba também para
        # ela, perguntando se o usuário queria fechar a aba/desconectar do MUD sem motivo nenhum.
        self.Bind(wx.EVT_WINDOW_DESTROY, self.aoFecharAba, source=self)
        self.Bind(EVT_RESULTADO_CONEXAO, self._onResultadoConexao)

        wx.StaticText(self, label="Saída")
        self.saida = wx.TextCtrl(self, style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_DONTWRAP)
        self.saida.Bind(wx.EVT_SET_FOCUS, self.ganhaFoco)
        self.saida.Bind(wx.EVT_KILL_FOCUS, self.perdeFoco)
        self.saida.Bind(wx.EVT_CHAR, self.detectaTeclas)
        self.saida.Bind(wx.EVT_KEY_DOWN, self.enterNoLink)

        wx.StaticText(self, label="Entrada")
        self.entrada = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER | wx.TE_MULTILINE | wx.TE_DONTWRAP)
        self.entrada.Bind(wx.EVT_TEXT, self.aoDigitarEntrada)
        self.entrada.Bind(wx.EVT_KEY_DOWN, self.verificaConexao)
        self.entrada.Bind(wx.EVT_CHAR_HOOK, self.enviaTexto)
        self.entrada.Bind(wx.EVT_TEXT_PASTE, self.aoColar)

        self._busca_saida = BuscaEmTexto(self.saida, self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.saida, 1, wx.EXPAND)
        sizer.Add(self.entrada, 0, wx.EXPAND)
        self.SetSizer(sizer)

        if not self.thread_mostra_mud or not self.thread_mostra_mud.is_alive():
            self.thread_mostra_mud = threading.Thread(
                target=self.processor.mostraMud,
                daemon=True
            )
            self.thread_mostra_mud.start()
        wx.CallAfter(self.inicia_gerenciador_timers)

        if self.json_personagem and self.json_personagem.get('login_automático'):
            self.realizaLogin()

    def aoFecharAba(self, evento=None):
        if self.janelaFechada:
            if evento: evento.Skip()
            return
        conexao_ativa = self.client.conexao_ativa
        if conexao_ativa and not getattr(self.frame_principal, 'fechando_tudo', False):
            perguntaSaida = wx.MessageDialog(self, "Deseja fechar esta aba e desconectar deste mud?", "Fechar Aba", wx.OK | wx.CANCEL | wx.ICON_QUESTION)
            if perguntaSaida.ShowModal() != wx.ID_OK:
                perguntaSaida.Destroy()
                if evento and hasattr(evento, 'Veto'):
                    evento.Veto()
                return
            perguntaSaida.Destroy()

        self.janelaFechada = True
        self.msp.musicOff()
        self.msp.soundOff()

        if conexao_ativa:
            self.client.enviaComando("quit")

        def cleanup_assincrono():
            self.client.terminaCliente()
            self.para_gerenciador_timers()
            self.gerenciador_scripts_ext.parar_todos()
            if hasattr(self, 'script_engine'):
                self.script_engine.cancelar_tudo()

        threading.Thread(target=cleanup_assincrono, daemon=True).start()

        if evento and not getattr(self.frame_principal, 'fechando_tudo', False):
            evento.Skip()
