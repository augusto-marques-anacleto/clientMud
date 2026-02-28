import re
import queue
from threading import Thread
from time import sleep
import wx

class Processor:
    def __init__(self, app_context):
        self.app = app_context
        self.padraoSom = re.compile(r"!!SOUND\(([^\s\\/!]+)\s*V?=?(\d+)?\)", re.IGNORECASE)
        self.padraoMusica = re.compile(r"!!MUSIC\(([^\s!\\/]+)\s*V?=?(\d+)?\s*L?=?(-?\d+)?\)", re.IGNORECASE)
        self.padraoTotal = re.compile(r"!!\w+\([^)]*\)")
        self.padraoAnsi = re.compile(r'\x1b\[\d+(?:;\d+)*m')
        self.fila_mensagens = queue.Queue()
        self.max_linhas = 2000
        self.linhas_remover = 50

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
            
            correspondencia = re.match(r'^#(\d+)\s+(.+)', comando_limpo)
            if correspondencia:
                try:
                    quantidade = int(correspondencia.group(1))
                    comando_real = correspondencia.group(2).strip()
                    quantidade = max(1, min(quantidade, 100))
                    for _ in range(quantidade):
                        lista_comandos.append(comando_real)
                except:
                    lista_comandos.append(comando_limpo)
            else:
                lista_comandos.append(comando_limpo)
        return lista_comandos

    def reiniciaFilas(self):
        self.fila_mensagens = queue.Queue()

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

    def thread_recebe(self):
        while self.app.client.ativo:
            mensagem = self.app.client.recebeMensagem()
            if mensagem:
                self.fila_mensagens.put(mensagem)
            else:
                sleep(0.01)

    def mostraMud(self):
        sleep(0.1)
        Thread(target=self.thread_recebe, daemon=True).start()
        while True:
            try:
                mensagem = self.fila_mensagens.get(timeout=0.1)
            except queue.Empty:
                if self.app.client.eof or not self.app.client.ativo:
                    self.app.msp.musicOff()
                    break
                continue
            for linha in mensagem.split("\n"):
                self.processaLinha(linha)
            if self.app.client.eof or not self.app.client.ativo:
                self.app.msp.musicOff()
                break

    def processaLinha(self, linha):
        linha = self.padraoAnsi.sub('', linha).strip()
        linha = ''.join(c for c in linha if c.isprintable() or c in '\n\r')
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
                        self.app.client.enviaComando(cmd)
                
                elif trigger.acao == 'som':
                    wx.CallAfter(self.app.msp.sound, trigger.valor_acao, 100)
                
                elif trigger.acao == 'historico':
                    self.app.janela_principal.adiciona_ao_historico_customizado(trigger.valor_acao, linha)
                
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
        
        if self.app.janela_principal.saidaFoco:
            wx.CallAfter(self.atualizaSaidaComFoco, linha)
        else:
            wx.CallAfter(self.adicionaSaida, linha)

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
                match = re.match(r'#(\d+)\s+(.*)', cmd_limpo)
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

    def limitaHistorico(self):
        saida = self.app.janela_principal.saida
        if saida.GetNumberOfLines() > self.max_linhas:
            fim = saida.XYToPosition(0, self.linhas_remover)
            saida.Remove(0, fim)

    def atualizaSaidaComFoco(self, linha):
        saida = self.app.janela_principal.saida
        posicao = saida.GetInsertionPoint()
        saida.AppendText(linha + '\n')
        saida.SetInsertionPoint(posicao)
        saida.ShowPosition(posicao)

    def adicionaSaida(self, linha):
        self.app.janela_principal.saida.AppendText(linha + '\n')
        self.limitaHistorico()
        self.app.janela_principal.saida.SetInsertionPointEnd()