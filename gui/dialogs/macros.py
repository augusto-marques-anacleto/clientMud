import wx
import re
from models.macro import Macro

class DialogoAcaoGravacao(wx.Dialog):
    def __init__(self, parent, comandos_gravados):
        super().__init__(parent, title="Gravação Interrompida")
        self.comandos_str_espaco = " ".join(comandos_gravados)
        self.comandos_str_ponto_virgula = " ; ".join(comandos_gravados)
        self.acao_escolhida = None
        
        painel = wx.Panel(self)
        
        texto = wx.StaticText(painel, label=f"Você gravou {len(comandos_gravados)} comandos.\nO que deseja fazer com esta rota?")
        
        self.btn_copiar = wx.Button(painel, label="Copiar para a Área de Transferência")
        self.btn_copiar.Bind(wx.EVT_BUTTON, self.on_copiar)
        
        self.btn_salvar_txt = wx.Button(painel, label="Salvar em Arquivo de Texto")
        self.btn_salvar_txt.Bind(wx.EVT_BUTTON, self.on_salvar_txt)
        
        self.btn_adicionar_macro = wx.Button(painel, label="Adicionar como Macro/Rota")
        self.btn_adicionar_macro.Bind(wx.EVT_BUTTON, self.on_adicionar)
        
        self.btn_descartar = wx.Button(painel, wx.ID_CANCEL, label="Descartar Gravação")
        
        self.btn_adicionar_macro.SetFocus()

    def on_copiar(self, evento):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.comandos_str_espaco))
            wx.TheClipboard.Close()
            wx.MessageBox("Comandos copiados (separados por espaço)!", "Sucesso", wx.ICON_INFORMATION)
            self.acao_escolhida = 'copiar'
            self.EndModal(wx.ID_OK)

    def on_salvar_txt(self, evento):
        estilo = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        dlg = wx.FileDialog(self, "Salvar Rota em TXT", wildcard="Arquivos de Texto (*.txt)|*.txt", style=estilo)
        if dlg.ShowModal() == wx.ID_OK:
            caminho = dlg.GetPath()
            try:
                with open(caminho, 'w', encoding='utf-8') as f:
                    f.write(self.comandos_str_espaco)
                wx.MessageBox("Arquivo salvo com sucesso!", "Sucesso", wx.ICON_INFORMATION)
                self.acao_escolhida = 'salvar'
                self.EndModal(wx.ID_OK)
            except Exception as e:
                wx.MessageBox(f"Erro ao salvar arquivo: {e}", "Erro", wx.ICON_ERROR)
        dlg.Destroy()

    def on_adicionar(self, evento):
        self.acao_escolhida = 'adicionar'
        self.EndModal(wx.ID_OK)

class DialogoEditaMacro(wx.Dialog):
    def __init__(self, parent, macro=None, comandos_iniciais=""):
        super().__init__(parent, title="Macro / Rota")
        self.macro_original = macro
        painel = wx.Panel(self)

        wx.StaticText(painel, label="Nome da Macro:")
        self.campo_nome = wx.TextCtrl(painel)
        
        wx.StaticText(painel, label="Comandos separados por ponto e vírgula (;):")
        self.campo_comandos = wx.TextCtrl(painel)

        wx.StaticText(painel, label="Intervalo entre cada comando (em segundos, apenas números e o separador ponto separando a parte inteira da fracionária):")
        self.campo_espera = wx.TextCtrl(painel)

        
        wx.StaticText(painel, label="Salvar em:")
        opcoes_escopo = ['Apenas este personagem/conexão', 'Todo o MUD', 'Global (Todos os MUDs)']
        self.choice_escopo = wx.Choice(painel, choices=opcoes_escopo)
        
        self.ativo = wx.CheckBox(painel, label='Ativar macro')
        
        self.btn_ok = wx.Button(painel, wx.ID_OK, "OK")
        self.btn_ok.Bind(wx.EVT_BUTTON, self.salva_macro)
        
        self.btn_cancelar = wx.Button(painel, wx.ID_CANCEL, "Cancelar")
        
        if macro:
            self.campo_nome.SetValue(macro.nome)
            self.campo_comandos.SetValue(macro.comandos)
            self.campo_espera.SetValue(str(macro.espera))
            self.choice_escopo.SetSelection(macro.escopo)
            self.ativo.SetValue(macro.ativo)
        else:
            self.campo_comandos.SetValue(comandos_iniciais)
            self.campo_espera.SetValue("0.1")
            self.choice_escopo.SetSelection(0)
            self.ativo.SetValue(True)
            
        self.campo_nome.SetFocus()

    def salva_macro(self, evt):
        if not self.campo_nome.GetValue().strip() or not self.campo_comandos.GetValue().strip() or not re.fullmatch(r'[0-9.]+', self.campo_espera.GetValue()):
            wx.MessageBox("Preencha o nome, os comandos e o tempo de espera corretamente.", "Aviso", wx.ICON_WARNING)
            return
        self.EndModal(wx.ID_OK)

    def get_macro(self):
        dados = {
            'id': getattr(self.macro_original, 'id', None),
            'nome': self.campo_nome.GetValue().strip(),
            'comandos': self.campo_comandos.GetValue().strip(),
            'espera': float(self.campo_espera.GetValue().strip()),
            'ativo': self.ativo.IsChecked(),
            'escopo': self.choice_escopo.GetSelection()
        }
        return Macro(dados)

class DialogoGerenciaMacros(wx.Dialog):
    def __init__(self, parent, lista_macros):
        super().__init__(parent, title="Gerenciar Macros / Rotas")
        self.parent = parent
        self.lista_macros = lista_macros
        self.alteracoes_feitas = False
        painel = wx.Panel(self)

        self.lista = wx.ListCtrl(painel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.lista.InsertColumn(0, "Nome")
        self.lista.InsertColumn(1, "Comandos")
        self.lista.InsertColumn(2, "Tempo de espera")

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
        condicao = bool(self.lista_macros)
        self.lista.Show(condicao)
        self.btn_editar.Show(condicao)
        self.btn_remover.Show(condicao)
        self.btn_ativar_desativar.Show(condicao)

    def atualiza_lista(self, manter_indice=None):
        self.lista.DeleteAllItems()
        for m in self.lista_macros:
            idx = self.lista.GetItemCount()
            self.lista.InsertItem(idx, getattr(m, 'nome', ''))
            self.lista.SetItem(idx, 1, getattr(m, 'comandos', ''))
            self.lista.SetItem(idx, 2, str(getattr(m, 'espera', '')))

        total = self.lista.GetItemCount()
        if total > 0:
            idx_foco = manter_indice if manter_indice is not None and manter_indice < total else 0
            self.lista.Select(idx_foco)
            self.lista.Focus(idx_foco)
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
            label = "Desativar" if self.lista_macros[index_selecionado].ativo else "Ativar"
            self.btn_ativar_desativar.SetLabel(f"{label}\tCtrl+D")
        else:
            self.btn_ativar_desativar.Enable(False)
            self.btn_ativar_desativar.SetLabel("Ativar/Desativar\tCtrl+D")

    def adiciona(self, evt):
        dlg = DialogoEditaMacro(self, None)
        if dlg.ShowModal() == wx.ID_OK:
            self.lista_macros.insert(0, dlg.get_macro())
            self.atualiza_lista()
            self.alteracoes_feitas = True
        dlg.Destroy()

    def edita(self, evt):
        indice = self.selecionado()
        if indice is None: return
        dlg = DialogoEditaMacro(self, self.lista_macros[indice])
        if dlg.ShowModal() == wx.ID_OK:
            self.lista_macros[indice] = dlg.get_macro()
            self.atualiza_lista()
            self.lista.Select(indice)
            self.lista.Focus(indice)
            self.alteracoes_feitas = True
        dlg.Destroy()

    def remove(self, evt):
        indice = self.selecionado()
        if indice is None: return
        confirmacao = wx.MessageDialog(self, "Tem certeza que deseja remover esta macro?", "Confirmar", wx.YES_NO | wx.ICON_QUESTION)
        if confirmacao.ShowModal() == wx.ID_YES:
            del self.lista_macros[indice]
            self.atualiza_lista()
            self.alteracoes_feitas = True
        confirmacao.Destroy()

    def on_ativar_desativar(self, evento):
        index = self.lista.GetFirstSelected()
        if index == -1: return
        self.lista_macros[index].ativo = not self.lista_macros[index].ativo
        estado = "ativada" if self.lista_macros[index].ativo else "desativada"
        wx.GetApp().fale(f"Macro {estado}")
        self.atualiza_lista(manter_indice=index)
        self.alteracoes_feitas = True