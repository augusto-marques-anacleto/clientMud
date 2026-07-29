import wx
import threading
import time

from gui.aba.utils import _RE_CMD_REPEAT, _aplica_vars_macro

class ComandosMixin:
    """Entrada de comandos: histórico de navegação, expansão de macros/repetições
    e envio ao MUD."""

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
                self.client.enviaComando(cmd)
        else:
            self.client.enviaComando(texto)

    def processa_e_envia_comando(self, comando):
        comando = comando.strip()
        if not comando:
            self.client.enviaComando("")
            return
        match = _RE_CMD_REPEAT.match(comando)
        if match:
            qtd = min(int(match.group(1)), 100)
            cmd_base = match.group(2).strip()
        else:
            qtd = 1
            cmd_base = comando

        cmd_lower = cmd_base.lower()
        if cmd_lower.startswith('#stop'):
            self.msp.soundOff()
            return

        if cmd_lower.startswith(('#wait', '#play', '#music')):
            engine = getattr(self, 'script_engine', None)
            if engine:
                engine.disparar(codigo=cmd_base, grupos=[], linha='', nome_trigger='', concorrencia='nova')
            return

        macro_encontrada = None
        macro_args = []
        for m in self.macros:
            if not getattr(m, 'ativo', True):
                continue
            if m.nome == cmd_base:
                macro_encontrada = m
                break
            if cmd_base.startswith(m.nome + ' '):
                macro_encontrada = m
                macro_args = cmd_base[len(m.nome):].strip().split()
                break

        if macro_encontrada and getattr(macro_encontrada, 'script', ''):
            self.script_engine.disparar(
                macro_encontrada.script, macro_args, cmd_base, macro_encontrada.nome,
                getattr(macro_encontrada, 'concorrencia', 'nova'),
            )
            return

        todos_comandos = []
        if not macro_encontrada and qtd == 1:
            self._desdobra_e_envia(cmd_base)
        else:
            for _ in range(qtd):
                if macro_encontrada:
                    for parte in macro_encontrada.comandos.split(';'):
                        parte_limpa = parte.strip()
                        if parte_limpa:
                            if macro_args:
                                parte_limpa = _aplica_vars_macro(parte_limpa, macro_args)
                            todos_comandos.append({parte_limpa: macro_encontrada.espera})
                else:
                    todos_comandos.append({cmd_base: 0.1})
        if 0 < len(todos_comandos) < 10:
            for comando in todos_comandos:
                for cmd, espera in comando.items():
                    self._desdobra_e_envia(cmd)
        elif len(todos_comandos) >= 10:
            threading.Thread(target=self._thread_envia_macro, args=(todos_comandos,), daemon=True).start()

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

    def enviaTexto(self, evento):
        cod = evento.GetKeyCode()
        mod = evento.GetModifiers()
        if cod in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and (mod == wx.MOD_SHIFT or mod == wx.MOD_NONE):
            if not self.client.conexao_ativa:
                self.perguntaReconexao()
                return
            texto_bruto = self.entrada.GetValue()
            texto_limpo = texto_bruto.strip()
            if not texto_limpo:
                self.processa_e_envia_comando("")
            else:
                self.adicionaComandoLista(texto_limpo)
                primeiro = texto_limpo.split(';')[0].strip().lower()
                if primeiro.startswith(('#wait', '#play', '#music', '#stop')):
                    if self._gravando_macro and not self._macro_pausada:
                        self._comandos_gravados.append(texto_limpo)
                    self.processa_e_envia_comando(texto_limpo)
                else:
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
