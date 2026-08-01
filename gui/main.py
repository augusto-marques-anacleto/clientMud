import subprocess
import concurrent.futures
from pathlib import Path

import wx

from models.config import Config, GerenciaPastas, GerenciaPersonagens
from core.asyncio_loop import LoopAsyncioThread
from core.sistema import cria_saida_voz, cria_leitor_de_mensagens
from gui.dialogs.settings import DialogoConfiguracoes
from gui.dialogs.connection import DialogoEntrada
from gui.frame import FramePrincipal

# Reexportado para compatibilidade com importações existentes de gui.main.
__all__ = ['Aplicacao', 'FramePrincipal']

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
        self.recarrega_saida_voz()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

    def recarrega_saida_voz(self):
        """(Re)cria as saídas de fala a partir das preferências salvas em
        gerais.voz-linux. Chamado ao iniciar e sempre que a tela de
        sintetizador (Linux) salva alterações, para aplicar sem precisar
        reiniciar o aplicativo."""
        preferencias_linux = self.config.config.get('gerais', {}).get('voz-linux') if self.config.config else None
        saida = cria_saida_voz(preferencias_linux)
        self.fale = saida.speak
        self.fala_mud = cria_leitor_de_mensagens(saida, preferencias_linux)

    def mostraDialogoEntrada(self):
        janela_inicial = DialogoEntrada(None)
        janela_inicial.ShowModal()
        janela_inicial.Destroy()

    def iniciaJanelaMud(self, dados):
        if not hasattr(self, 'janela_principal') or not self.janela_principal:
            self.janela_principal = FramePrincipal()
            self.SetTopWindow(self.janela_principal)
            self.janela_principal.Show()

        self.janela_principal.nova_aba_conexao(dados)

        if not dados.get('json_personagem'):
            self.config.config['gerais']['ultima-conexao'] = [dados["endereco"], dados["porta"], dados.get("ssl", False), dados.get("modo_escuro", True)]
            self.config.atualizaJson()
