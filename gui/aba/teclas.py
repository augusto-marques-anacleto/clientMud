import wx
import webbrowser

from core.processor import Processor
from gui.aba.utils import _RE_URL

class TeclasMixin:
    """Tratamento de teclado (atalhos globais, keys do usuário), foco entre
    saída/entrada e estado da janela desta aba."""

    def enterNoLink(self, evento):
        if evento.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            posicao = self.saida.GetInsertionPoint()
            valores = self.saida.PositionToXY(posicao)
            linha_idx = valores[2]
            texto_linha = self.saida.GetLineText(linha_idx)
            match = _RE_URL.search(texto_linha)
            if match:
                webbrowser.open(match.group(1))
                return
        evento.Skip()

    def ganhaFoco(self, evento):
        self.saidaFoco = True
        evento.Skip()

    def perdeFoco(self, evento):
        self.saida.SetInsertionPointEnd()
        self.saidaFoco = False
        self.entrada.SetInsertionPointEnd()
        evento.Skip()

    def teclasPressionadas(self, evento):
        codigo = evento.GetKeyCode()
        ctrl = evento.ControlDown()
        alt = evento.AltDown()
        shift = evento.ShiftDown()

        if codigo == wx.WXK_TAB and not ctrl:
            if self.entrada.HasFocus():
                self.saida.SetFocus()
            else:
                self.entrada.SetFocus()
            return

        if codigo == wx.WXK_ESCAPE or (ctrl and not alt and not shift and codigo == ord('W')):
            self.frame_principal.fechaAba(self)
            return

        if self.saidaFoco:
            u = evento.GetUnicodeKey()
            if not (ctrl or alt):
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

        if ctrl and not alt and not shift and tecla.isdigit():
            numero = int(tecla)
            if 1 <= numero <= 9:
                self._ler_historico_rapido(numero)
                return

        if comb == "F3":
            self._busca_saida.buscar_proximo()
            return

        if comb == "Ctrl+F":
            self._busca_saida.abrir_busca()
            return

        for k in self.keys:
            if getattr(k, 'ativo', True) and k.tecla == comb and getattr(k, 'comando', ""):
                if self.client.conexao_ativa:
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

    def _ler_historico_rapido(self, posicao):
        total_linhas = self.saida.GetNumberOfLines()
        linhas_validas = 0
        for i in range(total_linhas - 1, -1, -1):
            texto = self.saida.GetLineText(i).strip()
            if texto:
                linhas_validas += 1
                if linhas_validas == posicao:
                    self.app.fale(texto)
                    return
        self.app.fale(f"Não há {posicao} linhas no histórico ainda.")

    def focaSaida(self):
        self.saida.Unbind(wx.EVT_KILL_FOCUS, handler=self.perdeFoco)
        self.saida.Unbind(wx.EVT_SET_FOCUS, handler=self.ganhaFoco)
        self.saida.Unbind(wx.EVT_CHAR, handler=self.detectaTeclas)
        self.saida.SetFocus()
        self.saidaFoco = True
        self.entrada.Disable()

    def janelaAtiva(self, evento):
        self.janelaAtivada = evento.GetActive() and not self.frame_principal.IsIconized()
        evento.Skip()

    def janelaMinimizada(self, evento):
        if evento.IsIconized():
            self.janelaAtivada = False
        else:
            self.janelaAtivada = self.frame_principal.IsActive()
        evento.Skip()
