import wx
from models.trigger import Trigger

class DialogoEditaTrigger(wx.Dialog):
    def __init__(self, parent, trigger_obj):
        self.e_novo = trigger_obj is None
        self.trigger_atual = trigger_obj if not self.e_novo else Trigger()
        titulo = 'Criar Novo Trigger' if self.e_novo else 'Editar Trigger'
        super().__init__(parent, title=titulo)
        painel = wx.Panel(self)

        wx.StaticText(painel, label="Nome:")
        nome_inicial = "" if self.e_novo else self.trigger_atual.nome
        self.campo_nome = wx.TextCtrl(painel, value=nome_inicial)

        wx.StaticText(painel, label="Padrão: aceita coringas")
        self.campo_padrao = wx.TextCtrl(painel, value=self.trigger_atual.padrao)

        wx.StaticText(painel, label="Tipo de Busca:")
        padroes = ['Busca Padrão', 'Busca Regex']
        self.mapa_padroes = {'padrao': 0, 'regex': 1}
        self.choice_padroes = wx.Choice(painel, choices=padroes)
        self.choice_padroes.SetSelection(self.mapa_padroes.get(self.trigger_atual.tipo_match, 0))
        
        wx.StaticText(painel, label="Valor da Ação (Nome do histórico se aplicável):")
        self.campo_acao = wx.TextCtrl(painel, value=self.trigger_atual.valor_acao)
        
        wx.StaticText(painel, label="Ação Principal:")
        tipo_acao = ['Enviar comando', 'Tocar um Som', 'Enviar para um histórico']
        self.mapa_acao = {'comando': 0, 'som': 1, 'historico': 2}
        self.choice_acoes = wx.Choice(painel, choices=tipo_acao)
        self.choice_acoes.SetSelection(self.mapa_acao.get(self.trigger_atual.acao, 0))
        
        wx.StaticText(painel, label="Som Secundário:")
        self.campo_som_acao = wx.TextCtrl(painel, value=self.trigger_atual.som_acao)
        
        wx.StaticText(painel, label="Volume:")
        self.campo_som_volume = wx.SpinCtrl(painel, value=str(self.trigger_atual.som_volume), min=0, max=100)
        
        wx.StaticText(painel, label="Salvar em:")
        opcoes_escopo = ['Apenas este personagem/conexão', 'Todo o MUD', 'Global (Todos os MUDs)']
        self.choice_escopo = wx.Choice(painel, choices=opcoes_escopo)
        self.choice_escopo.SetSelection(self.trigger_atual.escopo)

        self.ativo = wx.CheckBox(painel, label='Ativar trigger')
        self.ativo.SetValue(self.trigger_atual.ativo)

        self.ignora_historico = wx.CheckBox(painel, label='Não mostrar mensagem no histórico principal')
        self.ignora_historico.SetValue(self.trigger_atual.ignorar_historico_principal)
        
        btn_salvar = wx.Button(painel, wx.ID_OK, label='Salvar Trigger')
        btn_salvar.Bind(wx.EVT_BUTTON, self.salvaTrigger)
        
        btn_cancelar = wx.Button(painel, wx.ID_CANCEL, label='Cancelar')
        
        self.campo_nome.SetFocus()

    def salvaTrigger(self, evento):
        nome = self.campo_nome.GetValue().strip()
        padrao = self.campo_padrao.GetValue().strip()
        if not nome or not padrao:
            wx.MessageBox('O nome e o padrão do trigger não podem estar vazios.', 'Erro', wx.OK | wx.ICON_ERROR)
            return
        
        mapa_padroes_inv = {v: k for k, v in self.mapa_padroes.items()}
        mapa_acao_inv = {v: k for k, v in self.mapa_acao.items()}
        
        self.trigger_atual.nome = nome
        self.trigger_atual.padrao = padrao
        self.trigger_atual.tipo_match = mapa_padroes_inv[self.choice_padroes.GetSelection()]
        self.trigger_atual.acao = mapa_acao_inv[self.choice_acoes.GetSelection()]
        self.trigger_atual.valor_acao = self.campo_acao.GetValue()
        self.trigger_atual.ativo = self.ativo.IsChecked()
        self.trigger_atual.ignorar_historico_principal = self.ignora_historico.IsChecked()
        self.trigger_atual.escopo = self.choice_escopo.GetSelection()
        self.trigger_atual.som_acao = self.campo_som_acao.GetValue().strip()
        self.trigger_atual.som_volume = self.campo_som_volume.GetValue()

        self.EndModal(wx.ID_OK)

class DialogoGerenciaTriggers(wx.Dialog):
    def __init__(self, parent, triggers_lista):
        super().__init__(parent, title="Gerenciador de Triggers")
        self.parent = parent
        self.triggers = triggers_lista
        self.alteracoes_feitas = False
        painel = wx.Panel(self)

        self.lista_triggers_ctrl = wx.ListCtrl(painel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.lista_triggers_ctrl.InsertColumn(0, "Nome do Trigger")

        self.btn_adicionar = wx.Button(painel, label="Adicionar...\tCtrl+A")
        self.btn_adicionar.Bind(wx.EVT_BUTTON, self.on_adicionar)

        self.btn_editar = wx.Button(painel, label="Editar...\tCtrl+E")
        self.btn_editar.Bind(wx.EVT_BUTTON, self.on_editar)

        self.btn_remover = wx.Button(painel, label="Remover\tDel")
        self.btn_remover.Bind(wx.EVT_BUTTON, self.on_remover)

        self.btn_ativar_desativar = wx.Button(painel, label="Ativar/Desativar\tCtrl+D")
        self.btn_ativar_desativar.Bind(wx.EVT_BUTTON, self.on_ativar_desativar)

        self.btn_fechar = wx.Button(painel, wx.ID_OK, label="Fechar")

        self.lista_triggers_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_editar)
        self.lista_triggers_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.atualiza_botao_ativar)
        self.lista_triggers_ctrl.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.atualiza_botao_ativar)

        id_adicionar = wx.NewIdRef()
        id_editar = wx.NewIdRef()
        id_remover = wx.NewIdRef()
        id_ativar = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, self.on_adicionar, id=id_adicionar)
        self.Bind(wx.EVT_MENU, self.on_editar, id=id_editar)
        self.Bind(wx.EVT_MENU, self.on_remover, id=id_remover)
        self.Bind(wx.EVT_MENU, self.on_ativar_desativar, id=id_ativar)

        aceleradores = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('A'), id_adicionar),
            (wx.ACCEL_CTRL, ord('E'), id_editar),
            (wx.ACCEL_NORMAL, wx.WXK_DELETE, id_remover),
            (wx.ACCEL_CTRL, ord('D'), id_ativar)
        ])
        self.SetAcceleratorTable(aceleradores)
        self.atualizar_visualizacao_lista()

    def mostraComponentes(self):
        condicao = bool(self.triggers)
        self.lista_triggers_ctrl.Show(condicao)
        self.btn_editar.Show(condicao)
        self.btn_remover.Show(condicao)
        self.btn_ativar_desativar.Show(condicao)

    def atualizar_visualizacao_lista(self):
        self.lista_triggers_ctrl.DeleteAllItems()
        for index, trigger in enumerate(self.triggers):
            self.lista_triggers_ctrl.InsertItem(index, trigger.nome)

        if self.lista_triggers_ctrl.GetItemCount() > 0:
            self.lista_triggers_ctrl.Select(0)
            self.lista_triggers_ctrl.Focus(0)
        else:
            self.btn_adicionar.SetFocus()

        self.mostraComponentes()

    def atualiza_botao_ativar(self, evento):
        index_selecionado = self.lista_triggers_ctrl.GetFirstSelected()
        if index_selecionado != -1:
            trigger = self.triggers[index_selecionado]
            self.btn_ativar_desativar.Enable(True)
            label = "Desativar" if trigger.ativo else "Ativar"
            self.btn_ativar_desativar.SetLabel(f"{label}\tCtrl+D")
        else:
            self.btn_ativar_desativar.Enable(False)
            self.btn_ativar_desativar.SetLabel("Ativar/Desativar\tCtrl+D")

    def on_adicionar(self, evento):
        dlg = DialogoEditaTrigger(self, None)
        if dlg.ShowModal() == wx.ID_OK:
            self.triggers.insert(0, dlg.trigger_atual)
            self.atualizar_visualizacao_lista()
            self.alteracoes_feitas = True
        dlg.Destroy()

    def on_editar(self, evento):
        index_selecionado = self.lista_triggers_ctrl.GetFirstSelected()
        if index_selecionado == -1: return
        dlg = DialogoEditaTrigger(self, self.triggers[index_selecionado])
        if dlg.ShowModal() == wx.ID_OK:
            self.atualizar_visualizacao_lista()
            self.lista_triggers_ctrl.Select(index_selecionado)
            self.lista_triggers_ctrl.Focus(index_selecionado)
            self.alteracoes_feitas = True
        dlg.Destroy()

    def on_remover(self, evento):
        index_selecionado = self.lista_triggers_ctrl.GetFirstSelected()
        if index_selecionado == -1: return
        nome_trigger = self.triggers[index_selecionado].nome
        confirmacao = wx.MessageDialog(self, f"Tem certeza que deseja remover o trigger '{nome_trigger}'?", "Confirmar Remoção", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        if confirmacao.ShowModal() == wx.ID_YES:
            self.triggers.pop(index_selecionado)
            self.atualizar_visualizacao_lista()
            self.alteracoes_feitas = True
        confirmacao.Destroy()

    def on_ativar_desativar(self, evento):
        index = self.lista_triggers_ctrl.GetFirstSelected()
        if index == -1: return
        self.triggers[index].ativo = not self.triggers[index].ativo
        self.atualizar_visualizacao_lista()
        self.alteracoes_feitas = True