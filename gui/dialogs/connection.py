import os
import wx
import wx.lib.newevent
import subprocess
from pathlib import Path
from threading import Thread
import sys
from core.backup import GerenciadorBackup
from models.config import chave_personagem, nome_de_chave, display_de_chave
from gui.theme import aplica_tema_se_ativo

EventoResultadoConexao, EVT_RESULTADO_CONEXAO = wx.lib.newevent.NewEvent()

class ThreadIniciaConexao(Thread):
    def __init__(self, janela_pai, args_conexao, app_context, json_personagem=None):
        super().__init__(daemon=True)
        self.janela_pai = janela_pai
        self.args_conexao = args_conexao
        self.json_personagem = json_personagem
        self.app = app_context

    def run(self):
        if len(self.args_conexao) == 3:
            endereco, porta, usar_ssl = self.args_conexao
        else:
            endereco, porta = self.args_conexao
            usar_ssl = False
        tentativa_conexao = self.app.client.conectaServidor(endereco, porta, usar_ssl)
        evt = EventoResultadoConexao(
            tentativa_conexao=tentativa_conexao,
            json_personagem=self.json_personagem,
            endereco=endereco,
            porta=porta,
            usar_ssl=usar_ssl
        )
        try:
            wx.PostEvent(self.janela_pai, evt)
        except RuntimeError:
            pass

class DialogoConectando(wx.Dialog):
    def __init__(self, pai, args, json=None):
        super().__init__(parent=pai, title='Conectando')
        self.app = wx.GetApp()
        self.Bind(EVT_RESULTADO_CONEXAO, self.retornaConexao)
        self.Bind(wx.EVT_CLOSE, self.cancelaConexao)
        self.Bind(wx.EVT_CHAR_HOOK, self.teclaPressionada)
        self.dados_conexao = None
        painel = wx.Panel(self)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.spinner = wx.ActivityIndicator(painel)
        self.spinner.Start()
        sizer.Add(self.spinner, 0, wx.ALL | wx.CENTER, 10)
        
        txt = wx.StaticText(painel, label=f"Tentando conectar em: {args[0]}\nPor favor, aguarde...")
        sizer.Add(txt, 0, wx.ALL | wx.CENTER, 10)
        
        btnCancelar = wx.Button(painel, wx.ID_ANY, label='Cancelar')
        btnCancelar.Bind(wx.EVT_BUTTON, self.cancelaConexao)
        sizer.Add(btnCancelar, 0, wx.ALL | wx.CENTER, 10)
        
        painel.SetSizer(sizer)
        sizer.Fit(self)
        
        thread_conexao = ThreadIniciaConexao(self, args, self.app, json)
        thread_conexao.start()

        aplica_tema_se_ativo(self)
        btnCancelar.SetFocus()

    def teclaPressionada(self, evento):
        if evento.GetKeyCode() == wx.WXK_ESCAPE:
            self.cancelaConexao(None)
        else:
            evento.Skip()

    def cancelaConexao(self, evento):
        self.EndModal(wx.ID_ABORT)
        Thread(target=self.app.client.terminaCliente, daemon=True).start()

    def retornaConexao(self, evento):
        if evento.tentativa_conexao:
            self.dados_conexao = {
                'json_personagem': evento.json_personagem,
                'endereco': evento.endereco,
                'porta': evento.porta,
                'ssl': evento.usar_ssl
            }
            self.EndModal(wx.ID_OK)
        else:
            self.EndModal(wx.ID_CANCEL)

class DialogoConexaoManual(wx.Dialog):
    def __init__(self, pai=None):
        super().__init__(parent=pai, title="Conexão")
        self.app = wx.GetApp()
        painel = wx.Panel(self)
        self.Bind(wx.EVT_CHAR_HOOK, self.teclaPressionada)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        t_endereco = wx.StaticText(painel, label="&Endereço:")
        sizer.Add(t_endereco, 0, wx.ALL, 5)
        self.endereco = wx.TextCtrl(painel)
        sizer.Add(self.endereco, 0, wx.EXPAND | wx.ALL, 5)
        
        t_porta = wx.StaticText(painel, label="&Porta:")
        sizer.Add(t_porta, 0, wx.ALL, 5)
        self.porta = wx.SpinCtrl(painel, min=1, max=65535)
        sizer.Add(self.porta, 0, wx.EXPAND | wx.ALL, 5)

        self.conexaoSegura = wx.CheckBox(painel, label="Usar conexão &segura (SSL/TLS)")
        self.conexaoSegura.Bind(wx.EVT_CHECKBOX, self.anuncia_checkbox)
        sizer.Add(self.conexaoSegura, 0, wx.ALL, 5)

        self.modoEscuro = wx.CheckBox(painel, label="&Usar modo escuro")
        self.modoEscuro.SetValue(True)
        self.modoEscuro.Bind(wx.EVT_CHECKBOX, self.anuncia_checkbox)
        sizer.Add(self.modoEscuro, 0, wx.ALL, 5)

        ultima = self.app.config.config['gerais'].get('ultima-conexao')
        if ultima:
            self.endereco.SetValue(ultima[0])
            self.porta.SetValue(ultima[1])
            if len(ultima) > 2:
                self.conexaoSegura.SetValue(bool(ultima[2]))
            if len(ultima) > 3:
                self.modoEscuro.SetValue(bool(ultima[3]))

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btnConecta = wx.Button(painel, wx.ID_OK, label="C&onectar")
        btnConecta.Bind(wx.EVT_BUTTON, self.confirma)
        btn_sizer.Add(btnConecta, 0, wx.ALL, 5)
        
        btnCancela = wx.Button(painel, wx.ID_CANCEL, label="&Cancelar")
        btnCancela.Bind(wx.EVT_BUTTON, self.cancela)
        btn_sizer.Add(btnCancela, 0, wx.ALL, 5)
        
        sizer.Add(btn_sizer, 0, wx.CENTER)
        
        painel.SetSizer(sizer)
        sizer.Fit(self)
        self.Center()

        aplica_tema_se_ativo(self)

    def anuncia_checkbox(self, evento):
        cb = evento.GetEventObject()
        estado = "marcado" if cb.GetValue() else "desmarcado"
        self.app.fale(estado)
        evento.Skip()

    def teclaPressionada(self, evento):
        if evento.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
        elif evento.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.confirma(None)
        else:
            evento.Skip()

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
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        txt = wx.StaticText(painel, label="Nenhum personagem foi encontrado.\nO que você deseja fazer para começar?")
        sizer.Add(txt, 0, wx.ALL | wx.CENTER, 10)
        
        self.btn_criar = wx.Button(painel, label="Criar Novo Personagem")
        sizer.Add(self.btn_criar, 0, wx.EXPAND | wx.ALL, 5)
        self.btn_importar = wx.Button(painel, label="Restaurar Backup")
        sizer.Add(self.btn_importar, 0, wx.EXPAND | wx.ALL, 5)
        
        self.btn_criar.Bind(wx.EVT_BUTTON, self.ao_criar)
        self.btn_importar.Bind(wx.EVT_BUTTON, self.ao_importar)
        self.Bind(wx.EVT_CHAR_HOOK, self.tecla_pressionada)
        self.Bind(wx.EVT_CLOSE, self.ao_fechar)
        
        painel.SetSizer(sizer)
        sizer.Fit(self)
        self.Center()
        
        self.acao_escolhida = None
        aplica_tema_se_ativo(self)
        self.btn_importar.SetFocus()

    def tecla_pressionada(self, evento):
        if evento.GetKeyCode() == wx.WXK_ESCAPE:
            self.acao_escolhida = "ignorar"
            self.EndModal(wx.ID_CANCEL)
        else:
            evento.Skip()

    def ao_fechar(self, evento):
        self.acao_escolhida = "ignorar"
        self.EndModal(wx.ID_CANCEL)

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
                except Exception:
                    pass
                wx.MessageBox("Backup restaurado com sucesso! O aplicativo será reiniciado automaticamente.", "Sucesso", wx.ICON_INFORMATION)
                self.acao_escolhida = "importado"
                self.EndModal(wx.ID_OK)
                
                rodando_pelo_python = sys.argv[0].lower().endswith('.py') or sys.argv[0].lower().endswith('.pyw')
                
                if rodando_pelo_python:
                    caminho_script = os.path.abspath(sys.argv[0])
                    comando = [sys.executable, caminho_script] + sys.argv[1:]
                    pasta_trabalho = os.path.dirname(caminho_script) or os.getcwd()
                else:
                    pasta_trabalho = os.getcwd()
                    caminho_exe = os.path.join(pasta_trabalho, "clientmud.exe")
                    comando = [caminho_exe] + sys.argv[1:]
                    
                subprocess.Popen(
                    comando, 
                    cwd=pasta_trabalho,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                sys.exit(0)
            else:
                try:
                    wx.GetApp().fale("Erro ao restaurar backup.")
                except Exception:
                    pass
                wx.MessageBox(mensagem, "Erro", wx.ICON_ERROR)

class DialogoEntrada(wx.Dialog):
    def __init__(self, pai):
        super().__init__(parent=pai, title="Conexões")
        self.app = wx.GetApp()
        painel = wx.Panel(self)
        self.Bind(wx.EVT_CHAR_HOOK, self.teclaPressionada)
        self.Bind(wx.EVT_CLOSE, self.encerraAplicativo)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.conectado = False
        self.dados_conexao = None
        self.dialogo_conexao = None
        self.personagem_conectado = None
        
        self.listaDePersonagens = self.app.config.config['personagens'] if self.app.config.config else []
        self.listBox = wx.ListBox(painel, choices=[display_de_chave(k) for k in self.listaDePersonagens])
        sizer.Add(self.listBox, 1, wx.EXPAND | wx.ALL, 5)
        
        if len(self.listaDePersonagens) > 0:
            self.listBox.SetSelection(0)
            
        self.btnConecta = wx.Button(painel, label="Conectar")
        self.btnConecta.Bind(wx.EVT_BUTTON, self.conecta)
        sizer.Add(self.btnConecta, 0, wx.EXPAND | wx.ALL, 5)
        
        btnAdicionaPersonagem = wx.Button(painel, label="Adicionar personagem\tCtrl+A")
        btnAdicionaPersonagem.Bind(wx.EVT_BUTTON, self.adicionaPersonagem)
        sizer.Add(btnAdicionaPersonagem, 0, wx.EXPAND | wx.ALL, 5)
        
        self.btnEditaPersonagem = wx.Button(painel, label="Editar personagem\tCtrl+E")
        self.btnEditaPersonagem.Bind(wx.EVT_BUTTON, self.editaPersonagem)
        sizer.Add(self.btnEditaPersonagem, 0, wx.EXPAND | wx.ALL, 5)
        
        self.btnRemovePersonagem = wx.Button(painel, label="Remover personagem\tDel")
        self.btnRemovePersonagem.Bind(wx.EVT_BUTTON, self.removePersonagem)
        sizer.Add(self.btnRemovePersonagem, 0, wx.EXPAND | wx.ALL, 5)
        
        btnConexaomanual = wx.Button(painel, label="Conexão manual\tCtrl+M")
        btnConexaomanual.Bind(wx.EVT_BUTTON, self.conexaomanual)
        sizer.Add(btnConexaomanual, 0, wx.EXPAND | wx.ALL, 5)
        
        btnSaida = wx.Button(painel, wx.ID_CANCEL, label='Sair\tCtrl+Q')
        btnSaida.Bind(wx.EVT_BUTTON, self.encerraAplicativo)
        sizer.Add(btnSaida, 0, wx.EXPAND | wx.ALL, 5)
        
        painel.SetSizer(sizer)
        self.SetSize((400, 450))
        self.Center()
        
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
        aplica_tema_se_ativo(self)

        if not self.listaDePersonagens:
            wx.CallAfter(self.verificaPrimeiroAcesso)

    def anuncia_checkbox(self, evento):
        cb = evento.GetEventObject()
        estado = "marcado" if cb.GetValue() else "desmarcado"
        self.app.fale(estado)
        evento.Skip()

    def verificaPrimeiroAcesso(self):
        ignorar = self.app.config.config['gerais'].get('ignorar_boas_vindas', False)
        if ignorar:
            return

        dlg = DialogoPrimeiroAcesso(self)
        dlg.ShowModal()
        acao = dlg.acao_escolhida
        dlg.Destroy()
        
        if acao == "importado":
            sys.exit(0)
        elif acao == "criar":
            self.adicionaPersonagem(None)
        elif acao == "ignorar":
            self.app.config.config['gerais']['ignorar_boas_vindas'] = True
            self.app.config.atualizaJson()

    def mostraComponentes(self):
        condicao = bool(self.listaDePersonagens)
        self.listBox.Show(condicao)
        self.btnConecta.Show(condicao)
        self.btnEditaPersonagem.Show(condicao)
        self.btnRemovePersonagem.Show(condicao)

    def teclaPressionada(self, evento):
        if evento.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and self.listBox.HasFocus():
            self.conecta(evento=None)
        else:
            evento.Skip()

    def conecta(self, evento):
        if self.listBox.GetSelection() == wx.NOT_FOUND: return
        chave = self.listaDePersonagens[self.listBox.GetSelection()]
        nome_personagem = nome_de_chave(chave)
        json_data = self.app.personagem.carregaPersonagem(chave)

        if json_data is None:
            wx.MessageBox(f"Não foi possível carregar o personagem '{display_de_chave(chave)}'.\nO arquivo de configuração pode estar ausente ou corrompido.", "Erro", wx.ICON_ERROR)
            self.listaDePersonagens.remove(chave)
            self.listBox.Set([display_de_chave(k) for k in self.listaDePersonagens])
            self.app.config.removePersonagem(chave)
            return

        json_data['_chave'] = chave
        pasta_base_personagem = Path(self.app.config.config['gerais']['pastas-dos-muds'][chave])

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
        ssl_limpo = bool(json_data.get('conexao_segura', False))

        self.app.modo_escuro = json_data.get('modo_escuro', True)

        args = (endereco_limpo, porta_limpa, ssl_limpo)
        dialogo_conexao = DialogoConectando(self, args, json_data)
        resultado = dialogo_conexao.ShowModal()
        
        if resultado == wx.ID_OK:
            self.dados_conexao = dialogo_conexao.dados_conexao
            dialogo_conexao.Destroy()
            self.app.iniciaJanelaMud(self.dados_conexao)
            self.EndModal(wx.ID_OK)
        elif resultado == wx.ID_CANCEL:
            dialogo_conexao.Destroy()
            wx.MessageBox('Não foi possível se conectar.', 'Erro de Conexão', wx.ICON_ERROR)
        else:
            dialogo_conexao.Destroy()

    def adicionaPersonagem(self, evento):
        dialogo_adiciona = wx.Dialog(self, title='Adicionar personagem')
        painel = wx.Panel(dialogo_adiciona)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        t1 = wx.StaticText(painel, label="Nome do Mud (necessário para criar a pasta):")
        sizer.Add(t1, 0, wx.ALL, 5)
        self.campoTextoNomeMud = wx.TextCtrl(painel)
        sizer.Add(self.campoTextoNomeMud, 0, wx.EXPAND | wx.ALL, 5)
        
        t2 = wx.StaticText(painel, label='Nome do personagem:')
        sizer.Add(t2, 0, wx.ALL, 5)
        self.campoTextoNome = wx.TextCtrl(painel)
        sizer.Add(self.campoTextoNome, 0, wx.EXPAND | wx.ALL, 5)
        
        t3 = wx.StaticText(painel, label='Senha (deixe em branco para não logar automaticamente):')
        sizer.Add(t3, 0, wx.ALL, 5)
        self.campoTextoSenha = wx.TextCtrl(painel, style=wx.TE_PASSWORD)
        sizer.Add(self.campoTextoSenha, 0, wx.EXPAND | wx.ALL, 5)
        
        t4 = wx.StaticText(painel, label='Endereço:')
        sizer.Add(t4, 0, wx.ALL, 5)
        self.campoTextoEndereco = wx.TextCtrl(painel)
        sizer.Add(self.campoTextoEndereco, 0, wx.EXPAND | wx.ALL, 5)
        
        t5 = wx.StaticText(painel, label='Porta:')
        sizer.Add(t5, 0, wx.ALL, 5)
        self.campoPorta = wx.SpinCtrl(painel, min=1, max=65535, initial=4000)
        sizer.Add(self.campoPorta, 0, wx.EXPAND | wx.ALL, 5)

        self.conexaoSegura = wx.CheckBox(painel, label='Usar conexão segura (SSL/TLS)')
        self.conexaoSegura.Bind(wx.EVT_CHECKBOX, self.anuncia_checkbox)
        sizer.Add(self.conexaoSegura, 0, wx.ALL, 5)

        self.loginAutomatico = wx.CheckBox(painel, label='Logar automaticamente ao conectar')
        self.loginAutomatico.Bind(wx.EVT_CHECKBOX, self.anuncia_checkbox)
        sizer.Add(self.loginAutomatico, 0, wx.ALL, 5)
        
        self.reproduzirForaDaJanela = wx.CheckBox(painel, label="Reproduzir sons fora da janela do MUD")
        self.reproduzirForaDaJanela.SetValue(True)
        self.reproduzirForaDaJanela.Bind(wx.EVT_CHECKBOX, self.anuncia_checkbox)
        sizer.Add(self.reproduzirForaDaJanela, 0, wx.ALL, 5)
        
        self.lerForaDaJanela = wx.CheckBox(painel, label='Ler mensagens fora da janela do MUD.')
        self.lerForaDaJanela.SetValue(True)
        self.lerForaDaJanela.Bind(wx.EVT_CHECKBOX, self.anuncia_checkbox)
        sizer.Add(self.lerForaDaJanela, 0, wx.ALL, 5)

        self.usarVolumePadrao = wx.CheckBox(painel, label='Usar volume fixo para todos os sons do jogo')
        self.usarVolumePadrao.Bind(wx.EVT_CHECKBOX, self.anuncia_checkbox)
        sizer.Add(self.usarVolumePadrao, 0, wx.ALL, 5)

        t6 = wx.StaticText(painel, label='Volume padrão (1 a 100):')
        sizer.Add(t6, 0, wx.ALL, 5)
        self.campoVolumePadrao = wx.SpinCtrl(painel, min=1, max=100, initial=100)
        sizer.Add(self.campoVolumePadrao, 0, wx.EXPAND | wx.ALL, 5)

        self.modoEscuro = wx.CheckBox(painel, label='Usar modo escuro')
        self.modoEscuro.SetValue(True)
        self.modoEscuro.Bind(wx.EVT_CHECKBOX, self.anuncia_checkbox)
        sizer.Add(self.modoEscuro, 0, wx.ALL, 5)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btnSalvar = wx.Button(painel, wx.ID_OK, label='&Salvar')
        btnSalvar.Bind(wx.EVT_BUTTON, lambda evt: self.salvaConfiguracoes(evt, dialogo_adiciona, None))
        btn_sizer.Add(btnSalvar, 0, wx.ALL, 5)
        
        btnCancelar = wx.Button(painel, wx.ID_CANCEL, label='&Cancelar')
        btn_sizer.Add(btnCancelar, 0, wx.ALL, 5)
        
        sizer.Add(btn_sizer, 0, wx.CENTER)
        
        painel.SetSizer(sizer)
        sizer.Fit(dialogo_adiciona)
        dialogo_adiciona.Center()

        aplica_tema_se_ativo(dialogo_adiciona)
        dialogo_adiciona.ShowModal()
        dialogo_adiciona.Destroy()

    def editaPersonagem(self, evento):
        if self.listBox.GetSelection() == wx.NOT_FOUND: return
        chave = self.listaDePersonagens[self.listBox.GetSelection()]
        nome_personagem = nome_de_chave(chave)
        json_data = self.app.personagem.carregaPersonagem(chave)

        if json_data is None:
            wx.MessageBox(f"Não foi possível carregar o personagem '{display_de_chave(chave)}'.", "Erro", wx.ICON_ERROR)
            return

        dialogo_edita = wx.Dialog(self, title='Editar personagem')
        painel = wx.Panel(dialogo_edita)
        sizer = wx.BoxSizer(wx.VERTICAL)

        caminho_completo = Path(self.app.config.config['gerais']['pastas-dos-muds'][chave])
        nome_mud = caminho_completo.parent.name

        t1 = wx.StaticText(painel, label='Nome do MUD:')
        sizer.Add(t1, 0, wx.ALL, 5)
        self.campoTextoNomeMud = wx.TextCtrl(painel, value=str(nome_mud))
        self.campoTextoNomeMud.Enable(False)
        sizer.Add(self.campoTextoNomeMud, 0, wx.EXPAND | wx.ALL, 5)

        t2 = wx.StaticText(painel, label='Nome do personagem:')
        sizer.Add(t2, 0, wx.ALL, 5)
        self.campoTextoNome = wx.TextCtrl(painel, value=nome_personagem)
        sizer.Add(self.campoTextoNome, 0, wx.EXPAND | wx.ALL, 5)

        t3 = wx.StaticText(painel, label='Senha:')
        sizer.Add(t3, 0, wx.ALL, 5)
        self.campoTextoSenha = wx.TextCtrl(painel, value=json_data.get('senha') or '', style=wx.TE_PASSWORD)
        sizer.Add(self.campoTextoSenha, 0, wx.EXPAND | wx.ALL, 5)

        t4 = wx.StaticText(painel, label='Endereço:')
        sizer.Add(t4, 0, wx.ALL, 5)
        self.campoTextoEndereco = wx.TextCtrl(painel, value=json_data.get('endereço', ''))
        sizer.Add(self.campoTextoEndereco, 0, wx.EXPAND | wx.ALL, 5)

        t5 = wx.StaticText(painel, label='Porta:')
        sizer.Add(t5, 0, wx.ALL, 5)
        self.campoPorta = wx.SpinCtrl(painel, min=1, max=65535, initial=int(json_data.get('porta', 4000)))
        sizer.Add(self.campoPorta, 0, wx.EXPAND | wx.ALL, 5)

        self.conexaoSegura = wx.CheckBox(painel, label='Usar conexão segura (SSL/TLS)')
        self.conexaoSegura.SetValue(json_data.get('conexao_segura', False))
        self.conexaoSegura.Bind(wx.EVT_CHECKBOX, self.anuncia_checkbox)
        sizer.Add(self.conexaoSegura, 0, wx.ALL, 5)

        self.loginAutomatico = wx.CheckBox(painel, label='Logar automaticamente:')
        self.loginAutomatico.SetValue(json_data.get('login_automático', False))
        self.loginAutomatico.Bind(wx.EVT_CHECKBOX, self.anuncia_checkbox)
        sizer.Add(self.loginAutomatico, 0, wx.ALL, 5)

        self.reproduzirForaDaJanela = wx.CheckBox(painel, label="Reproduzir sons fora da janela do MUD")
        self.reproduzirForaDaJanela.SetValue(json_data.get('reproduzir_sons_fora_janela', True))
        self.reproduzirForaDaJanela.Bind(wx.EVT_CHECKBOX, self.anuncia_checkbox)
        sizer.Add(self.reproduzirForaDaJanela, 0, wx.ALL, 5)

        self.lerForaDaJanela = wx.CheckBox(painel, label='Ler mensagens fora da janela do MUD.')
        self.lerForaDaJanela.SetValue(json_data.get('ler_fora_janela', True))
        self.lerForaDaJanela.Bind(wx.EVT_CHECKBOX, self.anuncia_checkbox)
        sizer.Add(self.lerForaDaJanela, 0, wx.ALL, 5)

        self.usarVolumePadrao = wx.CheckBox(painel, label='Usar volume fixo para todos os sons do jogo')
        self.usarVolumePadrao.SetValue(json_data.get('usar_volume_padrao', False))
        self.usarVolumePadrao.Bind(wx.EVT_CHECKBOX, self.anuncia_checkbox)
        sizer.Add(self.usarVolumePadrao, 0, wx.ALL, 5)

        t6 = wx.StaticText(painel, label='Volume padrão (1 a 100):')
        sizer.Add(t6, 0, wx.ALL, 5)
        self.campoVolumePadrao = wx.SpinCtrl(painel, min=1, max=100, initial=int(json_data.get('volume_padrao', 100)))
        sizer.Add(self.campoVolumePadrao, 0, wx.EXPAND | wx.ALL, 5)

        self.modoEscuro = wx.CheckBox(painel, label='Usar modo escuro')
        self.modoEscuro.SetValue(json_data.get('modo_escuro', True))
        self.modoEscuro.Bind(wx.EVT_CHECKBOX, self.anuncia_checkbox)
        sizer.Add(self.modoEscuro, 0, wx.ALL, 5)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btnSalvar = wx.Button(painel, label='&Salvar')
        btnSalvar.Bind(wx.EVT_BUTTON, lambda evt, c=chave: self.salvaConfiguracoes(evt, dialogo_edita, c))
        btn_sizer.Add(btnSalvar, 0, wx.ALL, 5)

        btnCancelar = wx.Button(painel, wx.ID_CANCEL, label='&Cancelar')
        btnCancelar.Bind(wx.EVT_BUTTON, lambda evt: dialogo_edita.EndModal(wx.ID_CANCEL))
        btn_sizer.Add(btnCancelar, 0, wx.ALL, 5)
        
        sizer.Add(btn_sizer, 0, wx.CENTER)
        
        painel.SetSizer(sizer)
        sizer.Fit(dialogo_edita)
        dialogo_edita.Center()

        aplica_tema_se_ativo(dialogo_edita)
        dialogo_edita.ShowModal()
        dialogo_edita.Destroy()

    def salvaConfiguracoes(self, evento, dialogo_pai, chave_antigo=None):
        nome_mud = self.campoTextoNomeMud.GetValue().strip()
        nome = self.campoTextoNome.GetValue().strip()

        if not nome_mud:
            wx.MessageBox('Por favor, preencha o nome do MUD.', 'Erro', wx.ICON_ERROR)
            self.campoTextoNomeMud.SetFocus()
            return
        if not nome:
            wx.MessageBox('Por favor coloque o nome do personagem.', 'Erro', wx.ICON_ERROR)
            self.campoTextoNome.SetFocus()
            return

        endereco_limpo = self.campoTextoEndereco.GetValue().strip()
        if not endereco_limpo:
            wx.MessageBox('Por favor, preencha o campo do endereço.', 'Erro', wx.ICON_ERROR)
            self.campoTextoEndereco.SetFocus()
            return
        if not self.campoPorta.GetValue():
            wx.MessageBox('Por favor, escolha uma porta.', 'Erro', wx.ICON_ERROR)
            self.campoPorta.SetFocus()
            return

        chave_nova = chave_personagem(nome, nome_mud)

        if chave_antigo:
            if chave_antigo != chave_nova and chave_nova in self.listaDePersonagens:
                wx.MessageBox('Um personagem com este nome já existe neste MUD.', 'Erro', wx.ICON_ERROR)
                self.campoTextoNome.SetFocus()
                return
        else:
            if chave_nova in self.listaDePersonagens:
                wx.MessageBox('Um personagem com este nome já existe neste MUD.', 'Erro', wx.ICON_ERROR)
                self.campoTextoNome.SetFocus()
                return

        pasta_base_muds = Path(self.app.config.config['gerais']['diretorio-de-dados']) / "clientmud" / "muds"
        pasta_do_mud = pasta_base_muds / nome_mud
        pasta_do_personagem = pasta_do_mud / nome

        dic_antigo = self.app.personagem.carregaPersonagem(chave_antigo) or {} if chave_antigo else {}
        if not self.campoTextoSenha.GetValue() and self.loginAutomatico.GetValue():
            self.loginAutomatico.SetValue(False)

        novo_dic = {
            **dic_antigo,
            'nome': nome,
            'mud': nome_mud,
            'senha': self.campoTextoSenha.GetValue(),
            'endereço': endereco_limpo,
            'porta': int(self.campoPorta.GetValue()),
            'conexao_segura': self.conexaoSegura.GetValue(),
            'login_automático': self.loginAutomatico.GetValue(),
            'reproduzir_sons_fora_janela': self.reproduzirForaDaJanela.GetValue(),
            'ler_fora_janela': self.lerForaDaJanela.GetValue(),
            'usar_volume_padrao': self.usarVolumePadrao.GetValue(),
            'volume_padrao': self.campoVolumePadrao.GetValue(),
            'modo_escuro': self.modoEscuro.GetValue()
        }

        if chave_antigo:
            if nome_de_chave(chave_antigo) != nome:
                if not self.app.personagem.renomeiaPersonagem(chave_antigo, nome):
                    wx.MessageBox('Erro ao renomear a pasta do personagem. Verifique se o arquivo está em uso.', 'Erro', wx.ICON_ERROR)
                    return
            confirmacao = self.app.personagem.atualizaPersonagem(chave_nova, novo_dic)
        else:
            confirmacao = self.app.personagem.criaPersonagem(
                pasta=str(pasta_do_personagem),
                pastaSons=str(pasta_do_mud / 'sons'),
                **novo_dic
            )
            if confirmacao:
                self.app.personagem.atualizaPersonagem(chave_nova, novo_dic)

        if confirmacao:
            self.app.config.atualizaJson()
            self.listaDePersonagens = self.app.config.config['personagens']
            self.listBox.Set([display_de_chave(k) for k in self.listaDePersonagens])
            self.mostraComponentes()

            try:
                idx = self.listaDePersonagens.index(chave_nova)
                self.listBox.SetSelection(idx)
            except ValueError:
                self.listBox.SetSelection(len(self.listaDePersonagens) - 1)

            self.listBox.SetFocus()
            dialogo_pai.EndModal(wx.ID_OK)
        else:
            wx.MessageBox('Ocorreu um erro ao salvar as configurações. Verifique as permissões de escrita.', 'Erro', wx.ICON_ERROR)

    def removePersonagem(self, evento):
        index = self.listBox.GetSelection()
        if index == wx.NOT_FOUND: return
        chave = self.listaDePersonagens[index]
        nome_display = display_de_chave(chave)
        dialogoPergunta = wx.MessageDialog(self, f'Deseja realmente remover o personagem "{nome_display}"?\nTodos os dados serão apagados.', 'Deletar personagem', wx.OK | wx.CANCEL | wx.ICON_QUESTION)

        if dialogoPergunta.ShowModal() == wx.ID_OK:
            self.app.personagem.removePersonagem(chave)
            self.listBox.Set([display_de_chave(k) for k in self.listaDePersonagens])
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
            usar_ssl = dialogo.conexaoSegura.GetValue()
            modo_escuro = dialogo.modoEscuro.GetValue()
            dialogo.Destroy()
            self.app.modo_escuro = modo_escuro

            pasta_geral = Path(self.app.config.config['gerais']['diretorio-de-dados']) / 'clientmud'
            pasta_logs = pasta_geral / 'logs'
            pasta_sons = pasta_geral / 'sons'
            pasta_scripts = pasta_geral / 'scripts'
            
            pasta_logs.mkdir(parents=True, exist_ok=True)
            pasta_sons.mkdir(parents=True, exist_ok=True)
            pasta_scripts.mkdir(parents=True, exist_ok=True)
            
            self.app.client.definePastaLog(str(pasta_logs))
            self.app.msp.definePastaSons(pasta_sons)
            
            dialogo_conexao = DialogoConectando(self, (endereco, porta, usar_ssl))
            resultado = dialogo_conexao.ShowModal()
            if resultado == wx.ID_OK:
                self.dados_conexao = dialogo_conexao.dados_conexao
                self.dados_conexao['modo_escuro'] = modo_escuro
                dialogo_conexao.Destroy()
                self.app.iniciaJanelaMud(self.dados_conexao)
                self.EndModal(wx.ID_OK)
            elif resultado == wx.ID_CANCEL:
                dialogo_conexao.Destroy()
                wx.MessageBox('Não foi possível se conectar.', 'Erro de Conexão', wx.ICON_ERROR)
            else:
                dialogo_conexao.Destroy()

    def encerraAplicativo(self, evento):
        self.EndModal(wx.ID_CANCEL)