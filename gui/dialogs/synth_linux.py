import wx

from core.sistema import listar_modulos_saida, listar_vozes, testar_voz
from gui.theme import aplica_tema_se_ativo

TECLAS_INTERROMPER = [
    ('Ctrl', 'ctrl'),
    ('Shift', 'shift'),
    ('Alt', 'alt'),
    ('Nenhuma', 'nenhuma'),
]

_SEM_PREFERENCIA = '(Automático, igual ao Orca)'


class DialogoSintetizadorLinux(wx.Dialog):
    """Configurações de fala específicas do Linux: qual módulo sintetizador
    e voz o ClientMUD usa para ler o texto do MUD, e a tecla que interrompe
    essa leitura. Só faz sentido no Linux porque é aqui que o ClientMUD
    precisa de uma conexão própria com o speech-dispatcher (ver
    core/sistema.py) -- no Windows o NVDA/JAWS cuidam disso sozinhos."""

    def __init__(self, pai=None):
        super().__init__(parent=pai, title="Sintetizador de voz (Linux)")
        self.app = wx.GetApp()
        painel = wx.Panel(self)
        self.Bind(wx.EVT_CHAR_HOOK, self.teclaPressionada)

        preferencias = self.app.config.config.get('gerais', {}).get('voz-linux', {}) or {}

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(painel, label='Sistema de fala: Speech Dispatcher (mesmo motor usado pelo Orca)'), 0, wx.ALL, 5)

        sizer.Add(wx.StaticText(painel, label='&Sintetizador (módulo):'), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.choice_modulo = wx.Choice(painel)
        sizer.Add(self.choice_modulo, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        self.choice_modulo.Bind(wx.EVT_CHOICE, self.ao_trocar_modulo)

        self.mostrar_todos_idiomas = wx.CheckBox(painel, label='Mostrar vozes de &todos os idiomas (lista muito mais longa)')
        sizer.Add(self.mostrar_todos_idiomas, 0, wx.ALL, 5)
        self.mostrar_todos_idiomas.Bind(wx.EVT_CHECKBOX, lambda e: self._popula_vozes())

        sizer.Add(wx.StaticText(painel, label='&Voz:'), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.choice_voz = wx.Choice(painel)
        sizer.Add(self.choice_voz, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        sizer.Add(wx.StaticText(painel, label='&Taxa de fala (-100 a 100):'), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.campo_taxa = wx.SpinCtrl(painel, min=-100, max=100, initial=int(preferencias.get('taxa') or 0))
        sizer.Add(self.campo_taxa, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        sizer.Add(wx.StaticText(painel, label='V&olume (-100 a 100):'), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.campo_volume = wx.SpinCtrl(painel, min=-100, max=100, initial=int(preferencias.get('volume') or 0))
        sizer.Add(self.campo_volume, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        sizer.Add(wx.StaticText(painel, label='Tecla para &interromper a leitura do MUD:'), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.choice_tecla = wx.Choice(painel, choices=[rotulo for rotulo, _ in TECLAS_INTERROMPER])
        sizer.Add(self.choice_tecla, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.btn_testar = wx.Button(painel, label='&Testar voz')
        self.btn_testar.Bind(wx.EVT_BUTTON, self.ao_testar)
        btn_sizer.Add(self.btn_testar, 0, wx.ALL, 5)

        btn_restaurar = wx.Button(painel, label='&Restaurar automático')
        btn_restaurar.Bind(wx.EVT_BUTTON, self.ao_restaurar)
        btn_sizer.Add(btn_restaurar, 0, wx.ALL, 5)

        btnSalvar = wx.Button(painel, wx.ID_OK, label='&Salvar')
        btnSalvar.Bind(wx.EVT_BUTTON, self.salva)
        btn_sizer.Add(btnSalvar, 0, wx.ALL, 5)

        btnCancelar = wx.Button(painel, wx.ID_CANCEL, label='&Cancelar')
        btn_sizer.Add(btnCancelar, 0, wx.ALL, 5)

        sizer.Add(btn_sizer, 0, wx.CENTER)

        painel.SetSizer(sizer)
        sizer.Fit(self)
        self.Center()

        self._popula_modulos(preferencias.get('modulo'))
        self.mostrar_todos_idiomas.SetValue(False)
        self._popula_vozes(preferencias.get('voz'))

        tecla_salva = preferencias.get('tecla-interromper', 'ctrl')
        indices = [chave for _, chave in TECLAS_INTERROMPER]
        self.choice_tecla.SetSelection(indices.index(tecla_salva) if tecla_salva in indices else 0)

        aplica_tema_se_ativo(self)
        self.choice_modulo.SetFocus()

    def teclaPressionada(self, evento):
        if evento.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
        else:
            evento.Skip()

    def _popula_modulos(self, modulo_salvo=None):
        modulos = listar_modulos_saida()
        itens = [_SEM_PREFERENCIA] + modulos
        self.choice_modulo.Set(itens)
        if modulo_salvo and modulo_salvo in modulos:
            self.choice_modulo.SetSelection(itens.index(modulo_salvo))
        else:
            self.choice_modulo.SetSelection(0)

    def _modulo_selecionado(self):
        texto = self.choice_modulo.GetStringSelection()
        return None if texto in ('', _SEM_PREFERENCIA) else texto

    def ao_trocar_modulo(self, evento):
        self._popula_vozes()

    def _popula_vozes(self, voz_salva=None):
        modulo = self._modulo_selecionado()
        idioma = None if self.mostrar_todos_idiomas.GetValue() else 'pt'
        try:
            import speechd
            cliente = speechd.SSIPClient('clientmud-consulta-vozes')
            try:
                if modulo:
                    cliente.set_output_module(modulo)
                vozes = list(cliente.list_synthesis_voices(language=idioma))
            finally:
                cliente.close()
        except Exception:
            vozes = listar_vozes(modulo)

        nomes = [nome for nome, _idioma, _variante in vozes]
        itens = [_SEM_PREFERENCIA] + nomes
        self.choice_voz.Set(itens)
        if voz_salva and voz_salva in nomes:
            self.choice_voz.SetSelection(itens.index(voz_salva))
        else:
            self.choice_voz.SetSelection(0)

    def _preferencias_atuais(self):
        voz = self.choice_voz.GetStringSelection()
        return {
            'modulo': self._modulo_selecionado(),
            'voz': None if voz in ('', _SEM_PREFERENCIA) else voz,
            'taxa': self.campo_taxa.GetValue(),
            'volume': self.campo_volume.GetValue(),
        }

    def ao_testar(self, evento):
        testar_voz('Assim vai soar a leitura das mensagens do MUD.', self._preferencias_atuais())

    def ao_restaurar(self, evento):
        self.choice_modulo.SetSelection(0)
        self._popula_vozes()
        self.campo_taxa.SetValue(0)
        self.campo_volume.SetValue(0)
        self.choice_tecla.SetSelection(0)

    def salva(self, evento):
        gerais = self.app.config.config['gerais']
        preferencias = self._preferencias_atuais()
        preferencias['tecla-interromper'] = TECLAS_INTERROMPER[self.choice_tecla.GetSelection()][1]
        gerais['voz-linux'] = preferencias
        self.app.config.atualizaJson()
        self.app.recarrega_saida_voz()
        self.EndModal(wx.ID_OK)
