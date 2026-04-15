import re
import queue
from threading import Thread, Timer, Lock
from time import sleep
import wx

_RE_NAO_IMPRIMIVEL = re.compile(r'[^\x20-\x7E\n\r\x80-\xFF]')
_RE_CMD_REPEAT = re.compile(r'^#(\d+)\s+(.+)')
_RE_CMD_TRIGGER = re.compile(r'^#(\d+)\s+(.*)')

class Processor:
    def __init__(self, app_context):
        self.app = app_context
        self.padraoSom = re.compile(r"!!SOUND\(([^\s\\/!]+)\s*V?=?(\d+)?\)", re.IGNORECASE)
        self.padraoMusica = re.compile(r"!!MUSIC\(([^\s!\\/]+)\s*V?=?(\d+)?\s*L?=?(-?\d+)?\)", re.IGNORECASE)
        self.padraoTotal = re.compile(r"!!\w+\([^)]*\)")
        self.padraoAnsi = re.compile(r'\x1b\[\d+(?:;\d+)*m')
        self.fila_mensagens = queue.Queue()
        self.max_chars = 100_000
        self.chars_alvo = 80_000
        self._buffer_saida = []
        self._buffer_lock = Lock()
        self._flush_pendente = False

    @staticmethod
    def _processaComandosScript(texto_comando):
        if not texto_comando:
            return []
        lista_comandos = []
        partes_comando = texto_comando.split(';')
        for parte in partes_comando:
            comando_limpo = parte.strip()
            if not comando_limpo:
                continue
            
            correspondencia = _RE_CMD_REPEAT.match(comando_limpo)
            if correspondencia:
                try:
                    quantidade = int(correspondencia.group(1))
                    comando_real = correspondencia.group(2).strip()
                    quantidade = max(1, min(quantidade, 100))
                    for _ in range(quantidade):
                        lista_comandos.append(comando_real)
                except Exception:
                    lista_comandos.append(comando_limpo)
            else:
                lista_comandos.append(comando_limpo)
        return lista_comandos

    def reiniciaFilas(self):
        while not self.app.client.fila_mensagens.empty():
            try:
                self.app.client.fila_mensagens.get_nowait()
            except queue.Empty:
                break

    def pegaMusica(self, mensagem):
        args = re.findall(self.padraoMusica, mensagem)
        if "off)" in mensagem.lower():
            self.app.msp.musicOff()
        if args:
            for arg in args:
                arquivo = arg[0]
                v = int(arg[1]) if arg[1] != "" else 100
                if self.app.janela_principal.usar_volume_padrao:
                    v = self.app.janela_principal.volume_padrao
                l = int(arg[2]) if arg[2] != "" else 1
                self.app.msp.music(arquivo, v, l)

    def pegaSom(self, mensagem):
        args = re.findall(self.padraoSom, mensagem)
        for arg in args:
            arquivo = arg[0]
            v = int(arg[1]) if arg[1] != "" else 100
            if self.app.janela_principal.usar_volume_padrao:
                v = self.app.janela_principal.volume_padrao
            self.app.msp.sound(arquivo, v)

    def mostraMud(self):
        while not hasattr(self.app, 'janela_principal') or not self.app.janela_principal:
            sleep(0.05)

        while True:
            try:
                mensagem = self.app.client.fila_mensagens.get(timeout=0.1)
            except queue.Empty:
                if not getattr(self.app.client, 'ativo', False):
                    wx.CallAfter(self.app.msp.musicOff)
                    break
                continue
            
            if isinstance(mensagem, str):
                for linha in mensagem.split('\n'):
                    if linha.strip():
                        self.processaLinha(linha)

    def processaLinha(self, linha):
        linha = self.padraoAnsi.sub('', linha).strip()
        linha = _RE_NAO_IMPRIMIVEL.sub('', linha)
        if not linha:
            return

        for trigger in self.app.janela_principal.triggers:
            grupos_capturados = trigger.verifica(linha)
            
            if grupos_capturados is not None:
                if trigger.som_acao:
                    wx.CallAfter(self.app.msp.sound, trigger.som_acao, trigger.som_volume)
                
                if trigger.acao == 'comando':
                    comandos_para_enviar = self.processa_comandos_trigger(trigger.valor_acao, grupos_capturados)
                    for cmd in comandos_para_enviar:
                        if hasattr(self.app, 'janela_principal') and self.app.janela_principal:
                            self.app.janela_principal.processa_e_envia_comando(cmd)
                        else:
                            self.app.client.enviaComando(cmd)
                
                elif trigger.acao == 'som':
                    wx.CallAfter(self.app.msp.sound, trigger.valor_acao, 100)
                
                elif trigger.acao == 'historico':
                    wx.CallAfter(self.app.janela_principal.adiciona_ao_historico_customizado, trigger.valor_acao, linha)
                
                if trigger.ignorar_historico_principal:
                    return
        
        if linha.lower().startswith(("!!sound(", "!!music(")):
            if self.app.janela_principal.reproduzirSons or self.app.janela_principal.janelaAtivada:
                wx.CallAfter(self.pegaSom, linha)
                wx.CallAfter(self.pegaMusica, linha)
            return

        self.app.executor.submit(self.app.client.salvaLog, linha)
        
        if self.app.janela_principal.lerMensagens or self.app.janela_principal.janelaAtivada:
            wx.CallAfter(self.app.fale, linha)
        
        with self._buffer_lock:
            self._buffer_saida.append(linha)
            if not self._flush_pendente:
                self._flush_pendente = True
                t = Timer(0.016, self._flush_saida)
                t.daemon = True
                t.start()

    def processa_comandos_trigger(self, comando_bruto, grupos):
        comandos_finais = []
        comandos_com_vars = comando_bruto
        
        for i, group_text in enumerate(grupos, 1):
            comandos_com_vars = comandos_com_vars.replace(f'%{i}', group_text or '')
        
        comandos_base = comandos_com_vars.split(';')
        
        for cmd in comandos_base:
            cmd_limpo = cmd.strip()
            if not cmd_limpo:
                continue
            
            repeticoes = 1
            if cmd_limpo.startswith('#'):
                match = _RE_CMD_TRIGGER.match(cmd_limpo)
                if match:
                    try:
                        repeticoes = int(match.group(1))
                        repeticoes = max(1, min(repeticoes, 100))
                        cmd_limpo = match.group(2).strip()
                    except ValueError:
                        cmd_limpo = cmd.strip()
            
            if cmd_limpo:
                for _ in range(repeticoes):
                    comandos_finais.append(cmd_limpo)
                    
        return comandos_finais

    def _flush_saida(self):
        with self._buffer_lock:
            linhas = self._buffer_saida[:]
            self._buffer_saida.clear()
            self._flush_pendente = False
        if linhas:
            wx.CallAfter(self._aplica_saida, linhas)

    def _aplica_saida(self, linhas):
        frame = self.app.janela_principal
        if not frame:
            return
        saida = getattr(frame, 'saida', None)
        if not saida:
            return
        texto = '\n'.join(linhas) + '\n'
        try:
            sel_start, sel_end = saida.GetSelection()
            tem_selecao = sel_start != sel_end
            usa_foco = frame.saidaFoco
            if usa_foco:
                posicao = saida.GetInsertionPoint()
            saida.AppendText(texto)
            removidos = self.limitaHistorico()
            if tem_selecao:
                novo_start = max(0, sel_start - removidos)
                novo_end = max(0, sel_end - removidos)
                if novo_start != novo_end:
                    saida.SetSelection(novo_start, novo_end)
                else:
                    saida.SetInsertionPointEnd()
            elif usa_foco:
                nova_posicao = max(0, posicao - removidos)
                saida.SetInsertionPoint(nova_posicao)
                saida.ShowPosition(nova_posicao)
            else:
                saida.SetInsertionPointEnd()
        except RuntimeError:
            return

    def limitaHistorico(self):
        frame = self.app.janela_principal
        if not frame:
            return 0
        saida = getattr(frame, "saida", None)
        if not saida:
            return 0
        try:
            total = saida.GetLastPosition()
            if total <= self.max_chars:
                return 0
            corte = total - self.chars_alvo
            trecho = saida.GetRange(corte, min(corte + 500, total))
            pos_nl = trecho.find('\n')
            if pos_nl >= 0:
                corte = corte + pos_nl + 1
            saida.Remove(0, corte)
            return corte
        except RuntimeError:
            return 0

    def atualizaSaidaComFoco(self, linha):
        frame = self.app.janela_principal
        if not frame:
            return
        saida = getattr(frame, "saida", None)
        if not saida:
            return
        try:
            sel_start, sel_end = saida.GetSelection()
            tem_selecao = sel_start != sel_end
            posicao = saida.GetInsertionPoint()
            saida.AppendText(linha + '\n')
            removidos = self.limitaHistorico()
            if tem_selecao:
                novo_start = max(0, sel_start - removidos)
                novo_end = max(0, sel_end - removidos)
                if novo_start != novo_end:
                    saida.SetSelection(novo_start, novo_end)
                else:
                    saida.SetInsertionPointEnd()
            else:
                nova_posicao = max(0, posicao - removidos)
                saida.SetInsertionPoint(nova_posicao)
                saida.ShowPosition(nova_posicao)
        except RuntimeError:
            return

    def adicionaSaida(self, linha):
        frame = self.app.janela_principal
        if not frame:
            return
        saida = getattr(frame, "saida", None)
        if not saida:
            return
        try:
            sel_start, sel_end = saida.GetSelection()
            tem_selecao = sel_start != sel_end
            saida.AppendText(linha + '\n')
            removidos = self.limitaHistorico()
            if tem_selecao:
                novo_start = max(0, sel_start - removidos)
                novo_end = max(0, sel_end - removidos)
                if novo_start != novo_end:
                    saida.SetSelection(novo_start, novo_end)
                else:
                    saida.SetInsertionPointEnd()
            else:
                saida.SetInsertionPointEnd()
        except RuntimeError:
            return