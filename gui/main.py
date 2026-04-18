import wx
import os
import sys
import subprocess
import threading
import time
from pathlib import Path
from collections import deque
import concurrent.futures
import webbrowser
import re
from accessible_output2 import outputs

from models.config import Config, GerenciaPastas, GerenciaPersonagens
from core.asyncio_loop import LoopAsyncioThread
from core.client import Cliente
from core.msp import Msp
from core.processor import Processor
from core.backup import GerenciadorBackup
from core.importer import SoundImporter
from gui.dialogs.settings import DialogoConfiguracoes
from gui.dialogs.connection import DialogoEntrada, DialogoConectando, EVT_RESULTADO_CONEXAO, ThreadIniciaConexao
from gui.dialogs.triggers import DialogoGerenciaTriggers
from gui.dialogs.timers import DialogoGerenciaTimers, GerenciadorTimers
from gui.dialogs.keys import DialogoGerenciaKeys
from gui.dialogs.history import DialogoHistorico
from gui.dialogs.import_sounds import DialogoPedeURL, JanelaProgresso

_RE_CMD_REPEAT = re.compile(r'^#(\d+)\s+(.+)')

class JanelaAjuda(wx.Frame):
    def __init__(self, parent):
        super().__init__(parent, title="Ajuda — ClientMUD")
        painel = wx.Panel(self)

        try:
            conteudo = Path('README.md').read_text(encoding='utf-8')
        except Exception:
            conteudo = "Arquivo de ajuda não encontrado."

        self.texto = wx.TextCtrl(painel, value=conteudo, style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_DONTWRAP)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.texto, 1, wx.EXPAND)
        painel.SetSizer(sizer)

        self.Bind(wx.EVT_CHAR_HOOK, self._teclaPressionada)
        self.Bind(wx.EVT_CLOSE, lambda e: self.Destroy())
        self.SetSize(700, 550)
        self.texto.SetFocus()
        self.Show()

    def _teclaPressionada(self, evento):
        if evento.GetKeyCode() == wx.WXK_ESCAPE:
            self.Destroy()
        else:
            evento.Skip()

class DialogoSobre(wx.Dialog):
    def __init__(self, parent, versao):
        super().__init__(parent, title="Sobre o ClientMUD")
        painel = wx.Panel(self)

        wx.StaticText(painel, label="ClientMUD")
        wx.StaticText(painel, label="Cliente de MUD de código aberto.")
        wx.StaticText(painel, label=f"Versão: {versao}")
        wx.StaticText(painel, label="Desenvolvido por: José Augusto")
        wx.StaticText(painel, label="Contribuições, revisões e suporte: Gustavo Barrios")

        btn_repo = wx.Button(painel, label="Abrir repositório no GitHub")
        btn_repo.Bind(wx.EVT_BUTTON, lambda e: webbrowser.open("https://github.com/augusto-marques-anacleto/clientmud/releases/"))

        btn_gustavo = wx.Button(painel, label="GitHub de Gustavo Barrios")
        btn_gustavo.Bind(wx.EVT_BUTTON, lambda e: webbrowser.open("https://github.com/gustavo-barrios2006"))

        btn_fechar = wx.Button(painel, wx.ID_CLOSE, label="Fechar")
        btn_fechar.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_CLOSE))
        self.Bind(wx.EVT_CHAR_HOOK, self._teclaPressionada)
        btn_fechar.SetFocus()

    def _teclaPressionada(self, evento):
        if evento.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CLOSE)
        else:
            evento.Skip()

class FramePrincipal(wx.Frame):
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

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.saida, 1, wx.EXPAND)
        sizer.Add(self.entrada, 0, wx.EXPAND)
        painel.SetSizer(sizer)

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

    def enterNoLink(self, evento):
        if evento.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            posicao = self.saida.GetInsertionPoint()
            valores = self.saida.PositionToXY(posicao)
            linha_idx = valores[2] 
            
            texto_linha = self.saida.GetLineText(linha_idx)
            
            padrao_url = re.compile(r'(https?://[^\s]+)')
            match = padrao_url.search(texto_linha)
            
            if match:
                webbrowser.open(match.group(1))
                return
        evento.Skip()

    def _defineVariaveis(self):
        self.pasta_geral = str(Path(self.app.config.config['gerais']['diretorio-de-dados']) / "clientmud")
        self.nome_mud = None
        self._chave_personagem = None
        if self.json_personagem:
            self.nome = self.json_personagem['nome']
            self.senha = self.json_personagem.get('senha')
            self.reproduzirSons = self.json_personagem.get('reproduzir_sons_fora_janela', True)
            self.lerMensagens = self.json_personagem.get('ler_fora_janela', False)
            self.login = self.json_personagem.get('login_automático', False)
            self.usar_volume_padrao = self.json_personagem.get('usar_volume_padrao', False)
            self.volume_padrao = self.json_personagem.get('volume_padrao', 100)

            chave = self.json_personagem.get('_chave')
            pastas = self.app.config.config['gerais']['pastas-dos-muds']
            if not chave or chave not in pastas:
                mud_hint = self.json_personagem.get('mud', '')
                if mud_hint:
                    candidata = f"{self.nome}@{mud_hint}"
                    if candidata in pastas:
                        chave = candidata
                if not chave or chave not in pastas:
                    for k in pastas:
                        if (k.split('@')[0] if '@' in k else k) == self.nome:
                            chave = k
                            break
                if chave:
                    self.json_personagem['_chave'] = chave
            self._chave_personagem = chave

            if not chave or chave not in pastas:
                self.pasta_logs = Path(self.pasta_geral) / 'logs'
                self.pasta_scripts = Path(self.pasta_geral) / 'scripts'
                self.pasta_sons = Path(self.pasta_geral) / 'sons'
                return

            pasta_base_personagem = Path(pastas[chave])
            self.nome_mud = pasta_base_personagem.parent.name
            self.pasta_personagem = pasta_base_personagem
            self.pasta_logs = pasta_base_personagem / 'logs'
            self.pasta_scripts = pasta_base_personagem / 'scripts'
            self.pasta_sons = pasta_base_personagem.parent / 'sons'
        else:
            self.pasta_logs = Path(self.pasta_geral) / 'logs'
            self.pasta_scripts = Path(self.pasta_geral) / 'scripts'
            self.pasta_sons = Path(self.pasta_geral) / 'sons'
            self.reproduzirSons = self.app.config.config['gerais'].get('toca-sons-fora-da-janela', True)
            self.lerMensagens = self.app.config.config['gerais'].get('ler fora da janela', True)
            self.login = False
            self.usar_volume_padrao = False
            self.volume_padrao = 100
            
        self.carregaTriggers()
        self.carregaTimers()
        self.carregaKeys()
        self.carregaMacros()

    def realizaLogin(self):
        self.app.client.enviaComando(self.json_personagem.get('nome'))
        self.app.client.enviaComando(self.json_personagem.get('senha'))

    def _iniciarConexaoThread(self, endereco, porta):
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
        ThreadIniciaConexao(self, (endereco, porta), self.app, self.json_personagem).start()

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
            if self.login:
                self.realizaLogin()
            self.entrada.SetFocus()
        else:
            self.saida.AppendText("Falha ao reconectar.\n")
            self.app.fale("Falha ao reconectar")

    def _setEntradaValor(self, texto=None, limpar=False):
        self._atualizando_entrada = True
        try:
            if limpar: self.entrada.Clear()
            elif texto is not None: self.entrada.SetValue(texto)
            self.entrada.SetInsertionPointEnd()
        finally:
            self._atualizando_entrada = False

    def aoDigitarEntrada(self, evento):
        if getattr(self, '_atualizando_entrada', False):
            evento.Skip()
            return
        total = len(self.comandos)
        if self.indexComandos >= total:
            self.rascunho = self.entrada.GetValue()
            if self.indexComandos > total and self.rascunho != '':
                self.indexComandos = total
        evento.Skip()

    def comandoAnterior(self):
        total = len(self.comandos)
        if self.indexComandos > total + 1: self.indexComandos = total + 1
        if self.indexComandos > total:
            self.indexComandos = total
            self._setEntradaValor(self.rascunho)
            return
        if self.indexComandos == total:
            self.rascunho = self.entrada.GetValue()
            if total <= 0:
                self.entrada.SetInsertionPointEnd()
                return
            self.indexComandos = total - 1
            self._setEntradaValor(self.comandos[self.indexComandos])
            return
        if self.indexComandos <= 0: return
        self.indexComandos -= 1
        self._setEntradaValor(self.comandos[self.indexComandos])

    def proximoComando(self):
        total = len(self.comandos)
        if self.indexComandos < 0: self.indexComandos = 0
        if self.indexComandos > total + 1: self.indexComandos = total + 1
        if self.indexComandos == total:
            self.rascunho = self.entrada.GetValue()
            self.indexComandos = total + 1
            self._setEntradaValor(limpar=True)
            return
        if self.indexComandos > total:
            self.entrada.SetInsertionPointEnd()
            return
        self.indexComandos += 1
        if self.indexComandos == total:
            self._setEntradaValor(self.rascunho)
        else:
            self._setEntradaValor(self.comandos[self.indexComandos])

    def _desdobra_e_envia(self, texto):
        match = _RE_CMD_REPEAT.match(texto)
        if match:
            qtd = min(int(match.group(1)), 100)
            cmd = match.group(2).strip()
            for _ in range(qtd):
                self.app.client.enviaComando(cmd)
        else:
            self.app.client.enviaComando(texto)

    def processa_e_envia_comando(self, comando):
        comando = comando.strip()
        if not comando:
            self.app.client.enviaComando("")
            return

        match = _RE_CMD_REPEAT.match(comando)
        if match:
            qtd = min(int(match.group(1)), 100)
            cmd_base = match.group(2).strip()
        else:
            qtd = 1
            cmd_base = comando

        macro_encontrada = None
        for m in self.macros:
            if getattr(m, 'ativo', True) and m.nome == cmd_base:
                macro_encontrada = m
                break

        todos_comandos = []
        if not macro_encontrada and qtd == 1:
            self._desdobra_e_envia(cmd_base)
        else:
            for _ in range(qtd):
                if macro_encontrada:
                    for parte in macro_encontrada.comandos.split(';'):
                        parte_limpa = parte.strip()
                        if parte_limpa:
                            todos_comandos.append({parte_limpa: macro_encontrada.espera})
                else:
                    todos_comandos.append({cmd_base: 0.1})
        if 0 < len(todos_comandos) < 10:
            for comando in todos_comandos:
                for cmd, espera in comando.items():
                    self._desdobra_e_envia(cmd)
        elif len(todos_comandos) >= 10:
            threading.Thread(target=self._thread_envia_macro, args=(todos_comandos,), daemon=True).start()

    def enviaTexto(self, evento):
        cod = evento.GetKeyCode()
        mod = evento.GetModifiers()
        if cod in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and (mod == wx.MOD_SHIFT or mod == wx.MOD_NONE):
            if not self.app.client.conexao_ativa:
                self.perguntaReconexao()
                return
            texto_bruto = self.entrada.GetValue()
            texto_limpo = texto_bruto.strip()
            if not texto_limpo: 
                self.processa_e_envia_comando("")
            else:
                self.adicionaComandoLista(texto_limpo)
                for cmd in texto_limpo.split(';'):
                    cmd_limpo = cmd.strip()
                    if self._gravando_macro and not self._macro_pausada:
                        self._comandos_gravados.append(cmd_limpo)
                    self.processa_e_envia_comando(cmd_limpo)
            if mod == wx.MOD_NONE:
                self.rascunho = ''
                self.indexComandos = len(self.comandos)
                self._setEntradaValor(limpar=True)
            else: 
                self.indexComandos = len(self.comandos)
                self.entrada.SetInsertionPointEnd()
            return
        if cod == wx.WXK_UP:
            self.comandoAnterior()
            return
        if cod == wx.WXK_DOWN:
            self.proximoComando()
            return
        evento.Skip()

    def adicionaComandoLista(self, comando):
        self.comandos.append(comando)

    def aoColar(self, evento):
        if not wx.TheClipboard.Open(): return
        if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT)):
            data = wx.TextDataObject()
            wx.TheClipboard.GetData(data)
            self.entrada.WriteText(data.GetText().strip())
        else:
            evento.Skip()
        wx.TheClipboard.Close()

    def ganhaFoco(self, evento):
        self.saidaFoco = True
        evento.Skip()

    def perdeFoco(self, evento):
        self.saida.SetInsertionPointEnd()
        self.saidaFoco = False
        self.entrada.SetInsertionPointEnd()
        evento.Skip()

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

        if conexao_ativa:
            self.app.client.enviaComando("quit")
            
        def cleanup_assincrono():
            self.app.client.terminaCliente()
            self.para_gerenciador_timers()
            
        threading.Thread(target=cleanup_assincrono, daemon=True).start()
        
        wx.CallAfter(self.app.mostraDialogoEntrada)
        self.Destroy()

    def teclasPressionadas(self, evento):
        codigo = evento.GetKeyCode()
        if codigo == wx.WXK_ESCAPE:
            self.encerraFrame()
            return
            
        if self.saidaFoco:
            u = evento.GetUnicodeKey()
            if not (evento.ControlDown() or evento.AltDown()):
                if 32 <= u <= 126:
                    evento.Skip()
                    return
                    
        teclas_bloqueadas = {
            wx.WXK_TAB, wx.WXK_UP, wx.WXK_DOWN, wx.WXK_LEFT, wx.WXK_RIGHT,
            wx.WXK_HOME, wx.WXK_END, wx.WXK_PAGEUP, wx.WXK_PAGEDOWN,
            wx.WXK_INSERT, wx.WXK_DELETE, wx.WXK_BACK, wx.WXK_RETURN
        }
        if codigo in teclas_bloqueadas:
            evento.Skip()
            return

        ctrl = evento.ControlDown()
        alt = evento.AltDown()
        shift = evento.ShiftDown()
        mods = []
        if ctrl: mods.append("Ctrl")
        if alt: mods.append("Alt")
        if shift: mods.append("Shift")
        
        tecla = ""
        if wx.WXK_F1 <= codigo <= wx.WXK_F12: tecla = f"F{codigo - wx.WXK_F1 + 1}"
        elif wx.WXK_NUMPAD0 <= codigo <= wx.WXK_NUMPAD9: tecla = f"Num{codigo - wx.WXK_NUMPAD0}"
        elif 65 <= codigo <= 90:
            if not (ctrl or alt):
                evento.Skip()
                return
            tecla = chr(codigo)
        elif 48 <= codigo <= 57:
            if not (ctrl or alt):
                evento.Skip()
                return
            tecla = f"{codigo - 48}"
        else:
            evento.Skip()
            return

        comb = "+".join(mods + [tecla]) if mods else tecla

        for k in self.keys:
            if getattr(k, 'ativo', True) and k.tecla == comb and getattr(k, 'comando', ""):
                if self.app.client.conexao_ativa:
                    lista_comandos = Processor._processaComandosScript(k.comando)
                    for comando_individual in lista_comandos:
                        self.processa_e_envia_comando(comando_individual)
                else:
                    self.perguntaReconexao()
                return
        if comb == "Ctrl+H" and self.historicos_customizados:
            self._abre_historico_pelo_atalho()
            return
        evento.Skip()

    def detectaTeclas(self, evento):
        u = evento.GetUnicodeKey()
        if self.saidaFoco and not evento.ControlDown() and not evento.AltDown() and (32 <= u <= 126):
            ch = chr(u) if u else ''
            if ch:
                self.entrada.SetFocus()
                self.entrada.SetValue(ch)
                self.entrada.SetInsertionPointEnd()
                self.saidaFoco = False
                return
        evento.Skip()

    def fechaApp(self, evento):
        if self.app.client.conexao_ativa:
            pergunta_saida = wx.MessageDialog(self, 'Encerrar o aplicativo agora irá desconectar do MUD.\nDeseja encerrar?', 'Encerrar aplicativo', wx.YES_NO | wx.ICON_QUESTION)
            if pergunta_saida.ShowModal() != wx.ID_YES:
                pergunta_saida.Destroy()
                return
            pergunta_saida.Destroy()
            
        self.janelaFechada = True
        self.app.msp.musicOff()
        self.app.client.terminaCliente()
        self.para_gerenciador_timers()
        self.Close()
        self.app.ExitMainLoop()

    def menuBar(self):
        geralMenu = wx.Menu()
        interrompeMusica = geralMenu.Append(wx.ID_ANY, "&Interromper música em reprodução\tCtrl-M")
        self.Bind(wx.EVT_MENU, lambda e: self.app.msp.musicOff(), interrompeMusica)
        geralMenu.AppendSeparator()
        encerraPrograma = geralMenu.Append(wx.ID_EXIT, "&Sair.")
        self.Bind(wx.EVT_MENU, self.fechaApp, encerraPrograma)
        
        menuPastas = wx.Menu()
        geral = menuPastas.Append(wx.ID_ANY, "Abrir Pasta Geral\tCtrl-G")
        self.Bind(wx.EVT_MENU, lambda e: subprocess.Popen(f"explorer {self.pasta_geral}"), geral)
        logs = menuPastas.Append(wx.ID_ANY, "abrir pasta de logs\tCtrl-L")
        self.Bind(wx.EVT_MENU, lambda e: subprocess.Popen(f"explorer {self.pasta_logs}"), logs)
        scripts = menuPastas.Append(wx.ID_ANY, "Abrir Pasta de Scripts\tCtrl-R")
        self.Bind(wx.EVT_MENU, lambda e: subprocess.Popen(f"explorer {self.pasta_scripts}"), scripts)
        sons = menuPastas.Append(wx.ID_ANY, "Abrir Pasta de Sons\tCtrl-S")
        self.Bind(wx.EVT_MENU, lambda e: subprocess.Popen(f"explorer {self.pasta_sons}"), sons)
        
        menuFerramentas = wx.Menu()
        menuBackup = wx.Menu()
        exportarBackup = menuBackup.Append(wx.ID_ANY, "Exportar configurações e personagens\tCtrl-Shift-E")
        self.Bind(wx.EVT_MENU, self.ao_exportar_backup, exportarBackup)
        
        importarBackup = menuBackup.Append(wx.ID_ANY, "Importar configurações e personagens\tCtrl-Shift-I")
        self.Bind(wx.EVT_MENU, self.ao_importar_backup, importarBackup)
        
        menuFerramentas.AppendSubMenu(menuBackup, "&Backup")
        menuSons = wx.Menu()
        baixarSons = menuSons.Append(wx.ID_ANY, "Baixar pacote de sons via Link\tCtrl-B")
        self.Bind(wx.EVT_MENU, self.iniciarDownloadSons, baixarSons)
        
        importarSonsLocal = menuSons.Append(wx.ID_ANY, "Importar pacote de sons local (ZIP)\tCtrl-p")
        self.Bind(wx.EVT_MENU, self.iniciarImportacaoLocal, importarSonsLocal)
        
        menuFerramentas.AppendSubMenu(menuSons, "Gerenciar &Sons do Personagem")
        menuAudio = wx.Menu()
        id_musica_mais = wx.NewIdRef()
        id_musica_menos = wx.NewIdRef()
        id_som_mais = wx.NewIdRef()
        id_som_menos = wx.NewIdRef()
        menuAudio.Append(id_musica_mais, "Aumentar volume Música\tCtrl+PgUp")
        menuAudio.Append(id_musica_menos, "Diminuir Volume Música\tCtrl+PgDn")
        menuAudio.Append(id_som_mais, "Aumentar Volume Sons\tCtrl+Shift+PgUp")
        menuAudio.Append(id_som_menos, "Diminuir Volume Sons\tCtrl+Shift+PgDn")
        self.Bind(wx.EVT_MENU, lambda e: self.alteraVolume('musica', 10), id=id_musica_mais)
        self.Bind(wx.EVT_MENU, lambda e: self.alteraVolume('musica', -10), id=id_musica_menos)
        self.Bind(wx.EVT_MENU, lambda e: self.alteraVolume('som', 10), id=id_som_mais)
        self.Bind(wx.EVT_MENU, lambda e: self.alteraVolume('som', -10), id=id_som_menos)
        menuFerramentas.AppendSubMenu(menuAudio, "&Audio")

        menuMacros = wx.Menu()
        self.id_iniciar_gravacao = wx.NewIdRef()
        self.item_iniciar_gravacao = menuMacros.Append(self.id_iniciar_gravacao, "Iniciar Gravação")
        self.Bind(wx.EVT_MENU, self.inicia_gravacao, id=self.id_iniciar_gravacao)
        
        self.id_pausar_gravacao = wx.NewIdRef()
        self.item_pausar_gravacao = menuMacros.Append(self.id_pausar_gravacao, "Pausar Gravação")
        self.item_pausar_gravacao.Enable(False)
        self.Bind(wx.EVT_MENU, self.pausa_retoma_gravacao, id=self.id_pausar_gravacao)
        
        self.id_ignorar_ultimo = wx.NewIdRef()
        self.item_ignorar_ultimo = menuMacros.Append(self.id_ignorar_ultimo, "Ignorar Último Comando")
        self.item_ignorar_ultimo.Enable(False)
        self.Bind(wx.EVT_MENU, self.ignora_ultimo_comando, id=self.id_ignorar_ultimo)
        
        self.id_interromper_gravacao = wx.NewIdRef()
        self.item_interromper_gravacao = menuMacros.Append(self.id_interromper_gravacao, "Interromper Gravação")
        self.item_interromper_gravacao.Enable(False)
        self.Bind(wx.EVT_MENU, self.interrompe_gravacao, id=self.id_interromper_gravacao)
        
        menuMacros.AppendSeparator()
        
        gerenciarMacros = menuMacros.Append(wx.ID_ANY, "Gerenciar &Macros / Rotas...\tCtrl-U")
        self.Bind(wx.EVT_MENU, self.abrirGerenciadorMacros, gerenciarMacros)
        
        menuFerramentas.AppendSubMenu(menuMacros, "M&acros e Rotas")
        
        menuGerenciarKeys = menuFerramentas.Append(wx.ID_ANY, 'Gerenciar atalhos...\tCtrl-K')
        self.Bind(wx.EVT_MENU, self.abrirGerenciadorKeys, menuGerenciarKeys)
        menuGerenciarTriggers = menuFerramentas.Append(wx.ID_ANY, "Gerenciar &Triggers...\tCtrl-T")
        self.Bind(wx.EVT_MENU, self.abrirGerenciadorTriggers, menuGerenciarTriggers)
        menuGerenciarTimers = menuFerramentas.Append(wx.ID_ANY, "Gerenciar &Timers...\tCtrl-I")
        self.Bind(wx.EVT_MENU, self.abrirGerenciadorTimers, menuGerenciarTimers)
        
        self.menuHistoricos = wx.Menu()
        menuFerramentas.AppendSubMenu(self.menuHistoricos, "&Históricos\tCtrl-H")
        
        ditado = menuFerramentas.Append(wx.ID_ANY, "Escrever por voz\tCtrl-O")
        self.Bind(wx.EVT_MENU, self.falaPorVoz, ditado)
        
        menuAjuda = wx.Menu()
        ajuda = menuAjuda.Append(wx.ID_ANY, "&Ajuda\tF1")
        self.Bind(wx.EVT_MENU, self.abrirAjuda, ajuda)
        menuAjuda.AppendSeparator()
        checarAtualizacoes = menuAjuda.Append(wx.ID_ANY, "Checar &Atualizações")
        self.Bind(wx.EVT_MENU, self.checarAtualizacoes, checarAtualizacoes)
        menuAjuda.AppendSeparator()
        sobre = menuAjuda.Append(wx.ID_ABOUT, "&Sobre o ClientMUD")
        self.Bind(wx.EVT_MENU, self.abrirSobre, sobre)

        menuBar = wx.MenuBar()
        menuBar.Append(geralMenu, "&Geral")
        menuBar.Append(menuPastas, "&Pastas")
        menuBar.Append(menuFerramentas, "&Ferramentas")
        menuBar.Append(menuAjuda, "&Ajuda")
        self.SetMenuBar(menuBar)

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

    def inicia_gravacao(self, evento):
        self._gravando_macro = True
        self._macro_pausada = False
        self._comandos_gravados = []
        self.item_iniciar_gravacao.Enable(False)
        self.item_pausar_gravacao.Enable(True)
        self.item_pausar_gravacao.SetItemLabel("Pausar Gravação")
        self.item_ignorar_ultimo.Enable(True)
        self.item_interromper_gravacao.Enable(True)
        self.app.fale("Gravação iniciada. Todos os comandos serão registrados.")
        
    def pausa_retoma_gravacao(self, evento):
        self._macro_pausada = not self._macro_pausada
        if self._macro_pausada:
            self.item_pausar_gravacao.SetItemLabel("Retomar Gravação")
            self.app.fale("Gravação pausada.")
        else:
            self.item_pausar_gravacao.SetItemLabel("Pausar Gravação")
            self.app.fale("Gravação retomada.")
            
    def ignora_ultimo_comando(self, evento):
        if self._comandos_gravados:
            removido = self._comandos_gravados.pop()
            self.app.fale(f"Comando ignorado: {removido}")
        else:
            self.app.fale("Nenhum comando gravado para ignorar.")
            
    def interrompe_gravacao(self, evento):
        self._gravando_macro = False
        self.item_iniciar_gravacao.Enable(True)
        self.item_pausar_gravacao.Enable(False)
        self.item_pausar_gravacao.SetItemLabel("Pausar Gravação")
        self.item_ignorar_ultimo.Enable(False)
        self.item_interromper_gravacao.Enable(False)
        
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

    def abrirGerenciadorMacros(self, evento):
        from gui.dialogs.macros import DialogoGerenciaMacros
        dlg = DialogoGerenciaMacros(self, self.macros)
        if dlg.ShowModal() == wx.ID_OK:
            if dlg.alteracoes_feitas:
                self.salvaConfiguracoesPersonagem()
        dlg.Destroy()

    def abrirGerenciadorTriggers(self, evento):
        dlg = DialogoGerenciaTriggers(self, self.triggers)
        if dlg.ShowModal() == wx.ID_OK:
            if dlg.alteracoes_feitas:
                self.salvaConfiguracoesPersonagem()
        dlg.Destroy()

    def falaPorVoz(self, evento):
        threading.Thread(target=self.ouvir_microfone_thread, daemon=True).start()

    def ouvir_microfone_thread(self):
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            try:
                r.adjust_for_ambient_noise(source, duration=0.1)
                self.app.fale("Comece a falar.")
                r.pause_threshold = 1.0
                r.non_speaking_duration = 1.0
                r.energy_threshold = 100
                r.dynamic_energy_threshold = True
                audio = r.listen(source, phrase_time_limit=None)
                texto = r.recognize_google(audio, language="pt-BR")
                
                substituicoes = [
                    (r'\s*ponto de interroga[çc][ãa]o', '?'),
                    (r'\s*ponto de exclama[çc][ãa]o', '!'),
                    (r'\s*ponto final', '.'),
                    (r'\s*ponto e v[íi]rgula', ';'),
                    (r'\s*dois pontos', ':'),
                    (r'\s*v[íi]rgula', ','),
                    (r'\s*retic[êe]ncias', '...')
                ]
                
                for padrao, simbolo in substituicoes:
                    texto = re.sub(padrao, simbolo, texto, flags=re.IGNORECASE)
                    
                self.adicionaComandoLista(texto)
                self.processa_e_envia_comando(texto)
            except sr.UnknownValueError:
                self.app.fale("Não entendi o que foi dito.")
            except Exception as e:
                self.app.fale(f"Erro inesperado: {e}")

    def abrirGerenciadorTimers(self, evento):
        if not self.gerenciador_timers:
            wx.MessageBox("O gerenciador de timers não está ativo.", "Erro", wx.ICON_ERROR)
            return
        dlg = DialogoGerenciaTimers(self, self.timers, self.gerenciador_timers)
        if dlg.ShowModal() == wx.ID_OK:
            if dlg.alteracoes_feitas:
                self.salvaConfiguracoesPersonagem()
        dlg.Destroy()

    def abrirGerenciadorKeys(self, evento=None):
        dlg = DialogoGerenciaKeys(self, self.keys)
        if dlg.ShowModal() == wx.ID_OK:
            self.salvaConfiguracoesPersonagem()
        dlg.Destroy()

    def adiciona_ao_historico_customizado(self, nome_historico, linha):
        if nome_historico not in self.historicos_customizados:
            self.historicos_customizados[nome_historico] = []
            item_menu = self.menuHistoricos.Append(wx.ID_ANY, nome_historico)
            self.Bind(wx.EVT_MENU, lambda evt, name=nome_historico: self.mostra_historico(name), item_menu)
        self.historicos_customizados[nome_historico].append(linha)
        if nome_historico in self.historicos_abertos:
            dlg = self.historicos_abertos[nome_historico]
            if dlg: wx.CallAfter(dlg.adiciona_linha, linha)

    def mostra_historico(self, nome_historico):
        if nome_historico in self.historicos_abertos:
            self.historicos_abertos[nome_historico].Raise()
            return
        dlg = DialogoHistorico(self, title=f"Histórico: {nome_historico}", nome_historico=nome_historico)
        self.historicos_abertos[nome_historico] = dlg
        dlg.ShowModal()
        if nome_historico in self.historicos_abertos:
            del self.historicos_abertos[nome_historico]
        dlg.Destroy()

    def _abre_historico_pelo_atalho(self):
        nomes = list(self.historicos_customizados.keys())
        if len(nomes) == 1:
            self.mostra_historico(nomes[0])
        elif len(nomes) > 1:
            dlg = wx.SingleChoiceDialog(self, "Escolha o histórico:", "Históricos", nomes)
            if dlg.ShowModal() == wx.ID_OK:
                self.mostra_historico(dlg.GetStringSelection())
            dlg.Destroy()

    def carregaTriggers(self):
        from models.trigger import Trigger
        triggers_globais = [Trigger(cfg) for cfg in self.app.config.carregaGlobalConfig().get('triggers', [])]
        triggers_mud = [Trigger(cfg) for cfg in self.app.config.carregaMudConfig(self.nome_mud).get('triggers', [])] if self.nome_mud else []
        triggers_locais = [Trigger(cfg) for cfg in self.json_personagem.get('triggers', [])] if self.json_personagem else []
        self.triggers = triggers_globais + triggers_mud + triggers_locais

    def carregaTimers(self):
        from models.timer import Timer
        timers_globais = [Timer(cfg) for cfg in self.app.config.carregaGlobalConfig().get('timers', [])]
        timers_mud = [Timer(cfg) for cfg in self.app.config.carregaMudConfig(self.nome_mud).get('timers', [])] if self.nome_mud else []
        timers_locais = [Timer(cfg) for cfg in self.json_personagem.get('timers', [])] if self.json_personagem else []
        self.timers = timers_globais + timers_mud + timers_locais

    def carregaKeys(self):
        from models.key import Key
        keys_globais = [Key(cfg) for cfg in self.app.config.carregaGlobalConfig().get('keys', [])]
        keys_mud = [Key(cfg) for cfg in self.app.config.carregaMudConfig(self.nome_mud).get('keys', [])] if self.nome_mud else []
        keys_locais = [Key(cfg) for cfg in self.json_personagem.get('keys', [])] if self.json_personagem else []
        self.keys = keys_globais + keys_mud + keys_locais

    def carregaMacros(self):
        from models.macro import Macro
        macros_globais = [Macro(cfg) for cfg in self.app.config.carregaGlobalConfig().get('macros', [])]
        macros_mud = [Macro(cfg) for cfg in self.app.config.carregaMudConfig(self.nome_mud).get('macros', [])] if self.nome_mud else []
        macros_locais = [Macro(cfg) for cfg in self.json_personagem.get('macros', [])] if self.json_personagem else []
        self.macros = macros_globais + macros_mud + macros_locais

    def inicia_gerenciador_timers(self):
        if self.gerenciador_timers and not self.gerenciador_timers.is_alive():
            self.gerenciador_timers = None
        if not self.gerenciador_timers and self.app.client.ativo:
            configs_para_thread = [t.to_dict() for t in self.timers]
            self.gerenciador_timers = GerenciadorTimers(configs_para_thread, self.app.client)
            self.gerenciador_timers.start()

    def para_gerenciador_timers(self):
        if self.gerenciador_timers:
            self.gerenciador_timers.parar()
            self.gerenciador_timers.join(timeout=1.0)
            self.gerenciador_timers = None

    def focaSaida(self):
        self.saida.Unbind(wx.EVT_KILL_FOCUS, handler=self.perdeFoco)
        self.saida.Unbind(wx.EVT_SET_FOCUS, handler=self.ganhaFoco)
        self.saida.Unbind(wx.EVT_CHAR, handler=self.detectaTeclas)
        self.saida.SetFocus()
        self.saidaFoco = True
        self.entrada.Disable()

    def janelaAtiva(self, evento):
        self.janelaAtivada = evento.GetActive()
        evento.Skip()

    def reconecta(self):
        endereco = self.app.client.endereco
        porta = self.app.client.porta
        if not endereco or not porta:
            if self.json_personagem:
                endereco = self.json_personagem.get('endereço')
                porta = self.json_personagem.get('porta')
            elif self.app.config.config['gerais'].get('ultima-conexao'):
                endereco, porta = self.app.config.config['gerais']['ultima-conexao']
        if endereco and porta:
            self._iniciarConexaoThread(endereco, porta)

    def perguntaReconexao(self):
        if self.janelaFechada: return
        dlg = wx.MessageDialog(self, 'Deseja se reconectar?', 'Conexão finalizada', wx.YES_NO | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_YES:
            self.reconecta()
        else:
            self.focaSaida()
        dlg.Destroy()

    def salvaConfiguracoesPersonagem(self):
        triggers_local, triggers_mud, triggers_global = [], [], []
        for t in self.triggers:
            if t.escopo == 2: triggers_global.append(t.to_dict())
            elif t.escopo == 1: triggers_mud.append(t.to_dict())
            else: triggers_local.append(t.to_dict())

        timers_local, timers_mud, timers_global = [], [], []
        for t in self.timers:
            if t.escopo == 2: timers_global.append(t.to_dict())
            elif t.escopo == 1: timers_mud.append(t.to_dict())
            else: timers_local.append(t.to_dict())

        keys_local, keys_mud, keys_global = [], [], []
        for k in self.keys:
            if k.escopo == 2: keys_global.append(k.to_dict())
            elif k.escopo == 1: keys_mud.append(k.to_dict())
            else: keys_local.append(k.to_dict())

        macros_local, macros_mud, macros_global = [], [], []
        for m in self.macros:
            if m.escopo == 2: macros_global.append(m.to_dict())
            elif m.escopo == 1: macros_mud.append(m.to_dict())
            else: macros_local.append(m.to_dict())

        self.app.config.salvaGlobalConfig(triggers_global, timers_global, keys_global, macros_global)

        if self.nome_mud:
            self.app.config.salvaMudConfig(self.nome_mud, triggers_mud, timers_mud, keys_mud, macros_mud)
        else:
            for item in triggers_mud:
                item['escopo'] = 0
                triggers_local.append(item)
            for item in timers_mud:
                item['escopo'] = 0
                timers_local.append(item)
            for item in keys_mud:
                item['escopo'] = 0
                keys_local.append(item)
            for item in macros_mud:
                item['escopo'] = 0
                macros_local.append(item)

        if not self.json_personagem:
            self.app.config.atualizaConfigsConexaoManual(triggers_local, timers_local, keys_local, macros_local)
            return

        self.json_personagem['triggers'] = triggers_local
        self.json_personagem['timers'] = timers_local
        self.json_personagem['keys'] = keys_local
        self.json_personagem['macros'] = macros_local
        
        chave = self._chave_personagem or self.nome
        if not self.app.personagem.atualizaPersonagem(chave, self.json_personagem):
            wx.MessageBox("Falha ao salvar as configurações do personagem.", "Erro", wx.ICON_ERROR)

    def verificaConexao(self, evento):
        if evento.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and not self.app.client.conexao_ativa:
            self.perguntaReconexao()
            return
        evento.Skip()

    def alteraVolume(self, tipo, valor):
        if not self.app.msp.alteraVolume(tipo, valor):
            self.app.fale(f"Volume de {tipo} chegou no limite.")
    
    def iniciarDownloadSons(self, evento):
        dlg = DialogoPedeURL(self)
        if dlg.ShowModal() == wx.ID_OK:
            url = dlg.campo_url.GetValue().strip()
            if url:
                importer = SoundImporter(self.pasta_sons)
                JanelaProgresso(self, importer, url=url)
        dlg.Destroy()

    def iniciarImportacaoLocal(self, evento):
        estilo = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        dlg = wx.FileDialog(self, "Selecione o arquivo ZIP com os sons", wildcard="Arquivos ZIP (*.zip)|*.zip", style=estilo)
        if dlg.ShowModal() == wx.ID_OK:
            caminho_zip = dlg.GetPath()
            importer = SoundImporter(self.pasta_sons)
            JanelaProgresso(self, importer, caminho_local=caminho_zip)
        dlg.Destroy()

    def ao_exportar_backup(self, evento):
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
                    wx.GetApp().fale("Backup exportado com sucesso!")
                except Exception:
                    pass
            wx.MessageBox(mensagem, titulo, icone)
            
        dlg.Destroy()
    def ao_importar_backup(self, evento):
        import sys
        import os
        import subprocess
        from pathlib import Path
        
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
                
                rodando_pelo_python = sys.argv[0].lower().endswith('.py') or sys.argv[0].lower().endswith('.pyw')
                
                if rodando_pelo_python:
                    caminho_script = os.path.abspath(sys.argv[0])
                    comando = [sys.executable, caminho_script] + sys.argv[1:]
                    pasta_trabalho = os.path.dirname(caminho_script) or os.getcwd()
                else:
                    pasta_trabalho = os.getcwd()
                    caminho_exe = os.path.join(pasta_trabalho, "clientmud.exe")
                    comando = [caminho_exe] + sys.argv[1:]
                    
                subprocess.Popen(
                    comando, 
                    cwd=pasta_trabalho,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                sys.exit(0)
            else:
                wx.MessageBox(mensagem, titulo, icone)
            
        dlg.Destroy()
    def _thread_envia_macro(self, lista_comandos):
        qtd_lote = 0
        for cmd in lista_comandos:
            if self.janelaFechada:
                break
            for comando, espera in cmd.items():
                self._desdobra_e_envia(comando)
                qtd_lote += 1
                if qtd_lote == 10:
                    qtd_lote = 0
                    time.sleep(1)
                else:
                    time.sleep(espera)

class Aplicacao(wx.App):
    def OnInit(self):
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
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count())

    def mostraDialogoEntrada(self):
        janela_inicial = DialogoEntrada(None)
        janela_inicial.ShowModal()
        janela_inicial.Destroy()

    def iniciaJanelaMud(self, dados):
        if dados['json_personagem']:
            frame = FramePrincipal(dados['json_personagem']['nome'], dados['json_personagem'])
        else:
            self.config.config['gerais']['ultima-conexao'] = [dados["endereco"], dados["porta"]]
            self.config.atualizaJson()
            frame = FramePrincipal(dados['endereco'])
            
        self.janela_principal = frame
        self.SetTopWindow(frame)