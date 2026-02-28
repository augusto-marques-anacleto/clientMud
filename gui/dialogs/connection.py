import wx
import wx.lib.newevent
from pathlib import Path
from threading import Thread
import sys
import json
from core.backup import GerenciadorBackup

EventoResultadoConexao, EVT_RESULTADO_CONEXAO = wx.lib.newevent.NewEvent()

class ThreadIniciaConexao(Thread):
    def __init__(self, janela_pai, args_conexao, app_context, json_personagem=None):
        super().__init__(daemon=True)
        self.janela_pai = janela_pai
        self.args_conexao = args_conexao
        self.json_personagem = json_personagem
        self.app = app_context

    def run(self):
        endereco, porta = self.args_conexao
        tentativa_conexao = self.app.client.conectaServidor(endereco, porta)
        evt = EventoResultadoConexao(
            tentativa_conexao=tentativa_conexao, 
            json_personagem=self.json_personagem, 
            endereco=endereco, 
            porta=porta
        )
        wx.PostEvent(self.janela_pai, evt)

class DialogoConectando(wx.Dialog):
    def __init__(self, pai, args, json=None):
        super().__init__(parent=pai, title='Conectando')
        self.app = wx.GetApp()
        self.Bind(EVT_RESULTADO_CONEXAO, self.retornaConexao)
        self.dados_conexao = None
        painel = wx.Panel(self)
        
        self.spinner = wx.ActivityIndicator(painel)
        self.spinner.Start()
        
        wx.StaticText(painel, label=f"Tentando conectar em: {args[0]}\nPor favor, aguarde...")
        
        thread_conexao = ThreadIniciaConexao(self, args, self.app, json)
        thread_conexao.start()

    def retornaConexao(self, evento):
        if evento.tentativa_conexao:
            self.dados_conexao = {
                'json_personagem': evento.json_personagem,
                'endereco': evento.endereco,
                'porta': evento.porta
            }
            self.EndModal(wx.ID_OK)
        else:
            self.EndModal(wx.ID_CANCEL)

class DialogoConexaoManual(wx.Dialog):
    def __init__(self, pai=None):
        super().__init__(parent=pai, title="Conexão")
        self.app = wx.GetApp()
        painel = wx.Panel(self)
        
        wx.StaticText(painel, label="&Endereço:")
        self.endereco = wx.TextCtrl(painel)
        
        wx.StaticText(painel, label="&Porta:")
        self.porta = wx.SpinCtrl(painel, min=1, max=65535)
        
        if self.app.config.config['gerais'].get('ultima-conexao'):
            self.endereco.SetValue(self.app.config.config['gerais']['ultima-conexao'][0])
            self.porta.SetValue(self.app.config.config['gerais']['ultima-conexao'][1])
            
        btnConecta = wx.Button(painel, wx.ID_OK, label="C&onectar")
        btnConecta.Bind(wx.EVT_BUTTON, self.confirma)
        
        btnCancela = wx.Button(painel, wx.ID_CANCEL, label="&Cancelar")
        btnCancela.Bind(wx.EVT_BUTTON, self.cancela)

    def confirma(self, evento):
        if not self.endereco.GetValue().strip():
            wx.MessageBox("Por favor, preencha o campo de endereço.", "Erro")
            self.endereco.SetFocus()
            return
        if self.porta.GetValue() == 1 or not self.porta.GetValue():
            wx.MessageBox("Por favor, preencha o campo da porta.", "Erro")
            self.porta.SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def cancela(self, evento):
        self.EndModal(wx.ID_CANCEL)

class DialogoPrimeiroAcesso(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Bem-vindo")
        painel = wx.Panel(self)
        
        wx.StaticText(painel, label="Nenhum personagem foi encontrado.\nO que você deseja fazer para começar?")
        
        self.btn_criar = wx.Button(painel, label="Criar Novo Personagem")
        self.btn_importar = wx.Button(painel, label="Restaurar Backup")
        
        self.btn_criar.Bind(wx.EVT_BUTTON, self.ao_criar)
        self.btn_importar.Bind(wx.EVT_BUTTON, self.ao_importar)
        
        self.acao_escolhida = None
        self.btn_importar.SetFocus()

    def ao_criar(self, evento):
        self.acao_escolhida = "criar"
        self.EndModal(wx.ID_OK)

    def ao_importar(self, evento):
        estilo = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        dlg = wx.FileDialog(self, "Selecione o arquivo de Backup", wildcard="Backup MUD (*.mudbak)|*.mudbak", style=estilo)
        
        resultado = dlg.ShowModal()
        caminho = dlg.GetPath() if resultado == wx.ID_OK else None
        dlg.Destroy()
        
        if resultado == wx.ID_OK:
            gerenciador = GerenciadorBackup(Path.cwd())
            sucesso, mensagem = gerenciador.importar(caminho)
            
            if sucesso:
                try:
                    wx.GetApp().fale("Backup restaurado com sucesso!")
                except:
                    pass
                wx.MessageBox("Backup restaurado com sucesso! O aplicativo será reiniciado automaticamente.", "Sucesso", wx.ICON_INFORMATION)
                self.acao_escolhida = "importado"
                self.EndModal(wx.ID_OK)
                import os
                import sys
                os.execv(sys.executable, [sys.executable] + sys.argv[1:])
            else:
                try:
                    wx.GetApp().fale("Erro ao restaurar backup.")
                except:
                    pass
                wx.MessageBox(mensagem, "Erro", wx.ICON_ERROR)

class DialogoEntrada(wx.Dialog):
    def __init__(self, pai):
        super().__init__(parent=pai, title="Conexões")
        self.app = wx.GetApp()
        painel = wx.Panel(self)
        self.Bind(wx.EVT_CHAR_HOOK, self.teclaPressionada)
        self.Bind(wx.EVT_CLOSE, self.encerraAplicativo)
        
        self.conectado = False
        self.dados_conexao = None
        self.dialogo_conexao = None
        self.personagem_conectado = None
        
        self.listaDePersonagens = self.app.config.config['personagens'] if self.app.config.config else []
        self.listBox = wx.ListBox(painel, choices=self.listaDePersonagens)
        if len(self.listaDePersonagens) > 0:
            self.listBox.SetSelection(0)
            
        self.btnConecta = wx.Button(painel, label="Conectar")
        self.btnConecta.Bind(wx.EVT_BUTTON, self.conecta)
        
        btnAdicionaPersonagem = wx.Button(painel, label="Adicionar personagem\tCtrl+A")
        btnAdicionaPersonagem.Bind(wx.EVT_BUTTON, self.adicionaPersonagem)
        
        self.btnEditaPersonagem = wx.Button(painel, label="Editar personagem\tCtrl+E")
        self.btnEditaPersonagem.Bind(wx.EVT_BUTTON, self.editaPersonagem)
        
        self.btnRemovePersonagem = wx.Button(painel, label="Remover personagem\tDel")
        self.btnRemovePersonagem.Bind(wx.EVT_BUTTON, self.removePersonagem)
        
        btnConexaomanual = wx.Button(painel, label="Conexão manual\tCtrl+M")
        btnConexaomanual.Bind(wx.EVT_BUTTON, self.conexaomanual)
        
        btnSaida = wx.Button(painel, wx.ID_CANCEL, label='Sair\tCtrl+Q')
        
        self.mostraComponentes()
        
        ids = {
            'adicionar': btnAdicionaPersonagem.GetId(),
            'editar': self.btnEditaPersonagem.GetId(),
            'remover': self.btnRemovePersonagem.GetId(),
            'manual': btnConexaomanual.GetId(),
            'sair': btnSaida.GetId()
        }
        entradas = [
            (wx.ACCEL_CTRL, ord('a'), ids['adicionar']),
            (wx.ACCEL_CTRL, ord('e'), ids['editar']),
            (wx.ACCEL_NORMAL, wx.WXK_DELETE, ids['remover']),
            (wx.ACCEL_CTRL, ord('m'), ids['manual']),
            (wx.ACCEL_CTRL, ord('q'), ids['sair'])
        ]
        self.SetAcceleratorTable(wx.AcceleratorTable(entradas))

        if not self.listaDePersonagens:
            wx.CallAfter(self.verificaPrimeiroAcesso)

    def verificaPrimeiroAcesso(self):
        dlg = DialogoPrimeiroAcesso(self)
        dlg.ShowModal()
        acao = dlg.acao_escolhida
        dlg.Destroy()
        
        if acao == "importado":
            sys.exit(0)
        elif acao == "criar":
            self.adicionaPersonagem(None)
        else:
            self.encerraAplicativo(None)

    def mostraComponentes(self):
        condicao = bool(self.listaDePersonagens)
        self.listBox.Show(condicao)
        self.btnConecta.Show(condicao)
        self.btnEditaPersonagem.Show(condicao)
        self.btnRemovePersonagem.Show(condicao)

    def teclaPressionada(self, evento):
        if evento.GetKeyCode() == wx.WXK_RETURN and self.listBox.HasFocus():
            self.conecta(evento=None)
        else:
            evento.Skip()

    def conecta(self, evento):
        if self.listBox.GetSelection() == wx.NOT_FOUND: return
        nome_personagem = self.listaDePersonagens[self.listBox.GetSelection()]
        json_data = self.app.personagem.carregaPersonagem(nome_personagem)
        
        if json_data is None:
            wx.MessageBox(f"Não foi possível carregar o personagem '{nome_personagem}'.\nO arquivo de configuração pode estar ausente ou corrompido.", "Erro", wx.ICON_ERROR)
            self.listaDePersonagens.remove(nome_personagem)
            self.listBox.Set(self.listaDePersonagens)
            self.app.config.removePersonagem(nome_personagem)
            return
            
        pasta_base_personagem = Path(self.app.config.config['gerais']['pastas-dos-muds'][nome_personagem])
        
        arquivo_json = pasta_base_personagem / f"{nome_personagem}.json"
        if arquivo_json.exists():
            try:
                with open(arquivo_json, 'r', encoding='utf-8') as f:
                    dados_frescos = json.load(f)
                    json_data.update(dados_frescos)
            except:
                pass
                
        pasta_sons = pasta_base_personagem.parent / 'sons'
        pasta_logs = pasta_base_personagem / 'logs'
        pasta_scripts = pasta_base_personagem / 'scripts'
        
        pasta_base_personagem.mkdir(parents=True, exist_ok=True)
        pasta_sons.mkdir(parents=True, exist_ok=True)
        pasta_logs.mkdir(parents=True, exist_ok=True)
        pasta_scripts.mkdir(parents=True, exist_ok=True)
        
        self.app.client.definePastaLog(str(pasta_logs), json_data['nome'])
        self.app.msp.definePastaSons(pasta_sons)
        
        endereco_limpo = str(json_data.get('endereço', '')).strip()
        porta_limpa = int(json_data.get('porta', 4000))
        
        args = (endereco_limpo, porta_limpa)
        dialogo_conexao = DialogoConectando(self, args, json_data)
        resultado = dialogo_conexao.ShowModal()
        
        if resultado == wx.ID_OK:
            self.dados_conexao = dialogo_conexao.dados_conexao
            dialogo_conexao.Destroy()
            self.EndModal(wx.ID_OK)
        else:
            dialogo_conexao.Destroy()
            wx.MessageBox('Não foi possível se conectar.', 'Erro de Conexão', wx.ICON_ERROR)

    def adicionaPersonagem(self, evento):
        dialogo_adiciona = wx.Dialog(self, title='Adicionar personagem')
        painel = wx.Panel(dialogo_adiciona)
        
        wx.StaticText(painel, label="Nome do Mud (necessário para criar a pasta):")
        self.campoTextoNomeMud = wx.TextCtrl(painel)
        
        wx.StaticText(painel, label='Nome do personagem:')
        self.campoTextoNome = wx.TextCtrl(painel)
        
        wx.StaticText(painel, label='Senha (deixe em branco para não logar automaticamente):')
        self.campoTextoSenha = wx.TextCtrl(painel, style=wx.TE_PASSWORD)
        
        wx.StaticText(painel, label='Endereço:')
        self.campoTextoEndereco = wx.TextCtrl(painel)
        
        wx.StaticText(painel, label='Porta:')
        self.campoPorta = wx.SpinCtrl(painel, min=1, max=65535, initial=4000)
        
        self.loginAutomatico = wx.CheckBox(painel, label='Logar automaticamente ao conectar')
        
        self.reproduzirForaDaJanela = wx.CheckBox(painel, label="Reproduzir sons fora da janela do MUD")
        self.reproduzirForaDaJanela.SetValue(True)
        
        self.lerForaDaJanela = wx.CheckBox(painel, label='Ler mensagens fora da janela do MUD.')
        self.lerForaDaJanela.SetValue(True)

        self.usarVolumePadrao = wx.CheckBox(painel, label='Usar volume fixo para todos os sons do jogo')
        
        wx.StaticText(painel, label='Volume padrão (1 a 100):')
        self.campoVolumePadrao = wx.SpinCtrl(painel, min=1, max=100, initial=100)

        btnSalvar = wx.Button(painel, wx.ID_OK, label='&Salvar')
        btnSalvar.Bind(wx.EVT_BUTTON, lambda evt: self.salvaConfiguracoes(evt, dialogo_adiciona, None))
        
        btnCancelar = wx.Button(painel, wx.ID_CANCEL, label='&Cancelar')
        
        dialogo_adiciona.ShowModal()
        dialogo_adiciona.Destroy()

    def editaPersonagem(self, evento):
        if self.listBox.GetSelection() == wx.NOT_FOUND: return
        nome_personagem = self.listaDePersonagens[self.listBox.GetSelection()]
        json_data = self.app.personagem.carregaPersonagem(nome_personagem)
        
        if json_data is None:
            wx.MessageBox(f"Não foi possível carregar o personagem '{nome_personagem}'.", "Erro", wx.ICON_ERROR)
            return
            
        dialogo_edita = wx.Dialog(self, title='Editar personagem')
        painel = wx.Panel(dialogo_edita)
        
        caminho_completo = Path(self.app.config.config['gerais']['pastas-dos-muds'][nome_personagem])
        nome_mud = caminho_completo.parent.name
        
        wx.StaticText(painel, label='Nome do MUD:')
        self.campoTextoNomeMud = wx.TextCtrl(painel, value=str(nome_mud))
        self.campoTextoNomeMud.Enable(False)
        
        wx.StaticText(painel, label='Nome do personagem:')
        self.campoTextoNome = wx.TextCtrl(painel, value=nome_personagem)
        
        wx.StaticText(painel, label='Senha:')
        self.campoTextoSenha = wx.TextCtrl(painel, value=json_data.get('senha') or '', style=wx.TE_PASSWORD)
        
        wx.StaticText(painel, label='Endereço:')
        self.campoTextoEndereco = wx.TextCtrl(painel, value=json_data.get('endereço', ''))
        
        wx.StaticText(painel, label='Porta:')
        self.campoPorta = wx.SpinCtrl(painel, min=1, max=65535, initial=int(json_data.get('porta', 4000)))
        
        self.loginAutomatico = wx.CheckBox(painel, label='Logar automaticamente:')
        self.loginAutomatico.SetValue(json_data.get('login_automático', False))
        
        self.reproduzirForaDaJanela = wx.CheckBox(painel, label="Reproduzir sons fora da janela do MUD")
        self.reproduzirForaDaJanela.SetValue(json_data.get('reproduzir_sons_fora_janela', True))
        
        self.lerForaDaJanela = wx.CheckBox(painel, label='Ler mensagens fora da janela do MUD.')
        self.lerForaDaJanela.SetValue(json_data.get('ler_fora_janela', True))

        self.usarVolumePadrao = wx.CheckBox(painel, label='Usar volume fixo para todos os sons do jogo')
        self.usarVolumePadrao.SetValue(json_data.get('usar_volume_padrao', False))
        
        wx.StaticText(painel, label='Volume padrão (1 a 100):')
        self.campoVolumePadrao = wx.SpinCtrl(painel, min=1, max=100, initial=int(json_data.get('volume_padrao', 100)))
        
        btnSalvar = wx.Button(painel, label='&Salvar')
        btnSalvar.Bind(wx.EVT_BUTTON, lambda evt: self.salvaConfiguracoes(evt, dialogo_edita, nome_personagem))
        
        btnCancelar = wx.Button(painel, wx.ID_CANCEL, label='&Cancelar')
        btnCancelar.Bind(wx.EVT_BUTTON, lambda evt: dialogo_edita.EndModal(wx.ID_CANCEL))
        
        dialogo_edita.ShowModal()
        dialogo_edita.Destroy()

    def salvaConfiguracoes(self, evento, dialogo_pai, nome_antigo=None):
        nome_mud = self.campoTextoNomeMud.GetValue().strip()
        nome = self.campoTextoNome.GetValue().strip()
        
        if not nome_mud:
            wx.MessageBox('Erro', 'Por favor, preencha o nome do \nMUD.', wx.ICON_ERROR)
            self.campoTextoNomeMud.SetFocus()
            return
        if not nome:
            wx.MessageBox('Erro', 'Por favor coloque o nome do personagem.', wx.ICON_ERROR)
            self.campoTextoNome.SetFocus()
            return
        
        endereco_limpo = self.campoTextoEndereco.GetValue().strip()
        if not endereco_limpo:
            wx.MessageBox('Erro', 'Por favor, preencha o campo do endereço.', wx.ICON_ERROR)
            self.campoTextoEndereco.SetFocus()
            return
        if not self.campoPorta.GetValue():
            wx.MessageBox('Erro', 'Por favor, escolha uma porta.', wx.ICON_ERROR)
            self.campoPorta.SetFocus()
            return
            
        if nome_antigo:
            if nome_antigo != nome and nome in self.listaDePersonagens:
                wx.MessageBox('Erro', 'Um personagem com este nome já existe.', wx.ICON_ERROR)
                self.campoTextoNome.SetFocus()
                return
        else:
            if nome in self.listaDePersonagens:
                wx.MessageBox('Erro', 'Um personagem com este nome já existe.', wx.ICON_ERROR)
                self.campoTextoNome.SetFocus()
                return
            
        pasta_base_muds = Path(self.app.config.config['gerais']['diretorio-de-dados']) / "clientmud" / "muds"
        pasta_do_mud = pasta_base_muds / nome_mud
        pasta_do_personagem = pasta_do_mud / nome
        
        dic_antigo = self.app.personagem.carregaPersonagem(nome_antigo or nome) or {} if not self.campoTextoNomeMud.IsEnabled() else {}
        if not self.campoTextoSenha.GetValue() and self.loginAutomatico.GetValue(): 
            self.loginAutomatico.SetValue(False)
            
        novo_dic = {
            **dic_antigo,
            'nome': nome,
            'senha': self.campoTextoSenha.GetValue(),
            'endereço': endereco_limpo,
            'porta': int(self.campoPorta.GetValue()),
            'login_automático': self.loginAutomatico.GetValue(),
            'reproduzir_sons_fora_janela': self.reproduzirForaDaJanela.GetValue(),
            'ler_fora_janela': self.lerForaDaJanela.GetValue(),
            'usar_volume_padrao': self.usarVolumePadrao.GetValue(),
            'volume_padrao': self.campoVolumePadrao.GetValue()
        }
        
        if nome_antigo:
            if nome_antigo != nome:
                if not self.app.personagem.renomeiaPersonagem(nome_antigo, nome):
                    wx.MessageBox('Erro ao renomear a pasta do personagem. Verifique se o arquivo está em uso.', 'Erro', wx.ICON_ERROR)
                    return
            confirmacao = self.app.personagem.atualizaPersonagem(nome, novo_dic)
        else:
            confirmacao = self.app.personagem.criaPersonagem(
                pasta=str(pasta_do_personagem),
                pastaSons=str(pasta_do_mud / 'sons'),
                **novo_dic
            )
            if confirmacao:
                self.app.personagem.atualizaPersonagem(nome, novo_dic)
            
        if confirmacao:
            self.app.config.atualizaJson()
            self.listaDePersonagens = self.app.config.config['personagens']
            self.listBox.Set(self.listaDePersonagens)
            self.mostraComponentes()
            
            try:
                idx = self.listaDePersonagens.index(nome)
                self.listBox.SetSelection(idx)
            except ValueError:
                self.listBox.SetSelection(len(self.listaDePersonagens)-1)
                
            self.listBox.SetFocus()
            dialogo_pai.EndModal(wx.ID_OK)
        else:
            wx.MessageBox('Ocorreu um erro ao salvar as configurações. Verifique as permissões de escrita.', 'Erro', wx.ICON_ERROR)

    def removePersonagem(self, evento):
        index = self.listBox.GetSelection()
        if index == wx.NOT_FOUND: return
        nome = self.listaDePersonagens[index]
        dialogoPergunta = wx.MessageDialog(self, f'Deseja realmente remover o personagem "{nome}"?\nTodos os dados serão apagados.', 'Deletar personagem', wx.OK | wx.CANCEL | wx.ICON_QUESTION)
        
        if dialogoPergunta.ShowModal() == wx.ID_OK:
            self.app.personagem.removePersonagem(nome)
            self.listBox.Set(self.listaDePersonagens)
            self.mostraComponentes()
            if self.listaDePersonagens:
                index_atualizado = min(index, len(self.listaDePersonagens) - 1)
                self.listBox.SetSelection(index_atualizado)
                self.listBox.SetFocus()
        dialogoPergunta.Destroy()

    def conexaomanual(self, evento):
        dialogo = DialogoConexaoManual(self)
        if dialogo.ShowModal() == wx.ID_OK:
            endereco = dialogo.endereco.GetValue().strip()
            porta = dialogo.porta.GetValue()
            dialogo.Destroy()
            
            pasta_geral = Path(self.app.config.config['gerais']['diretorio-de-dados']) / 'clientmud'
            pasta_logs = pasta_geral / 'logs'
            pasta_sons = pasta_geral / 'sons'
            pasta_scripts = pasta_geral / 'scripts'
            
            pasta_logs.mkdir(parents=True, exist_ok=True)
            pasta_sons.mkdir(parents=True, exist_ok=True)
            pasta_scripts.mkdir(parents=True, exist_ok=True)
            
            self.app.client.definePastaLog(str(pasta_logs))
            self.app.msp.definePastaSons(pasta_sons)
            
            dialogo_conexao = DialogoConectando(self, (endereco, porta))
            resultado = dialogo_conexao.ShowModal()
            if resultado == wx.ID_OK:
                self.dados_conexao = dialogo_conexao.dados_conexao
                dialogo_conexao.Destroy()
                self.EndModal(wx.ID_OK)
            else:
                dialogo_conexao.Destroy()
                wx.MessageBox('Não foi possível se conectar.', 'Erro de Conexão', wx.ICON_ERROR)

    def encerraAplicativo(self, evento):
        self.EndModal(wx.ID_CANCEL)