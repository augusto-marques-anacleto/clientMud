#*-*coding:latin-1-*-

import wx, cliente, msp, re, sys, os, glob
from time import sleep
msp=msp.Msp()
cliente=cliente.Cliente()
from accessible_output2 import outputs
import accessible_output2
saida=accessible_output2.outputs.auto.Auto()
fale=saida.speak

from threading import Thread

class dialogoEntrada(wx.Dialog):
	def __init__(self):
		wx.Dialog.__init__(self, parent=None, title="conex�o")
		global painel
		painel=wx.Panel(self)
		endereco=wx.StaticText(painel, label="&endere�o:")
		self.endereco=wx.TextCtrl(painel)
		porta=wx.StaticText(painel, label="&porta:")
		self.porta = wx.SpinCtrl(painel, min=1, max=65535)
		btnConecta = wx.Button(painel, wx.ID_OK, label="C&onectar")
		btnConecta.Bind(wx.EVT_BUTTON, self.confirma)
		btnCancela=wx.Button(painel, wx.ID_CANCEL, label="&cancelar")
		btnCancela.Bind(wx.EVT_BUTTON, self.cancela)
		btnConexoesRegistradas=wx.Button(painel, label="Conex�es &registradas")
		btnConexoesRegistradas.Bind(wx.EVT_BUTTON, conexoesRegistradas)

		self.ShowModal()
	def confirma(self, evento):
		fale("Conectando, por favor, aguarde.")
		if self.endereco.GetValue()=="":
			wx.MessageBox("Por favor, preencha o campo de endere�o.", "erro")
			self.endereco.SetFocus()
		elif self.porta.GetValue()==1:
			wx.MessageBox("por favor, preencha o campo da porta.", "erro")
			self.porta.SetFocus()
		elif cliente.conectaServidor(self.endereco.GetValue(), self.porta.GetValue()) == "":
			mud=janelaMud(self.endereco.GetValue())
			self.Destroy()
		else:
			wx.MessageBox("N�o foi poss�vel realizar a conex�o, por favor verifique sua conex�o e se o endere�o e porta est�o corretos.", "Erro de conex�o", wx.OK|wx.ICON_ERROR)
	def cancela(self, evento):
		self.Destroy
		sys.exit()
class janelaMud(wx.Frame):
	def __init__(self, endereco):
		wx.Frame.__init__(self, parent=None, title=endereco+" Cliente mud.")
		painel=wx.Panel(self)
		self.menuBar()
		self.mud=Mud(self)
		threadMensagens=Thread(target=self.mud.mostraMud)
		threadMensagens.start()
		self.saidaFoco=False
		self.Bind(wx.EVT_CLOSE, self.fechaApp)
		self.Bind(wx.EVT_CHAR_HOOK, self.teclasPrecionadas)
		self.comandos=[]
		self.indexComandos=0
		self.rotuloEntrada=wx.StaticText(painel, label="entrada")
		self.entrada=wx.TextCtrl(painel, style=wx.TE_PROCESS_ENTER)
		self.entrada.Bind(wx.EVT_CHAR_HOOK, self.enviaTexto)
		self.rotuloSaida=wx.StaticText(painel, label="sa�da")
		self.saida=wx.TextCtrl(painel, style=wx.TE_READONLY|wx.TE_MULTILINE)
		self.saida.Bind(wx.EVT_SET_FOCUS, self.ganhaFoco)
		self.saida.Bind(wx.EVT_KILL_FOCUS, self.perdeFoco)
		self.saida.Bind(wx.EVT_CHAR, self.detectaTeclas)
		self.saida.SetFont(wx.Font(1, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
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
				self.indexComandos=0
			else: cliente.enviaComando(self.texto)
		elif evento.GetKeyCode() == wx.WXK_RETURN:
			cliente.enviaComando(self.entrada.GetValue())
			self.texto=self.entrada.GetValue()
			self.adicionaComandoLista(self.texto)
			self.indexComandos=0
			self.entrada.Clear()
		elif evento.GetKeyCode() == wx.WXK_UP:
			self.navegaComandos(-1)
		elif evento.GetKeyCode() == wx.WXK_DOWN:
			self.navegaComandos(1)

		else:
			evento.Skip()
	def navegaComandos(self, posicao):
		if posicao ==-1 and len(self.comandos) >0:
			if self.indexComandos > -len(self.comandos):
				self.indexComandos+=posicao
		elif posicao ==1 and len(self.comandos) >0:
			if self.indexComandos <0:
				self.indexComandos+=posicao
			elif self.indexComandos == 0:
				self.entrada.Clear()

		if self.indexComandos >= -len(self.comandos) and self.indexComandos < 0:
			self.entrada.SetValue(self.comandos[self.indexComandos])

	def adicionaComandoLista(self, comando):
		if len(self.comandos) >=99:
			self.comandos.remove(self.comandos[0])
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
		perguntaSaida=wx.MessageDialog(self, "Deseja sair do mud?, note que se voc� n�o   desconectar antes do jogo seu personagem ainda poder� est� ativo.", "Sair do Mud", wx.OK | wx.CANCEL | wx.ICON_QUESTION)
		if perguntaSaida.ShowModal() == wx.ID_OK:

			msp.musicOff()
			cliente.enviaComando("quit")
			cliente.terminaCliente()
			self.Destroy()
			jan=dialogoEntrada()
	def teclasPrecionadas(self, evento):
		if evento.GetKeyCode() == wx.WXK_ESCAPE:
			self.encerraFrame()

		else:
			evento.Skip()
	def fechaApp(self, evento):
		perguntaSaida=wx.MessageDialog(self, "Deseja sair do mud?, note que se voc� n�o   desconectar antes do jogo seu personagem ainda poder� est� ativo.", "Encerrar aplicativo.", wx.OK | wx.CANCEL | wx.ICON_QUESTION)
		#perguntaSaida.SetCancelLabel("Cancelar")
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
		interrompeMusica=geralMenu.Append(-1, "&Interromper m�sica em reprodu��o\tCtrl-M", "Interrompe a m�sica de fundo, cujo o mud solicitou para reproduzir.")
		self.Bind(wx.EVT_MENU, self.interrompeMusica, interrompeMusica)
		geralMenu.AppendSeparator()
		encerraPrograma=geralMenu.Append(wx.ID_EXIT, "&Sair.")
		self.Bind(wx.EVT_MENU, self.fechaApp, encerraPrograma)

		menuBar=wx.MenuBar()
		menuBar.Append(geralMenu, "&geral")
		self.SetMenuBar(menuBar)
	def interrompeMusica(self, evento):
		msp.musicOff()
class Mud:
	def __init__(self, janelaMud):
		self.janelaMud=janelaMud
		self.padraoSom=re.compile(r"!!SOUND\(([^\s\\/!]+)\s*V?=?(\d+)?\)", re.IGNORECASE)
		self.padraoMusica=re.compile(r"!!MUSIC\(([^\s!\\/]+)\s*V?=?(\d+)?\s*L?=?(-?\d+)?\)", re.IGNORECASE)
		self.padraoTotal=re.compile(r"!!\w+\([^)]*\)")
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

				if linha.lower().startswith("!!sound(") or linha.lower().startswith("!!music("):

					self.pegaSom(linha)
					self.pegaMusica(linha)

				elif linha and linha != "\n":
					linha=linha.strip()
					if linha != "": fale(linha)
					if self.janelaMud.saidaFoco:

						posicao=self.janelaMud.saida.GetInsertionPoint()
						cliente.salvaLog(linha)
						self.janelaMud.saida.AppendText(linha)

						if linha: self.janelaMud.saida.AppendText("\n")

						self.janelaMud.saida.SetInsertionPoint(posicao)
					else:
						self.janelaMud.saida.AppendText(linha)
						cliente.salvaLog(linha)

						if linha: self.janelaMud.saida.AppendText("\n")

def conexoesRegistradas(evento=None):
	if not os.path.isdir("conex�es registradas"):
		fale("Pasta de conex�es registradas inesistente.")
		return
	global dialogoConexoesRegistradas
	dialogoConexoesRegistradas=wx.Dialog(None, title="Conex�es salvas")
	textoListaConexoesRegistradas=wx.StaticText(dialogoConexoesRegistradas, label="&Lista de conex�es registradas")
	listaConexoesRegistradas=wx.ListCtrl(dialogoConexoesRegistradas, size=(300,200), style=wx.LC_REPORT)
	listaConexoesRegistradas.InsertColumn(0, "Lista de conex�es registradas", width=250)
	listaConexoesRegistradas.Bind(wx.EVT_LIST_ITEM_ACTIVATED, conectaConexaoSelecionada)
	arquivosConexoesRegistradas=glob.glob(os.path.join("conex�es registradas", "*.txt"))
	nomesConexoesRegistradas=[]
	for arquivoConexaoRegistrada in arquivosConexoesRegistradas:
		if os.path.getsize(arquivoConexaoRegistrada)>0:
			nomesConexoesRegistradas.append(os.path.basename(arquivoConexaoRegistrada[:-4]))
		else:
			fale("Arquivo est� vazio, por isso foi desconsiderado da lista.")
	for nomeConexaoRegistrada in nomesConexoesRegistradas:
		listaConexoesRegistradas.Append((nomeConexaoRegistrada,))
	conectarConexaoRegistrada=wx.Button(dialogoConexoesRegistradas, label="C&onectar")
	conectarConexaoRegistrada.Bind(wx.EVT_BUTTON, conectaConexaoSelecionada)
	cancelarConexoesRegistradas=wx.Button(dialogoConexoesRegistradas, label="&Cancelar")
	cancelarConexoesRegistradas.Bind(wx.EVT_BUTTON, cancelaSelecaoConexoesRegistradas)
	dialogoConexoesRegistradas.ShowModal()
def conectaConexaoSelecionada(evento):
	pass
def cancelaSelecaoConexoesRegistradas(evento):
	dialogoConexoesRegistradas.Destroy()
app=wx.App()
dialogo=dialogoEntrada()
app.MainLoop()
