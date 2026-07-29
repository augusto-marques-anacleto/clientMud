import re
import queue
from threading import Timer, Lock
from time import sleep
import wx

_RE_NAO_IMPRIMIVEL = re.compile(r'[^\x20-\x7E\n\r\x80-\xFF]')
_RE_CMD_REPEAT = re.compile(r'^#(\d+)\s+(.+)')

class Processor:
    def __init__(self, aba_context):
        self.aba = aba_context
        self.padraoSom = re.compile(r"!!SOUND\(\s*([^)\s]+)([^)]*)\)", re.IGNORECASE)
        self.padraoMusica = re.compile(r"!!MUSIC\(\s*([^)\s]+)([^)]*)\)", re.IGNORECASE)
        self.padraoParamMsp = re.compile(r"([A-Za-z])\s*=\s*([^\s)]+)")
        self.padraoTotal = re.compile(r"!!\w+\([^)]*\)")
        self.padraoAnsi = re.compile(r'\x1b\[\d+(?:;\d+)*m')
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
        while not self.aba.client.fila_mensagens.empty():
            try:
                self.aba.client.fila_mensagens.get_nowait()
            except queue.Empty:
                break

    def _parseParamsMsp(self, texto):
        return {k.upper(): v for k, v in self.padraoParamMsp.findall(texto)}

    def pegaMusica(self, mensagem):
        for arquivo, resto in self.padraoMusica.findall(mensagem):
            if arquivo.lower() == "off":
                self.aba.msp.musicOff()
                continue
            params = self._parseParamsMsp(resto)
            v = int(params['V']) if params.get('V', '').isdigit() else 100
            if getattr(self.aba, 'usar_volume_padrao', False):
                v = getattr(self.aba, 'volume_padrao', 100)
            try:
                l = int(params.get('L', 1))
            except ValueError:
                l = 1
            self.aba.msp.music(arquivo, v, l, url=params.get('U'))

    def pegaSom(self, mensagem):
        for arquivo, resto in self.padraoSom.findall(mensagem):
            params = self._parseParamsMsp(resto)
            if arquivo.lower() == "off":
                if 'U' in params:
                    self.aba.msp.defineUrlBase(params['U'])
                self.aba.msp.soundOff(somente_mud=True)
                continue
            v = int(params['V']) if params.get('V', '').isdigit() else 100
            if getattr(self.aba, 'usar_volume_padrao', False):
                v = getattr(self.aba, 'volume_padrao', 100)
            self.aba.msp.sound(arquivo, v, url=params.get('U'))

    def mostraMud(self):
        while True:
            if getattr(self.aba, 'janelaFechada', False):
                break
                
            try:
                mensagem = self.aba.client.fila_mensagens.get(timeout=0.1)
            except queue.Empty:
                if not getattr(self.aba.client, 'ativo', False):
                    wx.CallAfter(self.aba.msp.musicOff)
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

        ignorar_historico = False
        for trigger in getattr(self.aba, 'triggers', []):
            grupos_capturados = trigger.verifica(linha)

            if grupos_capturados is not None:
                if trigger.som_acao:
                    wx.CallAfter(self.aba.msp.sound, trigger.som_acao, trigger.som_volume, de_trigger=True)

                if trigger.acao == 'comando':
                    comandos_para_enviar = self.processa_comandos_trigger(trigger.valor_acao, grupos_capturados)
                    for cmd in comandos_para_enviar:
                        if hasattr(self.aba, 'processa_e_envia_comando'):
                            self.aba.processa_e_envia_comando(cmd)
                        else:
                            self.aba.client.enviaComando(cmd)

                elif trigger.acao == 'script':
                    engine = getattr(self.aba, 'script_engine', None)
                    if engine:
                        engine.disparar(
                            codigo=trigger.valor_acao,
                            grupos=grupos_capturados,
                            linha=linha,
                            nome_trigger=trigger.nome,
                            concorrencia=getattr(trigger, 'concorrencia', 'nova'),
                        )

                elif trigger.acao == 'som':
                    wx.CallAfter(self.aba.msp.sound, trigger.valor_acao, 100, de_trigger=True)

                elif trigger.acao == 'historico':
                    wx.CallAfter(self.aba.adiciona_ao_historico_customizado, trigger.valor_acao, linha)

                if trigger.ignorar_historico_principal:
                    ignorar_historico = True

        engine = getattr(self.aba, 'script_engine', None)
        if engine:
            engine.publicar_linha(linha)

        if ignorar_historico:
            return

        # Avalia se a aba deste MUD está focada e se a janela principal do programa está ativa
        aba_focada = False
        try:
            frame = self.aba.frame_principal
            if wx.GetApp().IsActive() and frame.get_aba_ativa() == self.aba:
                aba_focada = True
        except Exception:
            pass

        if linha.lower().startswith(("!!sound(", "!!music(")):
            if getattr(self.aba, 'reproduzirSons', True) or aba_focada:
                wx.CallAfter(self.pegaSom, linha)
                wx.CallAfter(self.pegaMusica, linha)
            return

        # Passa o salvamento de log para o executor na Aplicacao global
        if hasattr(self.aba, 'app') and hasattr(self.aba.app, 'executor'):
            self.aba.app.executor.submit(self.aba.client.salvaLog, linha)
        
        # O NVDA só vai ler se for a aba ativa ou se você configurou para ler em segundo plano
        if getattr(self.aba, 'lerMensagens', False) or aba_focada:
            if hasattr(self.aba, 'app') and hasattr(self.aba.app, 'fale'):
                wx.CallAfter(self.aba.app.fale, linha)
        
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
        
        comandos_base = re.split(r'[;\n]', comandos_com_vars)
        
        for cmd in comandos_base:
            cmd_limpo = cmd.strip()
            if not cmd_limpo:
                continue
            
            repeticoes = 1
            if cmd_limpo.startswith('#'):
                match = _RE_CMD_REPEAT.match(cmd_limpo)
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
        if getattr(self.aba, 'janelaFechada', False):
            return
            
        saida = getattr(self.aba, 'saida', None)
        if not saida:
            return
            
        texto = '\n'.join(linhas) + '\n'
        try:
            sel_start, sel_end = saida.GetSelection()
            tem_selecao = sel_start != sel_end
            usa_foco = getattr(self.aba, 'saidaFoco', False)
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
        saida = getattr(self.aba, "saida", None)
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