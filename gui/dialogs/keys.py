import wx
from models.key import Key

class DialogoEditaKey(wx.Dialog):
    def __init__(self, parent, key=None):
        super().__init__(parent, title="Atalho")
        self.key_original = key
        painel = wx.Panel(self)

        wx.StaticText(painel, label="Nome:")
        self.campo_nome = wx.TextCtrl(painel)
        
        wx.StaticText(painel, label="Tecla:")
        self.campo_tecla = wx.TextCtrl(painel)
        
        wx.StaticText(painel, label="Comando:")
        self.campo_comando = wx.TextCtrl(painel)
        
        wx.StaticText(painel, label="Salvar em:")
        opcoes_escopo = ['Apenas este personagem/conexão', 'Todo o MUD', 'Global (Todos os MUDs)']
        self.choice_escopo = wx.Choice(painel, choices=opcoes_escopo)
        self.choice_escopo.SetSelection(key.escopo if key else 0)

        self.ativo = wx.CheckBox(painel, label='Ativar key')
        self.ativo.SetValue(key.ativo if key else True)
        
        self.btn_ok = wx.Button(painel, wx.ID_OK, "OK")
        self.btn_ok.Bind(wx.EVT_BUTTON, self.salva_key)
        
        self.btn_cancelar = wx.Button(painel, wx.ID_CANCEL, "Cancelar")
        
        self.campo_tecla.Bind(wx.EVT_KEY_DOWN, self.captura_tecla)
        self.campo_tecla.Bind(wx.EVT_CHAR, self.bloqueia_char)
        
        if key:
            self.campo_nome.SetValue(key.nome)
            self.campo_tecla.SetValue(key.tecla)
            self.campo_comando.SetValue(key.comando)
            
        self.campo_nome.SetFocus()

    def bloqueia_char(self, evento):
        pass

    def _bloqueada(self, keycode):
        b = {
            wx.WXK_TAB, wx.WXK_UP, wx.WXK_DOWN, wx.WXK_LEFT, wx.WXK_RIGHT,
            wx.WXK_HOME, wx.WXK_END, wx.WXK_PAGEUP, wx.WXK_PAGEDOWN,
            wx.WXK_INSERT, wx.WXK_DELETE, wx.WXK_BACK, wx.WXK_RETURN, wx.WXK_ESCAPE
        }
        return keycode in b

    def _evento_para_string(self, evt):
        if self._bloqueada(evt.GetKeyCode()):
            return ""

        mods = []
        if evt.ControlDown(): mods.append("Ctrl")
        if evt.AltDown(): mods.append("Alt")
        if evt.ShiftDown(): mods.append("Shift")

        code = evt.GetKeyCode()
        tecla = ""
        
        if 48 <= code <= 57: tecla = f"{code - 48}"
        elif 65 <= code <= 90: tecla = chr(code)
        elif wx.WXK_F1 <= code <= wx.WXK_F12: tecla = f"F{code - wx.WXK_F1 + 1}"
        elif wx.WXK_NUMPAD0 <= code <= wx.WXK_NUMPAD9: tecla = f"Num{code - wx.WXK_NUMPAD0}"
        else: return ""
        return "+".join(mods + [tecla]) if mods else tecla

    def captura_tecla(self, evento):
        s = self._evento_para_string(evento)
        if s:
            self.campo_tecla.SetValue(s)
        evento.Skip(False)

    def salva_key(self, evt):
        if not self.campo_nome.GetValue().strip() or not self.campo_tecla.GetValue().strip() or not self.campo_comando.GetValue().strip():
            wx.MessageBox("Preencha todos os campos do atalho.", "Aviso", wx.ICON_WARNING)
            return
        self.EndModal(wx.ID_OK)

    def get_key(self):
        dados = {
            'id': getattr(self.key_original, 'id', None),
            'nome': self.campo_nome.GetValue(),
            'tecla': self.campo_tecla.GetValue(),
            'comando': self.campo_comando.GetValue(),
            'ativo': self.ativo.IsChecked(),
            'escopo': self.choice_escopo.GetSelection()
        }
        return Key(dados)

class DialogoGerenciaKeys(wx.Dialog):
    def __init__(self, parent, lista_keys):
        super().__init__(parent, title="Gerenciar Atalhos")
        self.parent = parent
        self.lista_keys = lista_keys
        painel = wx.Panel(self)

        self.lista = wx.ListCtrl(painel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.lista.InsertColumn(0, "Nome")
        self.lista.InsertColumn(1, "Tecla")
        self.lista.InsertColumn(2, "Comando")
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.edita)

        self.btn_adicionar = wx.Button(painel, label="Adicionar...\tCtrl+A")
        self.btn_adicionar.Bind(wx.EVT_BUTTON, self.adiciona)

        self.btn_editar = wx.Button(painel, label="Editar...\tCtrl+E")
        self.btn_editar.Bind(wx.EVT_BUTTON, self.edita)

        self.btn_remover = wx.Button(painel, label="Remover\tDel")
        self.btn_remover.Bind(wx.EVT_BUTTON, self.remove)

        self.btn_ativar_desativar = wx.Button(painel, label="Ativar/Desativar\tCtrl+D")
        self.btn_ativar_desativar.Bind(wx.EVT_BUTTON, self.on_ativar_desativar)

        self.btn_fechar = wx.Button(painel, wx.ID_OK, label="Fechar")

        self.lista.Bind(wx.EVT_LIST_ITEM_SELECTED, self.atualiza_botao_ativar)
        self.lista.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.atualiza_botao_ativar)

        id_adicionar = wx.NewIdRef()
        id_editar = wx.NewIdRef()
        id_remover = wx.NewIdRef()
        id_ativar = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, self.adiciona, id=id_adicionar)
        self.Bind(wx.EVT_MENU, self.edita, id=id_editar)
        self.Bind(wx.EVT_MENU, self.remove, id=id_remover)
        self.Bind(wx.EVT_MENU, self.on_ativar_desativar, id=id_ativar)

        aceleradores = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('A'), id_adicionar),
            (wx.ACCEL_CTRL, ord('E'), id_editar),
            (wx.ACCEL_NORMAL, wx.WXK_DELETE, id_remover),
            (wx.ACCEL_CTRL, ord('D'), id_ativar)
        ])
        self.SetAcceleratorTable(aceleradores)
        self.atualiza_lista()

    def mostraComponentes(self):
        condicao = bool(self.lista_keys)
        self.lista.Show(condicao)
        self.btn_editar.Show(condicao)
        self.btn_remover.Show(condicao)
        self.btn_ativar_desativar.Show(condicao)

    def atualiza_lista(self):
        self.lista.DeleteAllItems()
        for k in self.lista_keys:
            idx = self.lista.GetItemCount()
            self.lista.InsertItem(idx, getattr(k, 'nome', ''))
            self.lista.SetItem(idx, 1, getattr(k, 'tecla', ''))
            self.lista.SetItem(idx, 2, getattr(k, 'comando', ''))

        if self.lista.GetItemCount() > 0:
            self.lista.Select(0)
            self.lista.Focus(0)
        else:
            self.btn_adicionar.SetFocus()
        self.mostraComponentes()

    def selecionado(self):
        ind = self.lista.GetFirstSelected()
        return ind if ind != -1 else None

    def atualiza_botao_ativar(self, evento):
        index_selecionado = self.lista.GetFirstSelected()
        if index_selecionado != -1:
            self.btn_ativar_desativar.Enable(True)
            label = "Desativar" if self.lista_keys[index_selecionado].ativo else "Ativar"
            self.btn_ativar_desativar.SetLabel(f"{label}\tCtrl+D")
        else:
            self.btn_ativar_desativar.Enable(False)
            self.btn_ativar_desativar.SetLabel("Ativar/Desativar\tCtrl+D")

    def adiciona(self, evt):
        dlg = DialogoEditaKey(self, None)
        if dlg.ShowModal() == wx.ID_OK:
            self.lista_keys.insert(0, dlg.get_key())
            self.atualiza_lista()
        dlg.Destroy()

    def edita(self, evt):
        indice = self.selecionado()
        if indice is None: return
        dlg = DialogoEditaKey(self, self.lista_keys[indice])
        if dlg.ShowModal() == wx.ID_OK:
            self.lista_keys[indice] = dlg.get_key()
            self.atualiza_lista()
            self.lista.Select(indice)
            self.lista.Focus(indice)
        dlg.Destroy()

    def remove(self, evt):
        indice = self.selecionado()
        if indice is None: return
        confirmacao = wx.MessageDialog(self, f"Tem certeza que deseja remover este atalho?", "Confirmar", wx.YES_NO | wx.ICON_QUESTION)
        if confirmacao.ShowModal() == wx.ID_YES:
            del self.lista_keys[indice]
            self.atualiza_lista()
        confirmacao.Destroy()

    def on_ativar_desativar(self, evento):
        index = self.lista.GetFirstSelected()
        if index == -1: return
        self.lista_keys[index].ativo = not self.lista_keys[index].ativo
        self.atualiza_lista()