import queue
import os
import subprocess, threading, json
import speech_recognition as sr
import concurrent.futures
from  pathlib import Path
import wx, logging,  re, sys, traceback
import wx.lib.newevent
from threading import Thread
from threading import Event, Lock
from time import sleep, time
from timer import  Timer
from msp import Msp
msp=Msp()

executor = concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count())
from cliente import Cliente
cliente=Cliente()
from accessible_output2 import outputs
saida=outputs.auto.Auto()
fale=saida.speak
from configuracoes import Config, gerenciaPersonagens, gerenciaPastas
config=Config()
pastas = gerenciaPastas(config)
personagem=gerenciaPersonagens(config, pastas)
from trigger import Trigger
from key import Key
from log import gravaErro

def excepthook(exctype, value, tb):
	mensagem = ''.join(traceback.format_exception(exctype, value, tb))
	gravaErro(mensagem)
	wx.MessageBox(f"{mensagem}", "Erro no programa.")
	if cliente: cliente.arquivoLog.close()
	wx.GetApp().ExitMainLoop()
	sys.exit()
	sys.excepthook = excepthook

EventoResultadoConexao, EVT_RESULTADO_CONEXAO = wx.lib.newevent.NewEvent()

class ThreadIniciaConexao(Thread):
	def __init__(self, janela_pai, args_conexao, json_personagem = None, ):
		super().__init__(daemon=True)
		self.janela_pai = janela_pai
		self.args_conexao = args_conexao
		self.json_personagem = json_personagem
	def run(self):
		endereco, porta = self.args_conexao
		tentativa_conexao = cliente.conectaServidor(endereco, porta)
		evt = EventoResultadoConexao(tentativa_conexao = tentativa_conexao, json_personagem = self.json_personagem, endereco = endereco, porta = porta)
		wx.PostEvent(self.janela_pai, evt)

class Aplicacao(wx.App):
	def OnInit(self):
		novo_atualizador = Path('atualizador_novo.exe')
		velho_atualizador = Path('atualizador.exe')
		if novo_atualizador.exists():
			try:
				for _ in range(20): 
					try:
						if velho_atualizador.exists():
							velho_atualizador.unlink()
						break
					except PermissionError:
						sleep(0.1)
				if not velho_atualizador.exists():
					novo_atualizador.rename(velho_atualizador)
			except Exception:
				pass
		if not config.config:
			mensagem_configuracao_inicial = wx.MessageDialog(
				None,
				'Bem-vindo. Para começar, é necessário realizar algumas configurações iniciais.',
				"Primeira Inicialização",
				wx.OK| wx.ICON_INFORMATION)
			mensagem_configuracao_inicial.SetOKLabel("Iniciar Configuração")
			mensagem_configuracao_inicial.ShowModal()
			mensagem_configuracao_inicial.Destroy()
			dialogo_configuracoes = configuracoes()
			dialogo_configuracoes.ShowModal()
			dialogo_configuracoes.Destroy()
			return False
		else:
			if config.config['gerais'].get('verifica-atualizacoes-automaticamente', True):
				caminho_atualizador = Path('atualizador.exe')
				if caminho_atualizador.exists(): subprocess.Popen(caminho_atualizador)
			pastas.criaPastaGeral()
			self.mostraDialogoEntrada()
			return True
	def mostraDialogoEntrada(self):
		janela_inicial= dialogoEntrada(None)
		resultado = janela_inicial.ShowModal()
		if resultado == wx.ID_OK:
			dados = janela_inicial.dados_conexao
			self.iniciaJanelaMud(dados)
		janela_inicial.Destroy()

	def iniciaJanelaMud(self,  dados):
		if dados['json_personagem']:
			frame = janelaMud(dados['json_personagem']['nome'], dados['json_personagem'])
		else:
			config.config['gerais']['ultima-conexao'] = [dados["endereco"], dados["porta"]]
			config.atualizaJson()
			frame = janelaMud(dados['endereco'])
		self.janela_principal = frame
		self.SetTopWindow(frame)
		frame.Raise()
		frame.entrada.SetFocus()

class DialogoConectando(wx.Dialog):
	def __init__(self, pai, args, json = None):
		super().__init__(parent=pai, title= 'Conectando')
		self.Bind(EVT_RESULTADO_CONEXAO, self.retornaConexao)
		self.dados_conexao = None
		painel = wx.Panel(self)
		self.spinner =  wx.ActivityIndicator(painel)
		self.spinner.Start()
		thread_conexao = ThreadIniciaConexao(self, args, json)
		thread_conexao.start()
		texto =wx.StaticText(painel, label=f"Tentando conectar em: {args[0]}\nPor favor, aguarde...")
		self.CenterOnParent()

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

class dialogoEntrada(wx.Dialog):
	def __init__(self, pai):
		wx.Dialog.__init__(self, parent=pai, title="Conexões.")
		painel=wx.Panel(self)
		self.Bind(wx.EVT_CHAR_HOOK, self.teclaPressionada)
		self.Bind(wx.EVT_CLOSE, self.encerraAplicativo)
		self.conectado = False
		self.dados_conexao = None
		self.dialogo_conexao = None
		self.personagem_conectado = None
		self.listaDePersonagens=config.config['personagens'] if config.config else []
		self.listBox=wx.ListBox(painel, choices=self.listaDePersonagens)
		if len(self.listaDePersonagens) >0:
			self.listBox.SetSelection(0)
		self.btnConecta=wx.Button(painel, label="conectar")
		self.btnConecta.Bind(wx.EVT_BUTTON, self.conecta)
		btnAdicionaPersonagem=wx.Button(painel, label="adicionar personagem\tCtrl+A")
		btnAdicionaPersonagem.Bind(wx.EVT_BUTTON, self.adicionaPersonagem)
		self.btnEditaPersonagem=wx.Button(painel, label="editar personagem\tCtrl+E")
		self.btnEditaPersonagem.Bind(wx.EVT_BUTTON, self.editaPersonagem)
		self.btnRemovePersonagem=wx.Button(painel, label="remover personagem\tDel)")
		self.btnRemovePersonagem.Bind(wx.EVT_BUTTON, self.removePersonagem)
		btnConexaomanual=wx.Button(painel, label="conexão manual\tCtrl+M")
		btnConexaomanual.Bind(wx.EVT_BUTTON, self.conexaomanual)
		btnSaida=wx.Button(painel, wx.ID_CANCEL, label='sair\tCtrl+Q')
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
	def mostraComponentes(self):
		condicao=bool(self.listaDePersonagens)
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
		json=personagem.carregaPersonagem(nome_personagem)
		if json is None:
			wx.MessageBox(f"Não foi possível  carregar o personagem '{nome_personagem}'. O arquivo de configuração pode estar ausente ou corrompido.", "Erro", wx.ICON_ERROR)
			self.listaDePersonagens.remove(nome_personagem)
			self.listBox.Set(self.listaDePersonagens)
			config.removePersonagem(nome_personagem)
			return
		pasta_base_personagem = Path(config.config['gerais']['pastas-dos-muds'][nome_personagem])
		pasta_sons = pasta_base_personagem.parent / 'sons'
		pasta_logs = pasta_base_personagem / 'logs'
		cliente.definePastaLog(str(pasta_logs), json['nome'])
		msp.definePastaSons(pasta_sons)
		args = (json['endereço'], json['porta'])
		dialogo_conexao = DialogoConectando(self, args, json)
		resultado = dialogo_conexao.ShowModal()
		if resultado == wx.ID_OK:
			self.dados_conexao = dialogo_conexao.dados_conexao
			dialogo_conexao.Destroy()
			self.EndModal(wx.ID_OK)
		else:
			dialogo_conexao.Destroy()
			wx.MessageBox('Não foi possível se conectar.', 'Erro de Conexão', wx.ICON_ERROR)
	def adicionaPersonagem(self, evento):
		dialogo_adiciona=wx.Dialog(self, title='Adicionar personagem')
		painel=wx.Panel(dialogo_adiciona)
		wx.StaticText(painel, label="nome do Mud, necessário para criar  uma pasta para o mud.")
		self.campoTextoNomeMud=wx.TextCtrl(painel)
		wx.StaticText(painel, label='nome do personagem:')
		self.campoTextoNome=wx.TextCtrl(painel)
		wx.StaticText(painel, label='senha, (deixe em branco para não logar automaticamente):')
		self.campoTextoSenha=wx.TextCtrl(painel, style=wx.TE_PASSWORD)
		wx.StaticText(painel, label='Endereço:')
		self.campoTextoEndereco=wx.TextCtrl(painel)
		wx.StaticText(painel, label='porta:')
		self.campoPorta = wx.SpinCtrl(painel, min=1, max=65535, initial=4000)
		self.loginAutomatico=wx.CheckBox(painel, label='Logar automaticamente ao conectar')
		self.reproduzirForaDaJanela= wx.CheckBox(painel, label="Reproduzir sons fora da janela do MUD")
		self.reproduzirForaDaJanela.SetValue(True)
		self.lerForaDaJanela = wx.CheckBox(painel, label='Ler mensagens fora da janela do MUD.')
		self.lerForaDaJanela.SetValue(True)

		btnSalvar=wx.Button(painel, wx.ID_OK, label='&salvar')
		btnSalvar.Bind(wx.EVT_BUTTON, lambda evt: self.salvaConfiguracoes(evt, dialogo_adiciona))
		btnCancelar=wx.Button(painel, wx.ID_CANCEL, label='&cancelar')
		dialogo_adiciona.ShowModal()
		dialogo_adiciona.Destroy()
	def editaPersonagem(self, evento):
		if self.listBox.GetSelection() == wx.NOT_FOUND: return
		nome_personagem = self.listaDePersonagens[self.listBox.GetSelection()]
		json = personagem.carregaPersonagem(nome_personagem)
		if json is None:
			wx.MessageBox(f"Não foi possível carregar o personagem '{nome_personagem}'. O arquivo de configuração pode estar ausente ou corrompido.", "Erro", wx.ICON_ERROR)
			return
		dialogo_edita=wx.Dialog(self, title='editar personagem')
		painel=wx.Panel(dialogo_edita)
		caminho_completo = Path(config.config['gerais']['pastas-dos-muds'][nome_personagem])
		nome_mud = caminho_completo.parent.name
		wx.StaticText(painel, label='Nome do MUD:')
		self.campoTextoNomeMud = wx.TextCtrl(painel, value=str(nome_mud))
		self.campoTextoNomeMud.Enable(False)
		wx.StaticText(painel, label='nome do personagem:')
		self.campoTextoNome=wx.TextCtrl(painel, value = nome_personagem)
		self.campoTextoNome.Enable(False)
		wx.StaticText(painel, label='senha: deixar em branco, caso não queira logar altomaticamente, ou seja um mud.')
		self.campoTextoSenha=wx.TextCtrl(painel, value=json.get('senha') or '', style=wx.TE_PASSWORD)
		wx.StaticText(painel, label='Endereço:')
		self.campoTextoEndereco=wx.TextCtrl(painel, value=json.get('endereço', ''))
		wx.StaticText(painel, label='porta:')
		self.campoPorta = wx.SpinCtrl(painel, min=1, max=65535, initial=json.get('porta', 4000))
		self.loginAutomatico=wx.CheckBox(painel, label='Logar automaticamente:')
		self.loginAutomatico.SetValue(json.get('login_automático', False))
		self.reproduzirForaDaJanela= wx.CheckBox(painel, label="Reproduzir sons fora da janela do MUD")
		self.reproduzirForaDaJanela.SetValue(json.get('reproduzir_sons_fora_janela', True))
		self.lerForaDaJanela = wx.CheckBox(painel, label='Ler mensagens fora da janela do MUD.')
		self.lerForaDaJanela.SetValue(json.get('ler_fora_janela', True))
		btnSalvar=wx.Button(painel, label='&salvar')
		btnSalvar.Bind(wx.EVT_BUTTON, lambda evt: self.salvaConfiguracoes(evt, dialogo_edita))
		btnCancelar=wx.Button(painel, wx.ID_CANCEL,label='&cancelar')
		btnCancelar.Bind(wx.EVT_BUTTON, lambda evt: dialogo_edita.EndModal(wx.ID_CANCEL))
		dialogo_edita.ShowModal()
		dialogo_edita.Destroy()
	def salvaConfiguracoes(self, evento, dialogo_pai):
		nome_mud = self.campoTextoNomeMud.GetValue().strip()
		nome=self.campoTextoNome.GetValue().strip()
		if not nome_mud:
			wx.MessageBox('Erro', 'por favor, preencha o nome do MUD.', wx.ICON_ERROR)
			self.campoTextoNomeMud.SetFocus()
			return
		if not nome:
			wx.MessageBox('Erro', 'Por favor coloque o nome do personagem.', wx.ICON_ERROR)
			self.campoTextoNome.SetFocus()
			return
		if not self.campoTextoEndereco.GetValue():
			wx.MessageBox('erro', 'por favor, preencha  o campo do endereço.', wx.ICON_ERROR)
			self.campoTextoEndereco.SetFocus()
			return
		if not self.campoPorta.GetValue():
			wx.MessageBox('Erro', 'Por favor, escolha uma porta.', wx.ICON_ERROR)
			self.campoPorta.SetFocus()
			return
		if self.campoTextoNome.IsEnabled() and nome in self.listaDePersonagens:
			wx.MessageBox('Erro', 'Um personagem com este nome já existe.', wx.ICON_ERROR)
			self.campoTextoNome.SetFocus()
			return
		pasta_base_muds = Path(config.config['gerais']['diretorio-de-dados']) / "clientmud" / "muds"
		pasta_do_mud = pasta_base_muds / nome_mud
		pasta_do_personagem = pasta_do_mud / nome
		if not self.campoTextoNomeMud.IsEnabled(): dic_antigo = personagem.carregaPersonagem(nome) or {}
		else: dic_antigo = {}
		if not self.campoTextoSenha.GetValue() and self.loginAutomatico.GetValue(): self.loginAutomatico.SetValue(False)
		novo_dic = {
			**dic_antigo,
			'nome': nome,
			'senha': self.campoTextoSenha.GetValue(),
			'endereço': self.campoTextoEndereco.GetValue(),
			'porta': self.campoPorta.GetValue(),
			'login_automático': self.loginAutomatico.GetValue(),
			'reproduzir_sons_fora_janela': self.reproduzirForaDaJanela.GetValue(),
			'ler_fora_janela': self.lerForaDaJanela.GetValue()
		}
		if self.campoTextoNome.IsEnabled():
			confirmacao = personagem.criaPersonagem(
				pasta=str(pasta_do_personagem),
				pastaSons = str(pasta_do_mud / 'sons'),
				**novo_dic
			)
		else:
			confirmacao = personagem.atualizaPersonagem(nome, novo_dic)
		if confirmacao:
			config.atualizaJson()
			self.listBox.Set(self.listaDePersonagens)
			self.mostraComponentes()
			self.listBox.SetSelection(len(self.listaDePersonagens)-1)
			self.listBox.SetFocus()
			dialogo_pai.EndModal(wx.ID_OK)
		else:
			wx.MessageBox('Ocorreu um erro ao salvar as configurações do personagem. Verifique as permissões de escrita na pasta do cliente.', 'Erro de Salvamento', wx.ICON_ERROR)
	def removePersonagem(self, evento):
		index=self.listBox.GetSelection()
		if index == wx.NOT_FOUND: return
		nome = self.listaDePersonagens[index]
		dialogoPergunta=wx.MessageDialog(self, f'deseja realmente remover o personagem "{nome}"?\ntodos os dados do personagens serão apagados definitivamente, incluindo as pastas criadas.', 'deletar personagem', wx.OK|wx.CANCEL|wx.ICON_QUESTION)
		if dialogoPergunta.ShowModal() == wx.ID_OK:
			personagem.removePersonagem(nome)
			self.listBox.Set(self.listaDePersonagens)
			self.mostraComponentes()
			if self.listaDePersonagens:
				index_atualizado = min(index, len(self.listaDePersonagens) -1)
				self.listBox.SetSelection(index_atualizado)
				self.listBox.SetFocus()
		dialogoPergunta.Destroy()
	def conexaomanual(self, evento):
		dialogo=dialogoConexaoManual(self)
		if dialogo.ShowModal() == wx.ID_OK:
			endereco = dialogo.endereco.GetValue().strip()
			porta = dialogo.porta.GetValue()
			dialogo.Destroy()
			pasta_geral = Path(config.config['gerais']['diretorio-de-dados']) / 'clientmud'
			cliente.definePastaLog(str(pasta_geral / 'logs'))
			msp.definePastaSons(pasta_geral / 'sons')
			dialogo_conexao =  DialogoConectando(self, (endereco, porta))
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
	def verificaConexao(self, evento):
		if self.dialogo_conexao and self.dialogo_conexao.IsModal():
			self.dialogo_conexao.EndModal(wx.ID_CANCEL)
			self.dialogo_conexao = None
		if evento.tentativa_conexao:
			self.conectado = True
			self.dados_conexao = {
				'json_personagem': evento.json_personagem,
				'endereco': evento.endereco,
				'porta': evento.porta
			}
			wx.CallAfter(self.EndModal, wx.ID_OK)
class dialogoConexaoManual(wx.Dialog):
	def __init__(self, pai=None):
		wx.Dialog.__init__(self, parent=pai, title="conexão")
		painel=wx.Panel(self)
		endereco=wx.StaticText(painel, label="&endereço:")
		self.endereco=wx.TextCtrl(painel)
		porta=wx.StaticText(painel, label="&porta:")
		self.porta = wx.SpinCtrl(painel, min=1, max=65535)
		if config.config['gerais']['ultima-conexao']:
			self.endereco.SetValue(config.config['gerais']['ultima-conexao'][0])
			self.porta.SetValue(config.config['gerais']['ultima-conexao'][1])
		btnConecta = wx.Button(painel, wx.ID_OK, label="C&onectar")
		btnConecta.Bind(wx.EVT_BUTTON, self.confirma)
		btnCancela=wx.Button(painel, wx.ID_CANCEL, label="&cancelar")
		btnCancela.Bind(wx.EVT_BUTTON, self.cancela)
	def confirma(self, evento):
		if not self.endereco.GetValue():
			wx.MessageBox("Por favor, preencha o campo de endereço.", "erro")
			self.endereco.SetFocus()
			return
		if self.porta.GetValue()==1 or not self.porta.GetValue():
			wx.MessageBox("por favor, preencha o campo da porta.", "erro")
			self.porta.SetFocus()
			return
		self.EndModal(wx.ID_OK)
	def cancela(self, evento):
		self.EndModal(wx.ID_CANCEL)

class janelaMud(wx.Frame):
	def __init__(self, endereco, json=None):
		wx.Frame.__init__(self, parent=None, title=endereco+" Cliente mud.")
		self.json_personagem = json
		self.nome = endereco
		self.janelaFechada = False
		self.janelaAtivada=True
		self.saidaFoco=False
		self.triggers = []
		self.keys = []
		self.timers = []
		self.gerenciador_timers = None
		self.historicos_customizados = {}
		self.historicos_abertos = {}
		self.comandos=[]
		self.indexComandos=len(self.comandos)
		self.rascunho = ''
		self._defineVariaveis()
		self.menuBar()
		self.Show()
		painel=wx.Panel(self)
		self.Bind(wx.EVT_ACTIVATE, self.janelaAtiva)
		self.Bind(wx.EVT_CLOSE, self.fechaApp)
		self.Bind(wx.EVT_CHAR_HOOK, self.teclasPressionadas)
		self.Bind(EVT_RESULTADO_CONEXAO, self._onResultadoConexao)
		self._aguardando_conexao = False
		wx.StaticText(painel, label="entrada")
		self.entrada = wx.TextCtrl(painel, style=wx.TE_PROCESS_ENTER | wx.TE_MULTILINE|wx.TE_DONTWRAP)
		self._atualizando_entrada = False
		self.entrada.Bind(wx.EVT_TEXT, self.aoDigitarEntrada)
		self.entrada.Bind(wx.EVT_KEY_DOWN, self.verificaConexao)
		self.entrada.Bind(wx.EVT_CHAR_HOOK, self.enviaTexto)
		self.entrada.Bind(wx.EVT_TEXT_PASTE, self.aoColar)
		wx.StaticText(painel, label="saída")
		self.saida=wx.TextCtrl(painel, style=wx.TE_READONLY|wx.TE_MULTILINE | wx.TE_DONTWRAP)
		self.saida.Bind(wx.EVT_SET_FOCUS, self.ganhaFoco)
		self.saida.Bind(wx.EVT_KILL_FOCUS, self.perdeFoco)
		self.saida.Bind(wx.EVT_CHAR, self.detectaTeclas)
		self.mud=Mud(self)
		Thread(target=self.mud.mostraMud).start()
		wx.CallAfter(self.inicia_gerenciador_timers)
		if self.json_personagem and self.json_personagem['login_automático']:
			self.realizaLogin()

	def _defineVariaveis(self):
		self.pasta_geral=f"{config.config['gerais']['diretorio-de-dados']}\\clientmud"
		self.nome_mud = None
		if self.json_personagem:
			self.nome = self.json_personagem['nome']
			self.senha = self.json_personagem.get('senha')
			self.reproduzirSons = self.json_personagem.get('reproduzir_sons_fora_janela', True)
			self.lerMensagens=self.json_personagem.get('ler_fora_janela', False)
			self.login = self.json_personagem.get('login_automático', False)
			pasta_base_personagem = Path(config.config['gerais']['pastas-dos-muds'][self.nome])
			self.nome_mud = pasta_base_personagem.parent.name
			self.pasta_personagem = pasta_base_personagem
			self.pasta_logs = pasta_base_personagem / 'logs'
			self.pasta_scripts = pasta_base_personagem / 'scripts'
			self.pasta_sons = pasta_base_personagem.parent / 'sons'
		else:
			self.pasta_logs = Path(self.pasta_geral) / 'logs'
			self.pasta_scripts = Path(self.pasta_geral) / 'scripts'
			self.pasta_sons = Path(self.pasta_geral) / 'sons'
			self.reproduzirSons = config.config['gerais'].get('toca-sons-fora-da-janela', True)
			self.lerMensagens = config.config['gerais'].get('ler fora da janela', True)
			self.login = False
		self.carregaTriggers()
		self.carregaTimers()
		self.carregaKeys()

	def realizaLogin(self):
		cliente.enviaComando(self.json_personagem.get('nome'))
		cliente.enviaComando(self.json_personagem.get('senha'))

	def _iniciarConexaoThread(self, endereco, porta):
		if self._aguardando_conexao:
			return
		self._aguardando_conexao = True
		try:
			cliente.terminaCliente()
		except:
			pass
		self.mud.reiniciaFilas()
		self.saida.Clear()
		self.comandos.clear()
		self.indexComandos = len(self.comandos)
		self.saida.AppendText(f"Conectando em {endereco}:{porta}...\n")
		fale("Conectando")
		ThreadIniciaConexao(self, (endereco, porta), self.json_personagem).start()

	def _onResultadoConexao(self, evento):
		self._aguardando_conexao = False
		if evento.tentativa_conexao:
			Thread(target=self.mud.mostraMud).start()
			if self.login:
				self.realizaLogin()
			self.entrada.SetFocus()
		else:
			self.saida.AppendText("Falha ao reconectar.\n")
			fale("Falha ao reconectar")

	def _setEntradaValor(self, texto=None, limpar=False):
		self._atualizando_entrada = True
		try:
			if limpar:
				self.entrada.Clear()
			elif texto is not None:
				self.entrada.SetValue(texto)
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
		if self.indexComandos > total + 1:
			self.indexComandos = total + 1
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
		if self.indexComandos <= 0:
			return
		self.indexComandos -= 1
		self._setEntradaValor(self.comandos[self.indexComandos])

	def proximoComando(self):
		total = len(self.comandos)
		if self.indexComandos < 0:
			self.indexComandos = 0
		if self.indexComandos > total + 1:
			self.indexComandos = total + 1
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

	def enviaTexto(self, evento):
		cod = evento.GetKeyCode()
		mod = evento.GetModifiers()
		if cod == wx.WXK_RETURN and (mod == wx.MOD_SHIFT or mod == wx.MOD_NONE):
			if not (cliente.ativo and not cliente.eof):
				self.perguntaReconexao()
				return
			texto_bruto = self.entrada.GetValue()
			texto_limpo = texto_bruto.strip()
			if texto_limpo:
				self.adicionaComandoLista(texto_limpo)
				comandos = texto_limpo.split(';')
				for cmd in comandos:
					if cmd.strip(): cliente.enviaComando(cmd.strip())
			if mod == wx.MOD_NONE:
				self.rascunho = ''
				self.indexComandos = len(self.comandos)
				self._setEntradaValor(limpar=True)
			else: self.entrada.SetInsertionPointEnd()
			return
		if cod == wx.WXK_UP:
			self.comandoAnterior()
			return
		if cod == wx.WXK_DOWN:
			self.proximoComando()
			return
		evento.Skip()

	def adicionaComandoLista(self, comando):
		if len(self.comandos) >=99:
			self.comandos.remove(self.comandos[0])
			self.comandos.append(comando)
		else:
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

	def ganhaFoco(self, evento):
		self.saidaFoco=True
		evento.Skip()

	def perdeFoco(self, evento):
		self.saida.SetInsertionPointEnd()
		self.saidaFoco=False
		self.entrada.SetInsertionPointEnd()
		evento.Skip()

	def encerraFrame(self):
		if cliente.ativo and not cliente.eof:
			perguntaSaida=wx.MessageDialog(self, "Deseja sair do mud e voltar para a janela principal?", "Sair do Mud", wx.OK | wx.CANCEL | wx.ICON_QUESTION)
			if perguntaSaida.ShowModal()!=  wx.ID_OK:
				perguntaSaida.Destroy()
				return
			self.janelaFechada = True
			msp.musicOff()
			cliente.enviaComando("quit")
			cliente.terminaCliente()
			self.para_gerenciador_timers()
			wx.CallAfter(wx.GetApp().mostraDialogoEntrada)
			self.Destroy()
		else:
			msp.musicOff()
			self.janelaFechada = True
			cliente.terminaCliente()
			self.para_gerenciador_timers()
			wx.CallAfter(wx.GetApp().mostraDialogoEntrada)
			self.Destroy()

	def teclasPressionadas(self, evento):
		codigo = evento.GetKeyCode()
		if codigo == wx.WXK_ESCAPE:
			self.encerraFrame()
			return
		if self.saidaFoco:
			u = evento.GetUnicodeKey()
			if not (evento.ControlDown() or evento.AltDown()):
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
		ctrl = evento.ControlDown()
		alt = evento.AltDown()
		shift = evento.ShiftDown()
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

		for k in getattr(self, 'keys', []):
			if getattr(k, 'ativo', True) and k.tecla == comb and getattr(k, 'comando', ""):
				if cliente.ativo and not cliente.eof: cliente.enviaComando(k.comando)
				else:
					self.perguntaReconexao()
				return

		evento.Skip()

	def detectaTeclas(self, evento):
		u = evento.GetUnicodeKey()
		if self.saidaFoco and not evento.ControlDown() and not evento.AltDown() and (32 <= u <= 126):
			try:
				ch = chr(u)
			except:
				ch = ''

			if ch:
				self.entrada.SetFocus()
				self.entrada.SetValue(ch)
				self.entrada.SetInsertionPointEnd()
				self.saidaFoco = False
				return
		evento.Skip()

	def fechaApp(self, evento):
		if cliente.ativo and not cliente.eof:
			pergunta_saida = wx.MessageDialog(
				self,
				'Encerrar o aplicativo agora irá desconectar do MUD. Deseja encerrar?',
				'Encerrar aplicativo',
				wx.YES_NO|wx.ICON_QUESTION
			)
			if pergunta_saida.ShowModal() != wx.ID_YES:
				pergunta_saida.Destroy()
				return
			pergunta_saida.Destroy()
			self.janelaFechada = True
			msp.musicOff()
			cliente.terminaCliente()
			self.para_gerenciador_timers()
			if cliente:
				cliente.arquivoLog.close()
			self.Close()
			wx.GetApp().ExitMainLoop()
		else:
			self.janelaFechada = True
			msp.musicOff()
			cliente.terminaCliente()
			self.para_gerenciador_timers()
			self.Close()
			if cliente:
				cliente.arquivoLog.close()
			wx.GetApp().ExitMainLoop()

	def menuBar(self):
		geralMenu=wx.Menu()
		interrompeMusica=geralMenu.Append(wx.ID_ANY, "&Interromper música em reprodução\tCtrl-M")
		self.Bind(wx.EVT_MENU, self.interrompeMusica, interrompeMusica)
		geralMenu.AppendSeparator()
		encerraPrograma=geralMenu.Append(wx.ID_EXIT, "&Sair.")
		self.Bind(wx.EVT_MENU, self.fechaApp, encerraPrograma)
		menuPastas=wx.Menu()
		geral = menuPastas.Append(wx.ID_ANY, "Abrir Pasta Geral\tCtrl-G")
		self.Bind(wx.EVT_MENU, self.abrirGeral, geral)
		logs=menuPastas.Append(wx.ID_ANY, "abrir pasta de logs\tCtrl-L")
		self.Bind(wx.EVT_MENU, self.abrirLogs, logs)
		scripts = menuPastas.Append(wx.ID_ANY, "Abrir Pasta de Scripts\tCtrl-R")
		self.Bind(wx.EVT_MENU, self.abrirScripts, scripts)
		sons = menuPastas.Append(wx.ID_ANY, "Abrir Pasta de Sons\tCtrl-S")
		self.Bind(wx.EVT_MENU, self.abrirSons, sons)
		menuFerramentas = wx.Menu()
		menuAudio = wx.Menu()
		id_musica_mais = wx.NewIdRef()
		id_musica_menos = wx.NewIdRef()
		id_som_mais = wx.NewIdRef()
		id_som_menos = wx.NewIdRef()
		menuAudio.Append(id_musica_mais, "Aumentar volume Música\tCtrl+PgUp")
		menuAudio.Append(id_musica_menos, "Diminuir Volume Música\tCtrl+PgDn")
		menuAudio.Append(id_som_mais, "Aumentar Volume Sons\tCtrl+Shift+PgUp")
		menuAudio.Append(id_som_menos, "Diminuir Volume Sons\tCtrl+Shift+PgDn")
		self.Bind(wx.EVT_MENU, lambda e: self.alteraVolume('musica', 10), id=id_musica_mais)
		self.Bind(wx.EVT_MENU, lambda e: self.alteraVolume('musica', -10), id=id_musica_menos)
		self.Bind(wx.EVT_MENU, lambda e: self.alteraVolume('som', 10), id=id_som_mais)
		self.Bind(wx.EVT_MENU, lambda e: self.alteraVolume('som', -10),id=id_som_menos)
		menuFerramentas.AppendSubMenu(menuAudio, "&Audio")
		menuGerenciarKeys = menuFerramentas.Append(wx.ID_ANY, 'Gerenciar atalhos...\tCtrl-K')
		self.Bind(wx.EVT_MENU, self.abrirGerenciadorKeys, menuGerenciarKeys)
		menuGerenciarTriggers = menuFerramentas.Append(wx.ID_ANY, "Gerenciar &Triggers...\tCtrl-T")
		self.Bind(wx.EVT_MENU, self.abrirGerenciadorTriggers, menuGerenciarTriggers)
		menuGerenciarTimers = menuFerramentas.Append(wx.ID_ANY, "Gerenciar &Timers...\tCtrl-Y")
		self.Bind(wx.EVT_MENU, self.abrirGerenciadorTimers, menuGerenciarTimers)
		self.menuHistoricos = wx.Menu()
		menuFerramentas.AppendSubMenu(self.menuHistoricos, "&Históricos\tCtrl-H")
		ditado = menuFerramentas.Append(wx.ID_ANY, "Escrever por voz\tCtrl-O")
		self.Bind(wx.EVT_MENU, self.falaPorVoz, ditado)
		menuBar=wx.MenuBar()
		menuBar.Append(geralMenu, "&geral")
		menuBar.Append(menuPastas, "&pastas")
		menuBar.Append(menuFerramentas, "&Ferramentas")
		self.SetMenuBar(menuBar)

	def abrirGerenciadorTriggers(self, evento):
		dlg = DialogoGerenciaTriggers(self, self.triggers)
		if dlg.ShowModal() == wx.ID_OK:
			if dlg.alteracoes_feitas:
				self.salvaConfiguracoesPersonagem()
		dlg.Destroy()

	def falaPorVoz(self, evento):
		threading.Thread(target=self.ouvir_microfone_thread, daemon=True).start()

	def ouvir_microfone_thread(self):
		r = sr.Recognizer()
		with sr.Microphone() as source:
			try:
				r.adjust_for_ambient_noise(source, duration=0.5)
				fale("Comece a falar.")
				r.pause_threshold = 1.0
				r.non_speaking_duration = 1.0
				r.energy_threshold = 100
				r.dynamic_energy_threshold = True

				audio = r.listen(source, phrase_time_limit=None)

				texto = r.recognize_google(audio, language="pt-BR")

				cliente.enviaComando(texto)
			except sr.UnknownValueError:
				fale("Não entendi o que foi dito.")
			except sr.RequestError as e:
				fale(f"Erro na requisição: {e}")
			except Exception as e:
				fale(f"Erro inesperado: {e}")

	def abrirGerenciadorTimers(self, evento):
		if not self.gerenciador_timers:
			wx.MessageBox("O gerenciador de timers não está ativo.", "Erro", wx.ICON_ERROR)
			return

		dlg = DialogoGerenciaTimers(self, self.timers, self.gerenciador_timers)
		if dlg.ShowModal() == wx.ID_OK:
			if dlg.alteracoes_feitas:
				self.salvaConfiguracoesPersonagem()
		dlg.Destroy()

	def abrirGerenciadorKeys(self, evento=None):
		dlg = DialogoGerenciaKeys(self, self.keys)
		if dlg.ShowModal() == wx.ID_OK:
			self.salvaConfiguracoesPersonagem()
		dlg.Destroy()

	def adiciona_ao_historico_customizado(self, nome_historico, linha):
		if nome_historico not in self.historicos_customizados:
			self.historicos_customizados[nome_historico] = []
			item_menu = self.menuHistoricos.Append(wx.ID_ANY, nome_historico)
			self.Bind(wx.EVT_MENU, lambda evt, name=nome_historico: self.mostra_historico(name), item_menu)
		self.historicos_customizados[nome_historico].append(linha)
		if nome_historico in self.historicos_abertos:
			dlg = self.historicos_abertos[nome_historico]
			if dlg: wx.CallAfter(dlg.adiciona_linha, linha)

	def mostra_historico(self, nome_historico):
		if nome_historico in self.historicos_abertos:
			self.historicos_abertos[nome_historico].Raise()
			return
		dlg = DialogoHistorico(self, title=f"Histórico: {nome_historico}", nome_historico=nome_historico)
		self.historicos_abertos[nome_historico] = dlg
		dlg.ShowModal()
		if nome_historico in self.historicos_abertos:
			del self.historicos_abertos[nome_historico]
		dlg.Destroy()

	def carregaTimers(self):
		timers_globais = [Timer(cfg) for cfg in config.carregaGlobalConfig().get('timers', [])]
		timers_mud = []
		if self.nome_mud:
			timers_mud = [Timer(cfg) for cfg in config.carregaMudConfig(self.nome_mud).get('timers', [])]
		
		timers_locais = []
		if self.json_personagem is not None:
			timers_locais = [Timer(cfg) for cfg in self.json_personagem.get('timers', [])]
		else:
			with open("config.json") as arquivo:
				timers_locais = [Timer(cfg) for cfg in json.load(arquivo).get('configuracoes-conexoes-manuais', {}).get('timers', [])]
				
		self.timers = timers_globais + timers_mud + timers_locais

	def inicia_gerenciador_timers(self):
		if not self.gerenciador_timers and cliente.ativo:
			configs_para_thread = [t.to_dict() for t in self.timers]
			self.gerenciador_timers = GerenciadorTimers(configs_para_thread, cliente)
			self.gerenciador_timers.start()

	def para_gerenciador_timers(self):
		if self.gerenciador_timers:
			self.gerenciador_timers.parar()
			self.gerenciador_timers.join(timeout=1.0)
			self.gerenciador_timers = None

	def interrompeMusica(self, evento):
		msp.musicOff()

	def abrirGeral(self, evento):
		subprocess.Popen(f"explorer {self.pasta_geral}")

	def abrirLogs(self, evento):
		subprocess.Popen(f"explorer {self.pasta_logs}")

	def abrirScripts(self, evento):
		subprocess.Popen(f"explorer {self.pasta_scripts}")

	def abrirSons(self, evento):
		subprocess.Popen(f"explorer {self.pasta_sons}")

	def focaSaida(self):
		self.saida.Unbind(wx.EVT_KILL_FOCUS, handler= self.perdeFoco)
		self.saida.Unbind(wx.EVT_SET_FOCUS, handler=self.ganhaFoco)
		self.saida.Unbind(wx.EVT_CHAR, handler=self.detectaTeclas)
		self.saida.SetFocus()
		self.saidaFoco=True
		self.entrada.Disable()

	def janelaAtiva(self, evento):
		self.janelaAtivada = evento.GetActive()
		evento.Skip()

	def reconecta(self):
		endereco = cliente.endereco
		porta = cliente.porta
		if not endereco or not porta:
			if self.json_personagem:
				endereco = self.json_personagem.get('endereço')
				porta = self.json_personagem.get('porta')
			elif config.config['gerais'].get('ultima-conexao'):
				endereco, porta = config.config['gerais']['ultima-conexao']
		if endereco and porta:
			self._iniciarConexaoThread(endereco, porta)

	def perguntaReconexao(self):
		if self.janelaFechada:
			return
		dlg = wx.MessageDialog(self, 'Deseja se reconectar?', 'Conexão finalizada', wx.YES_NO|wx.ICON_QUESTION)
		if dlg.ShowModal() == wx.ID_YES:
			dlg.Destroy()
			self.reconecta()
		else:
			dlg.Destroy()
			self.focaSaida()

	def carregaTriggers(self):
		triggers_globais = [Trigger(cfg) for cfg in config.carregaGlobalConfig().get('triggers', [])]
		triggers_mud = []
		if self.nome_mud:
			triggers_mud = [Trigger(cfg) for cfg in config.carregaMudConfig(self.nome_mud).get('triggers', [])]

		triggers_locais = []
		if self.json_personagem is not None:
			triggers_locais = [Trigger(cfg) for cfg in self.json_personagem.get('triggers', [])]
		else:
			with open("config.json") as arquivo:
				triggers_locais = [Trigger(cfg) for cfg in json.load(arquivo).get('configuracoes-conexoes-manuais', {}).get('triggers', [])]
		
		self.triggers = triggers_globais + triggers_mud + triggers_locais

	def carregaKeys(self):
		keys_globais = [Key(cfg) for cfg in config.carregaGlobalConfig().get('keys', [])]
		keys_mud = []
		if self.nome_mud:
			keys_mud = [Key(cfg) for cfg in config.carregaMudConfig(self.nome_mud).get('keys', [])]

		keys_locais = []
		if self.json_personagem is not None:
			keys_locais = [Key(cfg) for cfg in self.json_personagem.get('keys', [])]
		else:
			with open("config.json") as arquivo:
				keys_locais = [Key(cfg) for cfg in json.load(arquivo).get('configuracoes-conexoes-manuais', {}).get('keys', [])]
				
		self.keys = keys_globais + keys_mud + keys_locais

	def salvaConfiguracoesPersonagem(self):
		triggers_local, triggers_mud, triggers_global = [], [], []
		for t in self.triggers:
			if t.escopo == 2: triggers_global.append(t.to_dict())
			elif t.escopo == 1: triggers_mud.append(t.to_dict())
			else: triggers_local.append(t.to_dict())

		timers_local, timers_mud, timers_global = [], [], []
		for t in self.timers:
			if t.escopo == 2: timers_global.append(t.to_dict())
			elif t.escopo == 1: timers_mud.append(t.to_dict())
			else: timers_local.append(t.to_dict())

		keys_local, keys_mud, keys_global = [], [], []
		for k in self.keys:
			if k.escopo == 2: keys_global.append(k.to_dict())
			elif k.escopo == 1: keys_mud.append(k.to_dict())
			else: keys_local.append(k.to_dict())

		config.salvaGlobalConfig(triggers_global, timers_global, keys_global)

		if self.nome_mud:
			config.salvaMudConfig(self.nome_mud, triggers_mud, timers_mud, keys_mud)
		else:
			for item in triggers_mud + timers_mud + keys_mud:
				item['escopo'] = 0 
				if item in triggers_mud: triggers_local.append(item)
				elif item in timers_mud: timers_local.append(item)
				elif item in keys_mud: keys_local.append(item)

		if not self.json_personagem:
			config.atualizaConfigsConexaoManual(triggers_local, timers_local, keys_local)
			return

		self.json_personagem['triggers'] = triggers_local
		self.json_personagem['timers'] = timers_local
		self.json_personagem['keys'] = keys_local
		if not personagem.atualizaPersonagem(self.nome, self.json_personagem):
			wx.MessageBox("Falha ao salvar as configurações do personagem.", "Erro", wx.ICON_ERROR)

	def verificaConexao(self, evento):
		if evento.GetKeyCode() == wx.WXK_RETURN and (not cliente.ativo or cliente.eof):
			self.perguntaReconexao()
			return
		evento.Skip()

	def alteraVolume(self, tipo, valor):
		if not msp.alteraVolume(tipo, valor): fale(f"Volume de {tipo}  chegou no limite.")

class Mud:
	def __init__(self, janelaMud):
		self.janelaMud = janelaMud
		self.padraoSom = re.compile(r"!!SOUND\(([^\s\\/!]+)\s*V?=?(\d+)?\)", re.IGNORECASE)
		self.padraoMusica = re.compile(r"!!MUSIC\(([^\s!\\/]+)\s*V?=?(\d+)?\s*L?=?(-?\d+)?\)", re.IGNORECASE)
		self.padraoTotal = re.compile(r"!!\w+\([^)]*\)")
		self.padraoAnsi = re.compile(r'\x1b\[\d+(?:;\d+)*m')
		self.fila_mensagens = queue.Queue()
		
		self.max_linhas = 2000
		self.linhas_remover = 50
	def reiniciaFilas(self):
		self.fila_mensagens = queue.Queue()
	def pegaMusica(self, mensagem):
		args=re.findall(self.padraoMusica, mensagem)
		if "off)" in mensagem.lower():
			msp.musicOff()
		if args:
			for arg in args:
				arquivo=arg[0]
				v=int(arg[1]) if arg[1] != "" else 100
				l= int(arg[2]) if arg[2] != "" else 1
				msp.music(arquivo, v, l)
	def pegaSom(self,mensagem):
		args = re.findall(self.padraoSom, mensagem)
		for arg in args:
			arquivo = arg[0]
			v=int(arg[1]) if arg[1] != "" else 100
			msp.sound(arquivo, v)


	def thread_recebe(self):
		while cliente.ativo:
			mensagem = cliente.recebeMensagem()
			if mensagem:
				self.fila_mensagens.put(mensagem)
			else:
				sleep(0.01)

	def mostraMud(self):
		sleep(0.1)
		Thread(target=self.thread_recebe, daemon=True).start()
		while True:
			try:
				mensagem = self.fila_mensagens.get(timeout=0.1)
			except queue.Empty:
				if cliente.eof or not cliente.ativo:
					msp.musicOff()
					break
				continue
			for linha in mensagem.split("\n"):
				self.processaLinha(linha)
			if cliente.eof or not cliente.ativo:
				msp.musicOff()
				break
	def processaLinha(self, linha):
		linha = self.padraoAnsi.sub('', linha).strip()
		linha  = ''.join(c for c in linha if c.isprintable() or c in '\n\r')
		if not linha:
			return

		for trigger in self.janelaMud.triggers:
			grupos_capturados = trigger.verifica(linha)
			
			if grupos_capturados is not None:
				
				if trigger.som_acao:
					wx.CallAfter(msp.sound, trigger.som_acao, trigger.som_volume)
				
				if trigger.acao == 'comando':
					comandos_para_enviar = self.processa_comandos_trigger(trigger.valor_acao, grupos_capturados)
					for cmd in comandos_para_enviar:
						cliente.enviaComando(cmd)
				
				elif trigger.acao == 'som':
					wx.CallAfter(msp.sound, trigger.valor_acao, 100)
				
				elif trigger.acao == 'historico':
					self.janelaMud.adiciona_ao_historico_customizado(trigger.valor_acao, linha)
				
				if trigger.ignorar_historico_principal:
					return
		
		if linha.lower().startswith(("!!sound(", "!!music(")):
			if self.janelaMud.reproduzirSons or self.janelaMud.janelaAtivada:
				wx.CallAfter(self.pegaSom, linha)
				wx.CallAfter(self.pegaMusica, linha)
			return

		executor.submit(cliente.salvaLog, linha)
		if self.janelaMud.lerMensagens or self.janelaMud.janelaAtivada:
			wx.CallAfter(fale, linha)
		
		if self.janelaMud.saidaFoco:
			wx.CallAfter(self.atualizaSaidaComFoco, linha)
		else:
			wx.CallAfter(self.adicionaSaida, linha)
	def processa_comandos_trigger(self, comando_bruto, grupos):
		comandos_finais = []
		comandos_com_vars = comando_bruto
		
		for i, group_text in enumerate(grupos, 1):
			comandos_com_vars = comandos_com_vars.replace(f'%{i}', group_text or '')
		
		comandos_base = comandos_com_vars.split(';')
		
		for cmd in comandos_base:
			cmd_limpo = cmd.strip()
			if not cmd_limpo:
				continue
			
			repeticoes = 1
			if cmd_limpo.startswith('#'):
				match = re.match(r'#(\d+)\s+(.*)', cmd_limpo)
				if match:
					try:
						repeticoes = int(match.group(1))
						if repeticoes > 100: repeticoes = 100
						if repeticoes < 1: repeticoes = 1
						cmd_limpo = match.group(2).strip()
					except ValueError:
						cmd_limpo = cmd.strip()
				else:
					cmd_limpo = cmd.strip()
			
			if cmd_limpo:
				for _ in range(repeticoes):
					comandos_finais.append(cmd_limpo)
					
		return comandos_finais


	def limitaHistorico(self):
		saida = self.janelaMud.saida
		if saida.GetNumberOfLines() > self.max_linhas:
			fim = saida.XYToPosition(0, self.linhas_remover)
			saida.Remove(0, fim)

	def atualizaSaidaComFoco(self, linha):
		saida = self.janelaMud.saida
		posicao = saida.GetInsertionPoint()
		saida.AppendText(linha+ '\n')
		saida.SetInsertionPoint(posicao)
		saida.ShowPosition(posicao)
	def adicionaSaida(self, linha):
		self.janelaMud.saida.AppendText(linha+ '\n')
		self.limitaHistorico()
		self.janelaMud.saida.SetInsertionPointEnd()

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
		wx.StaticText(painel, label="Valor da Ação (Se tipo de ação for histórico, o valor deste campo será o nome do histórico.):")
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
		btn_cancelar = wx.Button(painel, wx.ID_CANCEL, label='Cancelar')
		btn_salvar.Bind(wx.EVT_BUTTON, self.salvaTrigger)
		
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

		self.lista_triggers_ctrl = wx.ListCtrl(painel, style=wx.LC_REPORT|wx.LC_SINGLE_SEL)
		self.lista_triggers_ctrl.InsertColumn(0, "Nome do Trigger")

		self.btn_adicionar = wx.Button(painel, label="Adicionar...\tCtrl+A")
		self.btn_editar = wx.Button(painel, label="Editar...\tCtrl+E")
		self.btn_remover = wx.Button(painel, label="Remover\tDel")
		self.btn_ativar_desativar = wx.Button(painel, label="Ativar/Desativar\tCtrl+D")
		self.btn_fechar = wx.Button(painel, wx.ID_OK, label="Fechar")

		self.btn_adicionar.Bind(wx.EVT_BUTTON, self.on_adicionar)
		self.btn_editar.Bind(wx.EVT_BUTTON, self.on_editar)
		self.btn_remover.Bind(wx.EVT_BUTTON, self.on_remover)
		self.btn_ativar_desativar.Bind(wx.EVT_BUTTON, self.on_ativar_desativar)
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
			novo_trigger = dlg.trigger_atual
			self.triggers.insert(0, novo_trigger)
			self.atualizar_visualizacao_lista()
			self.alteracoes_feitas = True
		dlg.Destroy()

	def on_editar(self, evento):
		index_selecionado = self.lista_triggers_ctrl.GetFirstSelected()
		if index_selecionado == -1: return
		trigger_para_editar = self.triggers[index_selecionado]
		dlg = DialogoEditaTrigger(self, trigger_para_editar)
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
					comandos_individuais = timer['comando'].split(';')
					for cmd in comandos_individuais:
						cmd_limpo = cmd.strip()
						if cmd_limpo:
							self.cliente.enviaComando(cmd_limpo)
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
		nome_inicial = "" if self.e_novo else self.timer_atual.nome
		self.campo_nome = wx.TextCtrl(painel, value=nome_inicial)
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
		btn_cancelar = wx.Button(painel, wx.ID_CANCEL, label='Cancelar')
		btn_salvar.Bind(wx.EVT_BUTTON, self.salvaTimer)
		self.campo_nome.SetFocus()
	def salvaTimer(self, evento):
		if not self.campo_nome.GetValue().strip():
			wx.MessageBox("O nome não foi preenchido.", "Erro", wx.ICON_ERROR)
			return
		if not self.campo_comando.GetValue().strip():
			wx.MessageBox("O comando não foi preenchido.", "Erro", wx.ICON_ERROR)
			return

		self.timer_atual.nome = self.campo_nome.GetValue()
		self.timer_atual.comando = self.campo_comando.GetValue()
		self.timer_atual.intervalo = self.campo_intervalo.GetValue()
		self.timer_atual.ativo = self.ativo.IsChecked()
		self.timer_atual.escopo = self.choice_escopo.GetSelection()
		self.EndModal(wx.ID_OK)

class DialogoGerenciaTimers(wx.Dialog):
	def __init__(self, parent, timers_lista, gerenciador_timers_ref):
		super().__init__(parent, title="Gerenciador de Timers", size=(600, 400))
		self.parent = parent
		self.timers = timers_lista
		self.gerenciador_timers = gerenciador_timers_ref
		self.alteracoes_feitas = False
		painel = wx.Panel(self)
		self.lista_ctrl = wx.ListCtrl(painel, style=wx.LC_REPORT|wx.LC_SINGLE_SEL)
		self.lista_ctrl.InsertColumn(0, "Ativo")
		self.lista_ctrl.InsertColumn(1, "Nome")
		self.lista_ctrl.InsertColumn(2, "Intervalo:", format=wx.LIST_FORMAT_RIGHT)
		self.lista_ctrl.InsertColumn(3, "Comando(s)")
		self.btn_adicionar = wx.Button(painel, label="Adicionar...\tCtrl+A")
		self.btn_editar = wx.Button(painel, label="Editar...\tCtrl+E")
		self.btn_remover = wx.Button(painel, label="Remover\tDel")
		self.btn_ativar_desativar = wx.Button(painel, label="Ativar/Desativar")
		self.btn_fechar = wx.Button(painel, wx.ID_OK, label="Fechar")

		self.btn_adicionar.Bind(wx.EVT_BUTTON, self.on_adicionar)
		self.btn_editar.Bind(wx.EVT_BUTTON, self.on_editar)
		self.btn_remover.Bind(wx.EVT_BUTTON, self.on_remover)
		self.btn_ativar_desativar.Bind(wx.EVT_BUTTON, self.on_ativar_desativar)
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
		self.atualiza_botao_ativar(None)
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
			idx_foco = 0
			if item_selecionado != -1 and item_selecionado < self.lista_ctrl.GetItemCount():
				idx_foco = item_selecionado
			
			self.lista_ctrl.Select(idx_foco)
			self.lista_ctrl.Focus(idx_foco)
		else:
			self.btn_adicionar.SetFocus()

		self.atualiza_botao_ativar(None)
		self.mostraComponentes()

	def atualiza_botao_ativar(self, evento):
		index_selecionado = self.lista_ctrl.GetFirstSelected()
		if index_selecionado != -1:
			timer = self.timers[index_selecionado]
			self.btn_ativar_desativar.Enable(True)
			label = "Desativar" if timer.ativo else "Ativar"
			self.btn_ativar_desativar.SetLabel(f"{label}\tCtrl+D")
		else:
			self.btn_ativar_desativar.Enable(False)
			self.btn_ativar_desativar.SetLabel("Ativar/Desativar\tCtrl+D")
	def on_adicionar(self, evento):
		dlg = DialogoEditaTimer(self, None)
		if dlg.ShowModal() == wx.ID_OK:
			novo_timer = dlg.timer_atual
			self.timers.insert(0, novo_timer)
			self.atualizar_visualizacao_lista()
			self.alteracoes_feitas = True
			self.atualiza_gerenciador_timers()
		dlg.Destroy()

	def on_editar(self, evento):
		index = self.lista_ctrl.GetFirstSelected()
		if index == -1: return
		timer_obj = self.timers[index]
		dlg = DialogoEditaTimer(self, timer_obj)
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

class DialogoGerenciaKeys(wx.Dialog):
	def __init__(self, parent, lista_keys):
		super().__init__(parent, title="Gerenciar Atalhos")
		self.parent = parent
		self.lista_keys = lista_keys

		painel = wx.Panel(self)

		self.lista = wx.ListCtrl(painel, style=wx.LC_REPORT|wx.LC_SINGLE_SEL)
		self.lista.InsertColumn(0, "Nome", width=220)
		self.lista.InsertColumn(1, "Tecla", width=120)
		self.lista.InsertColumn(2, "Comando", width=260)
		self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.edita)

		self.btn_adicionar = wx.Button(painel, label="Adicionar...\tCtrl+A")
		self.btn_editar = wx.Button(painel, label="Editar...\tCtrl+E")
		self.btn_remover = wx.Button(painel, label="Remover\tDel")
		self.btn_ativar_desativar = wx.Button(painel, label="Ativar/Desativar\tCtrl+D")
		self.btn_fechar = wx.Button(painel, wx.ID_OK,label="Fechar")

		self.lista.Bind(wx.EVT_LIST_ITEM_SELECTED, self.atualiza_botao_ativar)
		self.lista.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.atualiza_botao_ativar)
		self.btn_adicionar.Bind(wx.EVT_BUTTON, self.adiciona)
		self.btn_editar.Bind(wx.EVT_BUTTON, self.edita)
		self.btn_remover.Bind(wx.EVT_BUTTON, self.remove)
		self.btn_ativar_desativar.Bind(wx.EVT_BUTTON, self.on_ativar_desativar)
		self.btn_fechar.Bind(wx.EVT_BUTTON, lambda evt: self.EndModal(wx.ID_OK))

		self.atualiza_lista()

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
			key = self.lista_keys[index_selecionado]
			self.btn_ativar_desativar.Enable(True)
			label = "Desativar" if key.ativo else "Ativar"
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
		if indice is None:
			return
		dlg = DialogoEditaKey(self, self.lista_keys[indice])
		if dlg.ShowModal() == wx.ID_OK:
			self.lista_keys[indice] = dlg.get_key()
			self.atualiza_lista()
			self.lista.Select(indice)
			self.lista.Focus(indice)
		dlg.Destroy()

	def remove(self, evt):
		indice = self.selecionado()
		if indice is None:
			return

		nome_key = getattr(self.lista_keys[indice], 'nome', 'este atalho')
		confirmacao = wx.MessageDialog(self, f"Tem certeza que deseja remover o atalho '{nome_key}'?", "Confirmar Remoção", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
		if confirmacao.ShowModal() == wx.ID_YES:
			del self.lista_keys[indice]
			self.atualiza_lista()
		confirmacao.Destroy()

	def on_ativar_desativar(self, evento):
		index = self.lista.GetFirstSelected()
		if index == -1: return
		self.lista_keys[index].ativo = not self.lista_keys[index].ativo
		self.atualiza_lista()

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
		self.btn_cancelar = wx.Button(painel, wx.ID_CANCEL, "Cancelar")
		self.btn_ok.Bind(wx.EVT_BUTTON, self.salva_key)
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
		if evt.ControlDown():
			mods.append("Ctrl")
		if evt.AltDown():
			mods.append("Alt")
		if evt.ShiftDown():
			mods.append("Shift")

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
		nome = self.campo_nome.GetValue().strip()
		tecla = self.campo_tecla.GetValue().strip()
		comando = self.campo_comando.GetValue().strip()
		ativo = self.ativo.IsChecked()
		if not nome:
			wx.MessageBox("Informe o nome do atalho.", "Aviso", wx.ICON_WARNING)
			self.campo_nome.SetFocus()
			return
		if not tecla:
			wx.MessageBox("Escolha a tecla do atalho.", "Aviso", wx.ICON_WARNING)
			self.campo_tecla.SetFocus()
			return
		if not comando:
			wx.MessageBox("Informe o comando do atalho.", "Aviso", wx.ICON_WARNING)
			self.campo_comando.SetFocus()
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

class DialogoHistorico(wx.Dialog):
	def __init__(self, parent, title, nome_historico):
		super().__init__(parent, title=title)
		self.nome_historico = nome_historico
		painel = wx.Panel(self)
		self.texto_ctrl = wx.TextCtrl(painel, style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_DONTWRAP)
		self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down)
		conteudo = "\n".join(parent.historicos_customizados.get(self.nome_historico, []))
		self.texto_ctrl.SetValue(conteudo)
		self.texto_ctrl.SetInsertionPointEnd()
	def on_key_down(self, event):
		if event.GetKeyCode() == wx.WXK_ESCAPE:
			self.EndModal(wx.ID_CANCEL)
		else:
			event.Skip()
	def adiciona_linha(self, linha):
		self.texto_ctrl.AppendText(linha + '\n')
		self.texto_ctrl.SetInsertionPointEnd()

class configuracoes(wx.Dialog):
	def __init__(self):
		wx.Dialog.__init__(self, parent=None, title="Configurações")
		painel=wx.Panel(self)
		pastaExecutavel=Path(sys.executable)
		self.pastaInicial= str(pastaExecutavel.parent)

		rotulo=wx.StaticText(painel, label='Pasta de dados.')
		self.campoTextoPasta=wx.TextCtrl(painel)
		self.campoTextoPasta.SetValue(self.pastaInicial)
		btnEscolhePasta=wx.Button(painel, label='&escolher pasta de dados')
		btnEscolhePasta.Bind(wx.EVT_BUTTON, self.escolhePasta)
		self.reproducaoForaDaJanela = wx.CheckBox(painel, label='Reproduzir sons fora da janela do MUD')
		self.falaForaDaJanela = wx.CheckBox(painel, label='Ler as mensagens fora da janela do MUD')
		self.verificaAtualizacao=wx.CheckBox(painel, label='Verificar atualizações automaticamente ao iniciar')
		self.verificaAtualizacao.SetValue(True)
		btnFinaliza=wx.Button(painel, label='&finalizar configuração.')
		btnFinaliza.Bind(wx.EVT_BUTTON, self.finalizaConfiguracao)
	def escolhePasta(self, evento):
		dialogo=wx.DirDialog(self, 'Escolha de pasta')
		if dialogo.ShowModal() == wx.ID_OK:
			self.pastaInicial=dialogo.GetPath()
			self.campoTextoPasta.SetValue(self.pastaInicial)
	def finalizaConfiguracao(self, evento):
		pasta=self.campoTextoPasta.GetValue()
		if pasta:
			pastaPath=Path(pasta)
			if pastaPath.exists():
				self.pastaInicial=pasta
				som = self.reproducaoForaDaJanela.GetValue()
				leitura = self.falaForaDaJanela.GetValue()
				atualizacao=self.verificaAtualizacao.GetValue()
				dic = {
					'gerais': {
						"toca-sons-fora-da-janela": som,
						'ler fora da janela': leitura,
						'verifica-atualizacoes-automaticamente': atualizacao,
						"ultima-conexao": [],
						"diretorio-de-dados": self.pastaInicial,
						"logs": str(Path(pastaPath, "clientmud", "logs")),
						"scripts": str(Path(pastaPath, "clientmud", "scripts")),
						"sons": str(Path(pastaPath, "clientmud", "sons")),
						"pastas-dos-muds": {}
					},
					'personagens': []
				}
				config.atualizaJson(dic)
				pastas.config = config
				pastas.criaPastaGeral()
				wx.MessageBox("As configurações foram finalizadas com êxito, O aplicativo será encerrado agora. Por favor, inicie-o novamente para utilizá-lo normalmente.", "Configuração Concluída com êxito.", wx.OK | wx.ICON_INFORMATION)
				self.Destroy()
				sys.exit()
			else:
				wx.MessageBox("por favor, digite uma pasta válida.", "erro.", wx.ICON_ERROR)
if __name__ == '__main__':
	app = Aplicacao()
	app.MainLoop()