import wx


class BuscaEmTexto:
    def __init__(self, textctrl, janela_pai=None):
        self.textctrl = textctrl
        self.janela_pai = janela_pai or textctrl
        self.ultimo_termo = ""

    def abrir_busca(self):
        dlg = wx.TextEntryDialog(self.janela_pai, "Buscar no histórico:", "Buscar", value=self.ultimo_termo)
        if dlg.ShowModal() == wx.ID_OK:
            termo = dlg.GetValue().strip()
            dlg.Destroy()
            if termo:
                self.ultimo_termo = termo
                self._executaBusca()
            else:
                self.textctrl.SetFocus()
        else:
            dlg.Destroy()
            self.textctrl.SetFocus()

    def buscar_proximo(self):
        if not self.ultimo_termo:
            self.abrir_busca()
            return
        self._executaBusca()

    def _executaBusca(self):
        conteudo = self.textctrl.GetValue()
        if not conteudo:
            return

        termo_lower = self.ultimo_termo.lower()
        conteudo_lower = conteudo.lower()

        _, fim_selecao = self.textctrl.GetSelection()
        posicao_inicial = max(fim_selecao, self.textctrl.GetInsertionPoint())

        pos = conteudo_lower.find(termo_lower, posicao_inicial)
        voltou_ao_inicio = False
        if pos == -1:
            pos = conteudo_lower.find(termo_lower, 0)
            voltou_ao_inicio = True

        if pos == -1:
            wx.Bell()
            self._anuncia(f'"{self.ultimo_termo}" não encontrado.')
            return

        fim = pos + len(self.ultimo_termo)
        self.textctrl.SetFocus()
        self.textctrl.ShowPosition(pos)
        self.textctrl.SetSelection(pos, fim)
        if voltou_ao_inicio:
            self._anuncia("Busca voltou ao início do histórico.")

    def _anuncia(self, mensagem):
        try:
            wx.GetApp().fale(mensagem)
        except Exception:
            pass
