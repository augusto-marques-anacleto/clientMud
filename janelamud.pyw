from  pathlib import Path
import wx,logging,  re, sys
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

# Configuração do log
logging.basicConfig(filename='erros.log', level=logging.ERROR)

def excepthook(exctype, value, traceback):
	# Registra a exceção no arquivo de log
	logging.error('Ocorreu um erro não tratado:', exc_info=(exctype, value, traceback))
	# Exibe uma caixa de mensagem com uma mensagem de erro
	mensagem = f'Ocorreu um erro não tratado:\n\n{"".join(traceback.format_exception(exctype, value, traceback))}'
	wx.MessageBox(mensagem, 'Erro', wx.ICON_ERROR | wx.OK)
	
	# Encerra o aplicativo de forma limpa
	wx.CallAfter(wx.GetApp().ExitMainLoop)

# Define a função excepthook como o tratador de exceções padrão
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
		if cliente.conectaServidor(json['endereço'], json['porta']) == "":
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
		painel=wx.Panel(self.dialogo)
		rotuloPasta=wx.StaticText(painel, label="Pasta onde vai ficar salva a pasta do personagem.")
		self.campoTextoPasta=wx.TextCtrl(painel)
		rotuloNome=wx.StaticText(painel, label='nome do personagem ou mud')
		self.campoTextoNome=wx.TextCtrl(painel)
		rotuloSenha=wx.StaticText(painel, label='senha: deixar em branco, caso não queira logar altomaticamente, ou seja um mud.')
		self.campoTextoSenha=wx.TextCtrl(painel, style=wx.TE_PASSWORD)
		rotuloEndereco=wx.StaticText(painel, label='Endereço:')
		self.campoTextoEndereco=wx.TextCtrl(painel)
		rotuloPorta=wx.StaticText(painel, label='porta:')
		self.campoPorta = wx.SpinCtrl(painel, min=1, max=65535)
		self.criaPastaSons=wx.CheckBox(painel, label='criar uma pasta de sons para o personagem/mud.')
		self.loginAutomatico=wx.CheckBox(painel, label='Logar automaticamente:')
		btnSalvar=wx.Button(painel, label='&salvar')
		btnSalvar.Bind(wx.EVT_BUTTON, self.salvaConfiguracoes)
		btnCancelar=wx.Button(painel, label='&cancelar')
		btnCancelar.Bind(wx.EVT_BUTTON, self.encerraDialogo)
		self.dialogo.ShowModal()
	def editaPersonagem(self, evento):
		self.Hide()
		self.dialogo=wx.Dialog(self, title='editar personagem')
		painel=wx.Panel(self.dialogo)
		rotuloPasta=wx.StaticText(painel, label="pasta onde vai ficar  salva a pasta do personagem.")
		self.campoTextoPasta=wx.TextCtrl(painel)
		rotuloNome=wx.StaticText(painel, label='nome do personagem ou mud')
		self.campoTextoNome=wx.TextCtrl(painel)
		rotuloSenha=wx.StaticText(painel, label='senha: deixar em branco, caso não queira logar altomaticamente, ou seja um mud.')
		self.campoTextoSenha=wx.TextCtrl(painel, style=wx.TE_PASSWORD)
		rotuloEndereco=wx.StaticText(painel, label='Endereço:')
		self.campoTextoEndereco=wx.TextCtrl(painel)
		rotuloPorta=wx.StaticText(painel, label='porta:')
		self.campoPorta = wx.SpinCtrl(painel, min=1, max=65535)
		self.criaPastaSons=wx.CheckBox(painel, label='criar uma pasta de sons para o personagem/mud.')
		self.loginAutomatico=wx.CheckBox(painel, label='Logar automaticamente:')
		btnSalvar=wx.Button(painel, label='&salvar')
		btnSalvar.Bind(wx.EVT_BUTTON, self.salvaConfiguracoes)
		btnCancelar=wx.Button(painel, label='&cancelar')
		btnCancelar.Bind(wx.EVT_BUTTON, self.encerraDialogo)
		json=personagem.carregaPersonagem(self.listaDePersonagens[self.listBox.GetSelection()])
		pasta=json['pasta']
		nome=json['nome']
		senha=json['senha']
		endereco=json['endereço']
		porta=json['porta']
		opcaoSons=json['cria pasta de sons']
		opcaoLogin=json['login automático']
		self.campoTextoPasta.SetValue(pasta)
		self.campoTextoNome.SetValue(nome)
		self.campoTextoSenha.SetValue(senha)
		self.campoTextoEndereco.SetValue(endereco)
		self.campoPorta.SetValue(porta)
		self.criaPastaSons.SetValue(opcaoSons)
		self.loginAutomatico.SetValue(opcaoLogin)
		self.dialogo.ShowModal()
	def salvaConfiguracoes(self, evento):
		pasta=self.campoTextoPasta.GetValue()
		nome=self.campoTextoNome.GetValue()
		senha=self.campoTextoSenha.GetValue()
		endereco=self.campoTextoEndereco.GetValue()
		porta=self.campoPorta.GetValue()
		sons=self.criaPastaSons.GetValue()
		login=self.loginAutomatico.GetValue()
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
			personagem.criaPersonagem(pasta = pasta, nome = nome, endereco = endereco, porta = porta, senha = senha, sons = sons, login = login)
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
		cliente.definePastaLog(Path(config.config['gerais']['diretorio-de-dados'], 'clientmud', 'logs'))
		msp.definePastaSons(Path(config.config['gerais']['diretorio-de-dados'], 'clientmud', 'sons'))
		if self.endereco.GetValue()=="":
			wx.MessageBox("Por favor, preencha o campo de endereço.", "erro")
			self.endereco.SetFocus()
		elif self.porta.GetValue()==1:
			wx.MessageBox("por favor, preencha o campo da porta.", "erro")
			self.porta.SetFocus()
		elif cliente.conectaServidor(self.endereco.GetValue(), self.porta.GetValue()) == "":
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

		self.menuBar()
		self.mud=Mud(self)
		threadMensagens=Thread(target=self.mud.mostraMud)
		threadMensagens.start()
		self.saidaFoco=False
		self.pastaGeral=f"{config.config['gerais']['diretorio-de-dados']}\\clientmud"
		if json:

			self.pastaLogs = json['logs']
			self.pastaScripts = json['scripts']
			self.pastaSons=json['sons']
		else:
			self.pastaLogs=str(Path(config.config['gerais']['diretorio-de-dados'], 'clientmud', 'logs'))
			self.pastaScripts=str(Path(config.config['gerais']['diretorio-de-dados'], 'clientmud', 'scripts'))
			self.pastaSons=str(Path(config.config['gerais']['diretorio-de-dados'], 'clientmud', 'sons'))

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
	def enviaTexto(self, evento):
		if evento.GetKeyCode() == wx.WXK_RETURN and evento.GetModifiers() == wx.MOD_CONTROL:
			self.entrada.SetValue(self.entrada.GetValue()+"\n")
			self.entrada.SetInsertionPointEnd()
		elif evento.GetKeyCode() == wx.WXK_RETURN and evento.GetModifiers() == wx.MOD_SHIFT:
			if self.entrada.GetValue() != "":
				cliente.enviaComando(self.entrada.GetValue())
				self.texto=self.entrada.GetValue()
				self.adicionaComandoLista(self.texto)
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
		self.entrada.Clear()
		evento.Skip()
	def encerraFrame(self):
		if cliente.ativo==True:
			perguntaSaida=wx.MessageDialog(self, "Deseja sair do mud?, note que se você não   desconectar antes do jogo seu personagem ainda poderá está ativo.", "Sair do Mud", wx.OK | wx.CANCEL | wx.ICON_QUESTION)
			if perguntaSaida.ShowModal() == wx.ID_OK:

				msp.musicOff()
				cliente.enviaComando("quit")
				cliente.terminaCliente()
				self.Destroy()

				jan=dialogoEntrada()
				jan.ShowModal()
		else:
			msp.musicOff()
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
			msp.musicOff()
			cliente.close()
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
		from subprocess import Popen
		Popen(f"explorer {self.pastaGeral}")

	def abrirLogs(self, evento):
		from subprocess import Popen
		Popen(f"explorer {self.pastaLogs}")
	def abrirScripts(self, evento):
		from subprocess import Popen
		Popen(f"explorer {self.pastaScripts}")
	def abrirSons(self, evento):
		from subprocess import Popen
		Popen(f"explorer {self.pastaSons}")
	def focaSaida(self):
		self.saida.Unbind(wx.EVT_KILL_FOCUS, handler= self.perdeFoco)
		self.saida.Unbind(wx.EVT_SET_FOCUS, handler=self.ganhaFoco)

		self.saida.SetFocus()
		self.saidaFoco=True
		self.entrada.Destroy()
class Mud:
	def __init__(self, janelaMud):
		self.janelaMud=janelaMud
		self.padraoSom=re.compile(r"!!SOUND\(([^\s\\/!]+)\s*V?=?(\d+)?\)", re.IGNORECASE)
		self.padraoMusica=re.compile(r"!!MUSIC\(([^\s!\\/]+)\s*V?=?(\d+)?\s*L?=?(-?\d+)?\)", re.IGNORECASE)
		self.padraoTotal=re.compile(r"!!\w+\([^)]*\)")
		self.padraoAnsi = re.compile(r'\x1b\[\d+(?:;\d+)*m')
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
	def mostraMud(self):
		sleep(0.1)
		while True:
			mensagem=cliente.recebeMensagem()
			mensagem=mensagem.split('\n')
			for linha in mensagem:
				linha = self.padraoAnsi.sub('', linha)
				if linha.lower().startswith("!!sound(") or linha.lower().startswith("!!music("):

					self.pegaSom(linha)
					self.pegaMusica(linha)

				elif linha and linha != "\n":
					linha=linha.strip()
					cliente.salvaLog(linha)
					if linha != "": fale(linha)
					if self.janelaMud.saidaFoco:

						posicao=self.janelaMud.saida.GetInsertionPoint()
						self.janelaMud.saida.AppendText(linha)

						if linha: self.janelaMud.saida.AppendText("\n")

						self.janelaMud.saida.SetInsertionPoint(posicao)
					else:
						self.janelaMud.saida.AppendText(linha)

						if linha: self.janelaMud.saida.AppendText("\n")
			if cliente.ativo==False:
				self.janelaMud.focaSaida()
				msp.musicOff()
				wx.MessageBox("A conexão  foi encerrada, caso você não queira mais revisar o histórico pode voltar para a tela anterior.", "Conexão encerrada.", wx.ICON_INFORMATION)
				break

class configuracoes(wx.Dialog):
	def __init__(self):
		wx.Dialog.__init__(self, parent=None, title="Configurações")
		painel=wx.Panel(self)
		self.pastaInicial= '.'
		wx.MessageBox("nessa próxima tela, dentre algumas opções, será apresentado um campo para você colar o caminho da pasta onde quer salvar os personagens criados, bem como os sons/logs e configurações dos muds jogados.\nPor padrão a pasta que vem definida é a pasta onde está o executável do aplicativo, se não quiser colar o caminho é só criar em escolher pasta que o explorador do windows vai ser aberto.", "alerta sobre pastas.")

		rotulo=wx.StaticText(painel, label='Pasta de dados.')
		self.campoTextoPasta=wx.TextCtrl(painel)
		self.campoTextoPasta.SetValue(self.pastaInicial)
		btnEscolhePasta=wx.Button(painel, label='&escolher pasta de dados')
		btnEscolhePasta.Bind(wx.EVT_BUTTON, self.escolhePasta)
		self.reproducaoForaDaJanela = wx.CheckBox(painel, label='Reproduzir sons fora da janela do MUD')
		self.falaForaDaJanela = wx.CheckBox(painel, label='Ler as mensagens fora da janela do MUD')
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


				dic = {
					'gerais': {
						"toca-sons-fora-da-janela": som,
						'ler fora da janela': leitura,
						"ultima-conexao": [],
						"diretorio-de-dados": self.pastaInicial,
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
	pastas=gerenciaPastas()
	#personagem.carregaClasse()
	dialogo=dialogoEntrada()
	dialogo.ShowModal()
app.MainLoop()
