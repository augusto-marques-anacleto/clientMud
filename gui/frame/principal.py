import threading
from collections import deque

import wx

from core.processor import Processor
from core.external_scripts import GerenciadorScriptsExternos
from gui.dialogs.connection import EVT_RESULTADO_CONEXAO
from gui.theme import aplica_tema_se_ativo
from gui.busca import BuscaEmTexto

from gui.frame.backup_sons import BackupSonsMixin
from gui.frame.comandos import ComandosMixin
from gui.frame.conexao import ConexaoMixin
from gui.frame.config import ConfigMixin
from gui.frame.gerenciadores import GerenciadoresMixin
from gui.frame.gravacao import GravacaoMixin
from gui.frame.historicos import HistoricosMixin
from gui.frame.menu import MenuMixin
from gui.frame.teclas import TeclasMixin

class FramePrincipal(
    MenuMixin,
    ConfigMixin,
    ConexaoMixin,
    ComandosMixin,
    TeclasMixin,
    GravacaoMixin,
    HistoricosMixin,
    GerenciadoresMixin,
    BackupSonsMixin,
    wx.Frame,
):
    """Janela principal do cliente MUD. A implementação é dividida em mixins por
    responsabilidade (menu, configurações, conexão, comandos, teclas, gravação,
    históricos, gerenciadores e backup/sons); esta classe cuida da construção da
    interface e do ciclo de vida da janela."""

    def __init__(self, endereco, json_data=None):
        super().__init__(parent=None, title=f"{endereco} Cliente mud.")
        self.thread_mostra_mud = None
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

        self._defineVariaveis()
        self.menuBar()

        painel = wx.Panel(self)
        self.Bind(wx.EVT_ACTIVATE, self.janelaAtiva)
        self.Bind(wx.EVT_ICONIZE, self.janelaMinimizada)
        self.Bind(wx.EVT_CLOSE, self.fechaApp)
        self.Bind(wx.EVT_CHAR_HOOK, self.teclasPressionadas)
        self.Bind(EVT_RESULTADO_CONEXAO, self._onResultadoConexao)

        wx.StaticText(painel, label="Saída")
        self.saida = wx.TextCtrl(painel, style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_DONTWRAP)
        self.saida.Bind(wx.EVT_SET_FOCUS, self.ganhaFoco)
        self.saida.Bind(wx.EVT_KILL_FOCUS, self.perdeFoco)
        self.saida.Bind(wx.EVT_CHAR, self.detectaTeclas)
        self.saida.Bind(wx.EVT_KEY_DOWN, self.enterNoLink)

        wx.StaticText(painel, label="Entrada")
        self.entrada = wx.TextCtrl(painel, style=wx.TE_PROCESS_ENTER | wx.TE_MULTILINE | wx.TE_DONTWRAP)
        self.entrada.Bind(wx.EVT_TEXT, self.aoDigitarEntrada)
        self.entrada.Bind(wx.EVT_KEY_DOWN, self.verificaConexao)
        self.entrada.Bind(wx.EVT_CHAR_HOOK, self.enviaTexto)
        self.entrada.Bind(wx.EVT_TEXT_PASTE, self.aoColar)

        self._busca_saida = BuscaEmTexto(self.saida, self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.saida, 1, wx.EXPAND)
        sizer.Add(self.entrada, 0, wx.EXPAND)
        painel.SetSizer(sizer)

        aplica_tema_se_ativo(self)

        self.processor = Processor(self.app)
        if not self.thread_mostra_mud or not self.thread_mostra_mud.is_alive():
            self.thread_mostra_mud = threading.Thread(
                target=self.processor.mostraMud,
                daemon=True
            )
            self.thread_mostra_mud.start()
        wx.CallAfter(self.inicia_gerenciador_timers)

        if self.json_personagem and self.json_personagem.get('login_automático'):
            self.realizaLogin()

        self.Show()
        self.entrada.SetFocus()

    def encerraFrame(self):
        conexao_ativa = self.app.client.conexao_ativa
        if conexao_ativa:
            perguntaSaida = wx.MessageDialog(self, "Deseja sair do mud e voltar para a janela principal?", "Sair do Mud", wx.OK | wx.CANCEL | wx.ICON_QUESTION)
            if perguntaSaida.ShowModal() != wx.ID_OK:
                perguntaSaida.Destroy()
                return
            perguntaSaida.Destroy()

        self.janelaFechada = True
        self.app.msp.musicOff()
        self.app.msp.soundOff()

        if conexao_ativa:
            self.app.client.enviaComando("quit")

        def cleanup_assincrono():
            self.app.client.terminaCliente()
            self.para_gerenciador_timers()
            self.gerenciador_scripts_ext.parar_todos()
            if hasattr(self.app, 'script_engine'):
                self.app.script_engine.cancelar_tudo()

        threading.Thread(target=cleanup_assincrono, daemon=True).start()

        wx.CallAfter(self.app.mostraDialogoEntrada)
        self.Destroy()

    def fechaApp(self, evento):
        if self.app.client.conexao_ativa:
            pergunta_saida = wx.MessageDialog(self, 'Encerrar o aplicativo agora irá desconectar do MUD.\nDeseja encerrar?', 'Encerrar aplicativo', wx.YES_NO | wx.ICON_QUESTION)
            if pergunta_saida.ShowModal() != wx.ID_YES:
                pergunta_saida.Destroy()
                return
            pergunta_saida.Destroy()

        self.janelaFechada = True
        self.app.msp.musicOff()
        self.app.msp.soundOff()
        self.app.client.terminaCliente()
        self.para_gerenciador_timers()
        self.gerenciador_scripts_ext.parar_todos()
        if hasattr(self.app, 'script_engine'):
            self.app.script_engine.cancelar_tudo()
        self.Close()
        self.app.ExitMainLoop()
