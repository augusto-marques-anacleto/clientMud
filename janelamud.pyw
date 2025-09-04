import queue
import subprocess
from  pathlib import Path
import wx, logging,  re, sys, traceback
from threading import Thread
from time import sleep
from msp import Msp
msp=Msp()

from cliente import Cliente
cliente=Cliente()
from accessible_output2 import outputs
saida=outputs.auto.Auto()
fale=saida.speak
from configuracoes import Config, gerenciaPersonagens, gerenciaPastas
config=Config()
personagem=gerenciaPersonagens()
from log import gravaErro

def excepthook(exctype, value, tb):
	mensagem = ''.join(traceback.format_exception(exctype, value, tb))
	gravaErro(mensagem)
	wx.MessageBox(f"{mensagem}", "Erro no programa.")
	sys.exit()
sys.excepthook = excepthook

class dialogoEntrada(wx.Dialog):
	def __init__(self):
		wx.Dialog.__init__(self, parent=None, title="Conexões.")
		painel=wx.Panel(self)
		self.Bind(wx.EVT_CHAR_HOOK, self.teclaPressionada)
		self.Bind(wx.EVT_CLOSE, self.encerraAplicativo)
		self.listaDePersonagens=config.config['personagens']
		self.listBox=wx.ListBox(painel, choices=self.listaDePersonagens)
		if len(self.listaDePersonagens) >0:
			self.listBox.SetSelection(0)
		self.btnConecta=wx.Button(painel, label="conectar")
		self.btnConecta.Bind(wx.EVT_BUTTON, self.conecta)
		btnAdicionaPersonagem=wx.Button(painel, label="&adicionar personagem")
		btnAdicionaPersonagem.Bind(wx.EVT_BUTTON, self.adicionaPersonagem)
		self.btnEditaPersonagem=wx.Button(painel, label="&editar personagem")
		self.btnEditaPersonagem.Bind(wx.EVT_BUTTON, self.editaPersonagem)
		self.btnRemovePersonagem=wx.Button(painel, label="&remover personagem")
		self.btnRemovePersonagem.Bind(wx.EVT_BUTTON, self.removePersonagem)
		btnConexaomanual=wx.Button(painel, label="&conexão manual.")
		btnConexaomanual.Bind(wx.EVT_BUTTON, self.conexaomanual)
		btnSaida=wx.Button(painel, label='&sair')
		btnSaida.Bind(wx.EVT_BUTTON, self.encerraAplicativo)
		self.mostraComponentes()
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
		json=personagem.carregaPersonagem(self.listaDePersonagens[self.listBox.GetSelection()])
		cliente.definePastaLog(json['logs'], json['nome'])
		msp.definePastaSons(Path(json['sons']))
		if cliente.conectaServidor(json['endereço'], json['porta']):
			mud=janelaMud(json['nome'], json)
			if json['login automático']:
				cliente.enviaComando(json['nome'])
				cliente.enviaComando(json['senha'])
			self.Destroy()
		else:
			wx.MessageBox('Não foi possível se conectar.\n por favor, verifique sua conexão.', 'erro', wx.ICON_ERROR)
	def adicionaPersonagem(self, evento):
		self.Hide()
		self.dialogo=wx.Dialog(self, title='Adicionar personagem')
		self.pastaPersonagem = str(Path(config.config['gerais']['diretorio-de-dados'], 'clientmud', 'muds'))
		self.pastaLogs = config.config['gerais']['logs']
		self.pastaScripts = config.config['gerais']['scripts']
		self.pastaSons = config.config['gerais']['sons']
		painel=wx.Panel(self.dialogo)
		rotuloPasta=wx.StaticText(painel, label="nome do Mud, necessário caso queira criar  uma pasta para o mud.")
		self.campoTextoPasta=wx.TextCtrl(painel)
		self.listaDePastas = wx.ListCtrl(painel, style = wx.LC_REPORT)
		self.listaDePastas.InsertColumn(0, 'Nome')
		self.listaDePastas.InsertColumn(1, 'Caminho')
		self.listaDePastas.Append(['Pasta inicial:', self.pastaPersonagem])
		self.listaDePastas.Append(['Logs', self.pastaLogs])
		self.listaDePastas.Append(['Scripts', self.pastaScripts])
		self.listaDePastas.Append(['Sons', self.pastaSons])
		self.listaDePastas.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.alteraPasta)

		self.listaDePastas.Select(0)
		self.listaDePastas.Focus(0)
		rotuloNome=wx.StaticText(painel, label='nome do personagem ou mud')
		self.campoTextoNome=wx.TextCtrl(painel)
		rotuloSenha=wx.StaticText(painel, label='senha: deixar em branco, caso não queira logar altomaticamente, ou seja um mud.')
		self.campoTextoSenha=wx.TextCtrl(painel, style=wx.TE_PASSWORD)
		rotuloEndereco=wx.StaticText(painel, label='Endereço:')
		self.campoTextoEndereco=wx.TextCtrl(painel)
		rotuloPorta=wx.StaticText(painel, label='porta:')
		self.campoPorta = wx.SpinCtrl(painel, min=1, max=65535)
		self.loginAutomatico=wx.CheckBox(painel, label='Logar automaticamente:')
		self.reproduzirForaDaJanela= wx.CheckBox(painel, label="Reproduzir sons fora da janela do MUD")
		self.reproduzirForaDaJanela.SetValue(True)
		self.lerForaDaJanela = wx.CheckBox(painel, label='Ler mensagens fora da janela do MUD.')
		self.lerForaDaJanela.SetValue(True)
		self.criaSubPastas= wx.CheckBox(painel, label="Criar sub pastas de logs, scripts e sons automaticamente para o personagem Observação, a pasta sons ficará tro da pasta do mud, e as pastas logs e scripts ficará dentro da pasta do personagem.")
		self.criaSubPastas.Bind(wx.EVT_CHECKBOX, self.criaPastasPersonagem)

		btnSalvar=wx.Button(painel, label='&salvar')
		btnSalvar.Bind(wx.EVT_BUTTON, self.salvaConfiguracoes)
		btnCancelar=wx.Button(painel, label='&cancelar')
		btnCancelar.Bind(wx.EVT_BUTTON, self.encerraDialogo)
		self.dialogo.ShowModal()
	def editaPersonagem(self, evento):
		self.Hide()
		self.dialogo=wx.Dialog(self, title='editar personagem')
		painel=wx.Panel(self.dialogo)
		json=personagem.carregaPersonagem(self.listaDePersonagens[self.listBox.GetSelection()])
		self.pastaPersonagem = json['pasta']
		self.pastaLogs = json['logs']
		self.pastaScripts = json['scripts']
		self.pastaSons = json['sons']
		nome=json['nome']
		senha=json['senha']
		endereco=json['endereço']
		porta=json['porta']
		opcaoLogin=json['login automático']
		opcaoReproduzir = json["Reproduzir sons fora da janela do mud"]
		opcaoLer=json["ler fora da janela"]

		rotuloPasta=wx.StaticText(painel, label="pasta  do mud onde vai ficar  salva a pasta do personagem.")
		self.campoTextoPasta=wx.TextCtrl(painel)
		self.campoTextoPasta.SetValue(self.pastaPersonagem)
		self.listaDePastas = wx.ListCtrl(painel, style = wx.LC_REPORT)
		self.listaDePastas.InsertColumn(0, 'Nome')
		self.listaDePastas.InsertColumn(1, 'Caminho')
		self.listaDePastas.Append(['Pasta inicial:', self.pastaPersonagem])
		self.listaDePastas.Append(['Logs', self.pastaLogs])
		self.listaDePastas.Append(['Scripts', self.pastaScripts])
		self.listaDePastas.Append(['Sons', self.pastaSons])
		self.listaDePastas.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.alteraPasta)
		self.listaDePastas.Select(0)
		self.listaDePastas.Focus(0)
		rotuloNome=wx.StaticText(painel, label='nome do personagem ou mud')
		self.campoTextoNome=wx.TextCtrl(painel, value = nome)
		self.campoTextoNome.Enable(False)
		rotuloSenha=wx.StaticText(painel, label='senha: deixar em branco, caso não queira logar altomaticamente, ou seja um mud.')
		self.campoTextoSenha=wx.TextCtrl(painel, style=wx.TE_PASSWORD)
		self.campoTextoSenha.SetValue(senha)
		rotuloEndereco=wx.StaticText(painel, label='Endereço:')
		self.campoTextoEndereco=wx.TextCtrl(painel)
		self.campoTextoEndereco.SetValue(endereco)
		rotuloPorta=wx.StaticText(painel, label='porta:')
		self.campoPorta = wx.SpinCtrl(painel, min=1, max=65535)
		self.campoPorta.SetValue(porta)
		self.loginAutomatico=wx.CheckBox(painel, label='Logar automaticamente:')
		self.loginAutomatico.SetValue(opcaoLogin)
		self.reproduzirForaDaJanela= wx.CheckBox(painel, label="Reproduzir sons fora da janela do MUD")
		self.reproduzirForaDaJanela.SetValue(opcaoReproduzir)
		self.lerForaDaJanela = wx.CheckBox(painel, label='Ler mensagens fora da janela do MUD.')
		self.lerForaDaJanela.SetValue(opcaoLer)
		btnSalvar=wx.Button(painel, label='&salvar')
		btnSalvar.Bind(wx.EVT_BUTTON, self.salvaConfiguracoes)
		btnCancelar=wx.Button(painel, label='&cancelar')
		btnCancelar.Bind(wx.EVT_BUTTON, self.encerraDialogo)
		self.dialogo.ShowModal()
	def salvaConfiguracoes(self, evento):
		pasta=self.pastaPersonagem
		nome=self.campoTextoNome.GetValue()
		senha=self.campoTextoSenha.GetValue()
		endereco=self.campoTextoEndereco.GetValue()
		porta=self.campoPorta.GetValue()
		login=self.loginAutomatico.GetValue()
		opcaoSons = self.reproduzirForaDaJanela.GetValue()
		opcaoLer = self.lerForaDaJanela.GetValue()
		if not senha and login == True:
			login=False
		if not pasta:
			wx.MessageBox('Erro', 'por favor, preencha o campo da pasta.', wx.ICON_ERROR)
			self.campoTextoPasta.SetFocus()
		elif not nome:
			wx.MessageBox('Erro', 'Por favor coloque o nome do personagem.', wx.ICON_ERROR)
			self.campoTextoNome.SetFocus()
		elif not endereco:
			wx.MessageBox('erro', 'por favor, preencha  o campo do endereço.', wx.ICON_ERROR)
			self.campoTextoEndereco.SetFocus()
		elif not porta:
			wx.MessageBox('Erro', 'Por favor, escolha uma porta.', wx.ICON_ERROR)
			self.campoPorta.SetFocus()
		else:
			personagem.criaPersonagem(
			pasta = pasta,
			pastaLogs = self.pastaLogs,
			pastaScripts = self.pastaScripts,
			pastaSons = self.pastaSons,
			nome = nome,
			endereco = endereco,
			porta = porta,
			senha = senha,
			login = login,
			sons = opcaoSons,
			leitura=opcaoLer
			)
			if nome not in self.listaDePersonagens:
				self.listaDePersonagens.append(nome)
				self.listBox.Set(self.listaDePersonagens)
				self.mostraComponentes()
				self.listBox.SetSelection(len(self.listaDePersonagens)-1)
			self.Show()
			self.dialogo.Destroy()
	def encerraDialogo(self, evento):
		self.Show()
		self.dialogo.EndModal(wx.CANCEL)
	def removePersonagem(self, evento):
		dialogoPergunta=wx.MessageDialog(self, 'deseja realmente remover o personagem?\ntodos os dados do personagens serão apagados definitivamente, incluindo as pastas criadas.', 'deletar personagem', wx.OK|wx.CANCEL|wx.ICON_INFORMATION)
		if dialogoPergunta.ShowModal() == wx.ID_OK:
			index=self.listBox.GetSelection()
			if index != wx.NOT_FOUND:
				personagem.removePersonagem(self.listaDePersonagens[index])
				del self.listaDePersonagens[index]
				self.listBox.Set(self.listaDePersonagens)
				self.mostraComponentes()
	def conexaomanual(self, evento):
		self.Hide()
		dialogo=dialogoConexaoManual(self)
		resultado=dialogo.ShowModal()
		if resultado == wx.ID_OK:
			self.Destroy()
	def encerraAplicativo(self, evento):
		sys.exit()
	def escolhePasta(self, evento):
		dialogo=wx.DirDialog(self, 'Escolha de pasta')
		if dialogo.ShowModal() == wx.ID_OK:
			self.campoTextoPasta.SetValue(dialogo.GetPath())
	def atualizaListaDePastas(self):
		self.listaDePastas.SetItem(0, 1, str(self.pastaPersonagem))
		self.listaDePastas.SetItem(1, 1, str(self.pastaLogs))
		self.listaDePastas.SetItem(2, 1, str(self.pastaScripts))
		self.listaDePastas.SetItem(3, 1, str(self.pastaSons))


	def alteraPasta(self, evento):
		index = evento.GetIndex()
		dialogo=wx.DirDialog(self, 'Escolha de pasta')
		if dialogo.ShowModal() == wx.ID_OK:
			match index:
				case 0:
					self.pastaPersonagem= dialogo.GetPath()
					self.campoTextoPasta.SetValue(self.pastaPersonagem)
					self.atualizaListaDePastas()
				case 1:
					self.pastaLogs = dialogo.GetPath()
					self.atualizaListaDePastas()
				case 2:
					self.pastaScripts = dialogo.GetPath()
					self.atualizaListaDePastas()
				case 3:
					self.pastaSons = dialogo.GetPath()
					self.atualizaListaDePastas()

	def criaPastasPersonagem(self, evento):
		if self.criaSubPastas.IsChecked():
			if not self.campoTextoPasta.GetValue() or not self.campoTextoNome.GetValue():
				wx.MessageBox("Para usar essa função, primeiro você precisa escolher o nome do mud, para a criação da pasta do mud, que conterá a pasta do personagem, e o nome do personagem, para que seja criada a estrutura de pastas do personagem.", "Erro, informações ausentes.")
				self.criaSubPastas.SetValue(False)
			else:
				pastaMud = Path(config.config['gerais']['diretorio-de-dados'], 'clientmud', 'muds', self.campoTextoPasta.GetValue())
				self.pastaPersonagem = Path(pastaMud, self.campoTextoNome.GetValue())
				self.pastaLogs = Path(self.pastaPersonagem, 'logs')
				self.pastaScripts = Path(self.pastaPersonagem, 'scripts')
				self.pastaSons = Path(pastaMud, 'sons')
				self.atualizaListaDePastas()
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
		fale("Conectando, por favor, aguarde.")
		cliente.definePastaLog(config.config['gerais']['logs'])
		msp.definePastaSons(Path(config.config['gerais']['sons']))
		if self.endereco.GetValue()=="":
			wx.MessageBox("Por favor, preencha o campo de endereço.", "erro")
			self.endereco.SetFocus()
		elif self.porta.GetValue()==1:
			wx.MessageBox("por favor, preencha o campo da porta.", "erro")
			self.porta.SetFocus()
		elif cliente.conectaServidor(self.endereco.GetValue(), self.porta.GetValue()):
			config.config['gerais']['ultima-conexao']=[self.endereco.GetValue(), self.porta.GetValue()]
			config.atualizaJson()
			mud=janelaMud(self.endereco.GetValue())
			self.EndModal(wx.ID_OK)
		else:
			wx.MessageBox("Não foi possível realizar a conexão, por favor verifique sua conexão e se o endereço e porta estão corretos.", "Erro de conexão", wx.ICON_ERROR)
	def cancela(self, evento):
		pai=self.GetParent()
		pai.Show()
		self.Destroy()

class janelaMud(wx.Frame):
	def __init__(self, endereco, json=None):
		wx.Frame.__init__(self, parent=None, title=endereco+" Cliente mud.")
		painel=wx.Panel(self)
		self.janelaFechada = False
		self.menuBar()
		self.janelaAtivada=True
		self.saidaFoco=False
		self.pastaGeral=f"{config.config['gerais']['diretorio-de-dados']}\\clientmud"
		if json:
			self.pastaLogs = json['logs']
			self.pastaScripts = json['scripts']
			self.pastaSons=json['sons']
			self.reproduzirSons = json['Reproduzir sons fora da janela do mud']
			self.lerMensagens=json['ler fora da janela']
			self.nome = json['nome']
			self.senha = json['senha']
			self.login = json['login automático']
		else:
			self.pastaLogs=str(Path(config.config['gerais']['diretorio-de-dados'], 'clientmud', 'logs'))
			self.pastaScripts=str(Path(config.config['gerais']['diretorio-de-dados'], 'clientmud', 'scripts'))
			self.pastaSons=str(Path(config.config['gerais']['diretorio-de-dados'], 'clientmud', 'sons'))
			self.reproduzirSons = config.config['gerais']['toca-sons-fora-da-janela']
			self.lerMensagens = config.config['gerais']['ler fora da janela']
			self.login = False
		self.Bind(wx.EVT_ACTIVATE, self.janelaAtiva)
		self.Bind(wx.EVT_CLOSE, self.fechaApp)
		self.Bind(wx.EVT_CHAR_HOOK, self.teclasPressionadas)
		self.comandos=[]
		self.indexComandos=len(self.comandos)
		self.rotuloEntrada=wx.StaticText(painel, label="entrada")
		self.entrada=wx.TextCtrl(painel, style=wx.TE_PROCESS_ENTER)
		self.entrada.Bind(wx.EVT_CHAR_HOOK, self.enviaTexto)
		self.rotuloSaida=wx.StaticText(painel, label="saída")
		self.saida=wx.TextCtrl(painel, style=wx.TE_READONLY|wx.TE_MULTILINE | wx.TE_DONTWRAP)
		self.saida.Bind(wx.EVT_SET_FOCUS, self.ganhaFoco)
		self.saida.Bind(wx.EVT_KILL_FOCUS, self.perdeFoco)
		self.saida.Bind(wx.EVT_CHAR, self.detectaTeclas)
		self.Show()
		self.mud=Mud(self)
		Thread(target=self.mud.mostraMud).start()

	def enviaTexto(self, evento):
		if evento.GetKeyCode() == wx.WXK_RETURN and evento.GetModifiers() == wx.MOD_CONTROL:
			self.entrada.SetValue(self.entrada.GetValue()+"\n")
			self.entrada.SetInsertionPointEnd()
		elif evento.GetKeyCode() == wx.WXK_RETURN and evento.GetModifiers() == wx.MOD_SHIFT:
			if self.entrada.GetValue() != "":

				cliente.enviaComando(self.entrada.GetValue())
				self.texto=self.entrada.GetValue()
				#self.adicionaComandoLista(self.texto)
				self.entrada.Clear()
				self.indexComandos=len(self.comandos)
			else: cliente.enviaComando(self.texto)
		elif evento.GetKeyCode() == wx.WXK_RETURN:
			cliente.enviaComando(self.entrada.GetValue())
			self.texto=self.entrada.GetValue()
			self.adicionaComandoLista(self.texto)
			self.indexComandos=len(self.comandos)
			self.entrada.Clear()
		elif evento.GetKeyCode() == wx.WXK_UP:
			self.comandoAnterior()
		elif evento.GetKeyCode() == wx.WXK_DOWN:
			self.proximoComando()

		else:
			evento.Skip()
	def comandoAnterior(self):
		if self.indexComandos>0:
			self.indexComandos-=1
			self.entrada.SetValue(self.comandos[self.indexComandos])
	def proximoComando(self):
		if self.indexComandos <len(self.comandos): self.indexComandos+=1

		if self.indexComandos <= len(self.comandos) -1: self.entrada.SetValue(self.comandos[self.indexComandos])

		elif self.indexComandos >len(self.comandos)-1: self.entrada.Clear()

	def adicionaComandoLista(self, comando):
		if len(self.comandos) >=99:
			self.comandos.remove(self.comandos[0])
			self.comandos.append(comando)
		else:
			self.comandos.append(comando)
	def ganhaFoco(self, evento):
		self.saidaFoco=True
		evento.Skip()
	def perdeFoco(self, evento):
		self.saida.SetInsertionPointEnd()
		self.saidaFoco=False
		self.entrada.SetInsertionPointEnd()
		evento.Skip()
	def encerraFrame(self):
		if not cliente.eof:
			perguntaSaida=wx.MessageDialog(self, "Deseja sair do mud?, note que se você não   desconectar antes do jogo seu personagem ainda poderá está ativo.", "Sair do Mud", wx.OK | wx.CANCEL | wx.ICON_QUESTION)
			if perguntaSaida.ShowModal() == wx.ID_OK:
				perguntaSaida.Destroy()
				self.janelaFechada = True
				msp.musicOff()
				cliente.enviaComando("quit")
				cliente.terminaCliente()
				self.Destroy()

				jan=dialogoEntrada()
				jan.ShowModal()
		else:
			msp.musicOff()
			self.janelaFechada = True
			cliente.terminaCliente()
			self.Destroy()
			jan=dialogoEntrada()
			jan.ShowModal()

	def teclasPressionadas(self, evento):
		if evento.GetKeyCode() == wx.WXK_ESCAPE:
			self.encerraFrame()

		else:
			evento.Skip()
	def fechaApp(self, evento):
		perguntaSaida=wx.MessageDialog(self, "Deseja sair do mud?, note que se você não   desconectar antes do jogo seu personagem ainda poderá está ativo.", "Encerrar aplicativo.", wx.OK | wx.CANCEL | wx.ICON_QUESTION)
		if perguntaSaida.ShowModal() == wx.ID_OK:
			self.janelaFechada = True
			perguntaSaida.Destroy()
			self.Destroy()
			msp.musicOff()
			cliente.terminaCliente()
			wx.Exit()
	def detectaTeclas(self, evento):
		if 32<= evento.GetUnicodeKey() <=126 and self.saidaFoco==True:
			self.entrada.SetFocus()
			self.entrada.SetValue(chr(evento.GetUnicodeKey()))
			self.entrada.SetInsertionPointEnd()
			self.saidaFoco=False
		else:
			evento.Skip()
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

		menuBar=wx.MenuBar()
		menuBar.Append(geralMenu, "&geral")
		menuBar.Append(menuPastas, "&pastas")

		self.SetMenuBar(menuBar)
	def interrompeMusica(self, evento):
		msp.musicOff()
	def abrirGeral(self, evento):
		subprocess.Popen(f"explorer {self.pastaGeral}")

	def abrirLogs(self, evento):
		subprocess.Popen(f"explorer {self.pastaLogs}")
	def abrirScripts(self, evento):
		subprocess.Popen(f"explorer {self.pastaScripts}")
	def abrirSons(self, evento):
		subprocess.Popen(f"explorer {self.pastaSons}")
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
		cliente.terminaCliente()
		self.saida.Clear()
		self.comandos.clear()
		self.mud.reiniciaFilas()
		cliente.conectaServidor(endereco, porta)
		Thread(target=self.mud.mostraMud).start()
		if self.login:
			cliente.enviaComando(self.nome)
			cliente.enviaComando(self.senha)
	def perguntaReconexao(self):
		if not self.janelaFechada:
			dlg = wx.MessageDialog(self, 'Deseja se reconectar?', 'Conexão finalizada', wx.YES_NO|wx.ICON_QUESTION)
			if dlg.ShowModal() == wx.ID_YES:
				dlg.Destroy()
				self.reconecta()
			else:
				dlg.Destroy()
				self.focaSaida()
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
				#if not self.fila_mensagens.empty():
				mensagem = self.fila_mensagens.get(timeout=0.1)
			except queue.Empty:
				if cliente.eof or not cliente.ativo:
					msp.musicOff()
					wx.CallAfter(self.janelaMud.perguntaReconexao)
					break

				continue
			for linha in mensagem.split("\n"):
				self.processaLinha(linha)
			if cliente.eof or not cliente.ativo:
				msp.musicOff()
				wx.CallAfter(self.janelaMud.perguntaReconexao)
				break

	def processaLinha(self, linha):
		linha = self.padraoAnsi.sub('', linha).strip()
		linha  = ''.join(c for c in linha if c.isprintable() or c in '\n\r')
		if not linha:
			return
		if linha.lower().startswith(("!!sound(", "!!music(")):
			if self.janelaMud.reproduzirSons or self.janelaMud.janelaAtivada:
				self.pegaSom(linha)
				self.pegaMusica(linha)
			return
		cliente.salvaLog(linha)
		if self.janelaMud.lerMensagens or self.janelaMud.janelaAtivada:
			fale(linha)
		if self.janelaMud.saidaFoco:
			wx.CallAfter(self.atualizaSaidaComFoco, linha)

		else:
			wx.CallAfter(self.adicionaSaida, linha)

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
		#self.janelaMud.saida.SetInsertionPointEnd()
		self.janelaMud.saida.AppendText(linha+ '\n')
		self.limitaHistorico()
		self.janelaMud.saida.ShowPosition(self.janelaMud.saida.GetInsertionPoint())

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
				pastas=gerenciaPastas()
				pastas.criaPastaGeral()
				wx.MessageBox("As configurações foram finalizadas com êxito, O aplicativo será encerrado agora. Por favor, inicie-o novamente para utilizá-lo normalmente.", "Configuração Concluída com êxito.", wx.OK | wx.ICON_INFORMATION)
				self.Destroy()
				sys.exit()
			else:
				wx.MessageBox("por favor, digite uma pasta válida.", "erro.", wx.ICON_ERROR)





app=wx.App()
if not config.config:
	mensagemBoasVindas=wx.MessageDialog(None, "essa é a primeira execução do aplicativo, por tanto algumas configurações precisarão ser feitas, mas será rapidinho!", "primeira execução.")
	mensagemBoasVindas.SetOKLabel("Vamos Lá!")
	mensagemBoasVindas.ShowModal()
	dialogo=configuracoes()
	dialogo.ShowModal()
else:
	#if config.config['gerais']['verifica-atualizacoes-automaticamente']:
		#subprocess.Popen('atualizador.exe')
	pastas=gerenciaPastas()
	dialogo=dialogoEntrada()
	dialogo.ShowModal()
app.MainLoop()
