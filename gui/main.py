import subprocess
import concurrent.futures
from pathlib import Path

import wx
from accessible_output2 import outputs

from models.config import Config, GerenciaPastas, GerenciaPersonagens
from core.asyncio_loop import LoopAsyncioThread
from core.client import Cliente
from core.msp import Msp
from core.script_engine import ScriptEngine
from gui.dialogs.settings import DialogoConfiguracoes
from gui.dialogs.connection import DialogoEntrada
from gui.dialogs.help import JanelaAjuda
from gui.dialogs.about import DialogoSobre
from gui.frame import FramePrincipal

# Reexportado para compatibilidade com importações existentes de gui.main.
__all__ = ['Aplicacao', 'FramePrincipal', 'JanelaAjuda', 'DialogoSobre']

class Aplicacao(wx.App):
    def OnInit(self):
        self.modo_escuro = True
        self.config = Config()
        self.pastas = GerenciaPastas(self.config)
        self.personagem = GerenciaPersonagens(self.config, self.pastas)

        if not self.config.config:
            mensagem_configuracao = wx.MessageDialog(
                None,
                'Bem-vindo.\nPara começar, é necessário realizar algumas configurações iniciais.',
                "Primeira Inicialização",
                wx.OK | wx.ICON_INFORMATION
            )
            mensagem_configuracao.SetOKLabel("Iniciar Configuração")
            mensagem_configuracao.ShowModal()
            mensagem_configuracao.Destroy()

            dialogo = DialogoConfiguracoes()
            dialogo.ShowModal()
            dialogo.Destroy()
            return False

        if self.config.config['gerais'].get('verifica-atualizacoes-automaticamente', True):
            caminho_atualizador = Path('atualizador.exe')
            if caminho_atualizador.exists():
                subprocess.Popen(caminho_atualizador)

        self.pastas.criaPastaGeral()
        self._carregaModulos()
        self.mostraDialogoEntrada()
        return True

    def _carregaModulos(self):
        self.async_loop = LoopAsyncioThread()
        self.async_loop.start()
        self.client = Cliente(self.async_loop)
        self.msp = Msp()
        saida = outputs.auto.Auto()
        self.fale = saida.speak
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self.script_engine = ScriptEngine(self.async_loop)
        self.script_engine.set_app(self)

    def mostraDialogoEntrada(self):
        janela_inicial = DialogoEntrada(None)
        janela_inicial.ShowModal()
        janela_inicial.Destroy()

    def iniciaJanelaMud(self, dados):
        if dados['json_personagem']:
            frame = FramePrincipal(dados['json_personagem']['nome'], dados['json_personagem'])
        else:
            self.config.config['gerais']['ultima-conexao'] = [dados["endereco"], dados["porta"], dados.get("ssl", False), dados.get("modo_escuro", True)]
            self.config.atualizaJson()
            frame = FramePrincipal(dados['endereco'])

        self.janela_principal = frame
        self.SetTopWindow(frame)
