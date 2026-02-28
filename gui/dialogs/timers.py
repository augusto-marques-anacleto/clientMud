import wx
from models.timer import Timer
from time import time, sleep
from threading import Thread, Event, Lock
from core.processor import Processor

class GerenciadorTimers(Thread):
    def __init__(self, timers_config, cliente_ref):
        super().__init__(daemon=True)
        self.cliente = cliente_ref
        self.timers_ativos = []
        self._parar_evento = Event()
        self._lock = Lock() 

        agora = time()
        for config in timers_config:
            if config.get('ativo', False):
                intervalo = config.get('intervalo', 60)
                if intervalo > 0:
                    self.timers_ativos.append({
                        'id': config.get('id'),
                        'comando': config.get('comando'),
                        'intervalo': intervalo,
                        'proxima_execucao': agora + intervalo
                    })

    def run(self):
        while not self._parar_evento.is_set():
            agora = time()
            with self._lock:
                timers_para_executar = []
                for timer in self.timers_ativos:
                    if agora >= timer['proxima_execucao']:
                        timers_para_executar.append(timer)
                        timer['proxima_execucao'] = agora + timer['intervalo'] 
                        
            for timer in timers_para_executar:
                if self.cliente.ativo:
                    lista_comandos = Processor._processaComandosScript(timer['comando'])
                    for comando_individual in lista_comandos:
                        self.cliente.enviaComando(comando_individual)
            sleep(0.5)

    def parar(self):
        self._parar_evento.set()

    def atualizar_timers(self, novos_timers_config):
        agora = time()
        with self._lock:
            self.timers_ativos.clear()
            for config in novos_timers_config:
                if config.get('ativo', False):
                    intervalo = config.get('intervalo', 60)
                    if intervalo > 0:
                        self.timers_ativos.append({
                            'id': config.get('id'),
                            'comando': config.get('comando'),
                            'intervalo': intervalo,
                            'proxima_execucao': agora + intervalo 
                        })

class DialogoEditaTimer(wx.Dialog):
    def __init__(self, parent, timer_obj):
        self.e_novo = timer_obj is None
        self.timer_atual = timer_obj if not self.e_novo else Timer()
        titulo = 'Criar Novo Timer' if self.e_novo else 'Editar Timer'
        super().__init__(parent, title=titulo)
        painel = wx.Panel(self)
        
        wx.StaticText(painel, label="Nome do Timer:")
        self.campo_nome = wx.TextCtrl(painel, value=self.timer_atual.nome if not self.e_novo else "")
        
        wx.StaticText(painel, label="Comando:")
        self.campo_comando = wx.TextCtrl(painel, value=self.timer_atual.comando, style=wx.TE_MULTILINE)
        
        wx.StaticText(painel, label="Intervalo (segundos):")
        self.campo_intervalo = wx.SpinCtrl(painel, min=1, max=3600, initial=self.timer_atual.intervalo)
        
        wx.StaticText(painel, label="Salvar em:")
        opcoes_escopo = ['Apenas este personagem/conexão', 'Todo o MUD', 'Global (Todos os MUDs)']
        self.choice_escopo = wx.Choice(painel, choices=opcoes_escopo)
        self.choice_escopo.SetSelection(self.timer_atual.escopo)

        self.ativo = wx.CheckBox(painel, label='Ativar timer')
        self.ativo.SetValue(self.timer_atual.ativo)
        
        btn_salvar = wx.Button(painel, wx.ID_OK, label='Salvar')
        btn_salvar.Bind(wx.EVT_BUTTON, self.salvaTimer)
        
        btn_cancelar = wx.Button(painel, wx.ID_CANCEL, label='Cancelar')
        
        self.campo_nome.SetFocus()

    def salvaTimer(self, evento):
        if not self.campo_nome.GetValue().strip() or not self.campo_comando.GetValue().strip():
            wx.MessageBox("O nome e o comando devem ser preenchidos.", "Erro", wx.ICON_ERROR)
            return

        self.timer_atual.nome = self.campo_nome.GetValue()
        self.timer_atual.comando = self.campo_comando.GetValue()
        self.timer_atual.intervalo = self.campo_intervalo.GetValue()
        self.timer_atual.ativo = self.ativo.IsChecked()
        self.timer_atual.escopo = self.choice_escopo.GetSelection()
        self.EndModal(wx.ID_OK)

class DialogoGerenciaTimers(wx.Dialog):
    def __init__(self, parent, timers_lista, gerenciador_timers_ref):
        super().__init__(parent, title="Gerenciador de Timers")
        self.parent = parent
        self.timers = timers_lista
        self.gerenciador_timers = gerenciador_timers_ref
        self.alteracoes_feitas = False
        painel = wx.Panel(self)
        
        self.lista_ctrl = wx.ListCtrl(painel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.lista_ctrl.InsertColumn(0, "Ativo")
        self.lista_ctrl.InsertColumn(1, "Nome")
        self.lista_ctrl.InsertColumn(2, "Intervalo")
        self.lista_ctrl.InsertColumn(3, "Comando")
        
        self.btn_adicionar = wx.Button(painel, label="Adicionar...\tCtrl+A")
        self.btn_adicionar.Bind(wx.EVT_BUTTON, self.on_adicionar)

        self.btn_editar = wx.Button(painel, label="Editar...\tCtrl+E")
        self.btn_editar.Bind(wx.EVT_BUTTON, self.on_editar)

        self.btn_remover = wx.Button(painel, label="Remover\tDel")
        self.btn_remover.Bind(wx.EVT_BUTTON, self.on_remover)

        self.btn_ativar_desativar = wx.Button(painel, label="Ativar/Desativar")
        self.btn_ativar_desativar.Bind(wx.EVT_BUTTON, self.on_ativar_desativar)

        self.btn_fechar = wx.Button(painel, wx.ID_OK, label="Fechar")

        self.lista_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_editar)
        self.lista_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.atualiza_botao_ativar)
        self.lista_ctrl.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.atualiza_botao_ativar)

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
        condicao = bool(self.timers)
        self.lista_ctrl.Show(condicao)
        self.btn_editar.Show(condicao)
        self.btn_remover.Show(condicao)
        self.btn_ativar_desativar.Show(condicao)

    def atualizar_visualizacao_lista(self):
        item_selecionado = self.lista_ctrl.GetFirstSelected()
        self.lista_ctrl.DeleteAllItems()
        for index, timer in enumerate(self.timers):
            estado = "Sim" if timer.ativo else "Não"
            self.lista_ctrl.InsertItem(index, estado)
            self.lista_ctrl.SetItem(index, 1, timer.nome)
            self.lista_ctrl.SetItem(index, 2, str(timer.intervalo))
            self.lista_ctrl.SetItem(index, 3, timer.comando)
        
        if self.lista_ctrl.GetItemCount() > 0:
            idx_foco = item_selecionado if item_selecionado != -1 else 0
            self.lista_ctrl.Select(idx_foco)
            self.lista_ctrl.Focus(idx_foco)
        else:
            self.btn_adicionar.SetFocus()

        self.atualiza_botao_ativar(None)
        self.mostraComponentes()

    def atualiza_botao_ativar(self, evento):
        index_selecionado = self.lista_ctrl.GetFirstSelected()
        if index_selecionado != -1:
            self.btn_ativar_desativar.Enable(True)
            label = "Desativar" if self.timers[index_selecionado].ativo else "Ativar"
            self.btn_ativar_desativar.SetLabel(f"{label}\tCtrl+D")
        else:
            self.btn_ativar_desativar.Enable(False)
            self.btn_ativar_desativar.SetLabel("Ativar/Desativar\tCtrl+D")

    def on_adicionar(self, evento):
        dlg = DialogoEditaTimer(self, None)
        if dlg.ShowModal() == wx.ID_OK:
            self.timers.insert(0, dlg.timer_atual)
            self.atualizar_visualizacao_lista()
            self.alteracoes_feitas = True
            self.atualiza_gerenciador_timers()
        dlg.Destroy()

    def on_editar(self, evento):
        index = self.lista_ctrl.GetFirstSelected()
        if index == -1: return
        dlg = DialogoEditaTimer(self, self.timers[index])
        if dlg.ShowModal() == wx.ID_OK:
            self.atualizar_visualizacao_lista()
            self.alteracoes_feitas = True
            self.atualiza_gerenciador_timers()
        dlg.Destroy()
        
    def on_remover(self, evento):
        index = self.lista_ctrl.GetFirstSelected()
        if index == -1: return
        confirmacao = wx.MessageDialog(self, f"Remover o timer '{self.timers[index].nome}'?", "Confirmar", wx.YES_NO | wx.ICON_QUESTION)
        if confirmacao.ShowModal() == wx.ID_YES:
            self.timers.pop(index)
            self.atualizar_visualizacao_lista()
            self.alteracoes_feitas = True
            self.atualiza_gerenciador_timers()
        confirmacao.Destroy()

    def on_ativar_desativar(self, evento):
        index = self.lista_ctrl.GetFirstSelected()
        if index == -1: return
        self.timers[index].ativo = not self.timers[index].ativo
        self.atualizar_visualizacao_lista()
        self.alteracoes_feitas = True
        self.atualiza_gerenciador_timers()

    def atualiza_gerenciador_timers(self):
        if self.gerenciador_timers:
            configs_atuais = [t.to_dict() for t in self.timers]
            self.gerenciador_timers.atualizar_timers(configs_atuais)