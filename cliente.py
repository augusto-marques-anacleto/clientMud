#*-*coding:latin-1-*-
import os, sys, socket
from pathlib import Path
from datetime import datetime
class Cliente(socket.socket):
	def __init__(self):
		self.ativo=False
		self.pastaLogs=self.getCurrentPath() / "logs"
		if not self.pastaLogs.exists():
			self.pastaLogs.mkdir()
	def getCurrentPath(self):
		if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
			return Path(sys.executable).parent
		else:
			return Path(os.getcwd())


	def enviaComando(self, comando):
		try:
			self.send(f'{comando}\n'.encode('latin-1'))
			self.salvaLog(comando)
		except OSError:
			return "não foi possível enviar o comando."
	def conectaServidor(self, endereco, porta):
		try:
			super().__init__(socket.AF_INET, socket.SOCK_STREAM)
			self.settimeout(3.0)
			self.connect((endereco, porta))
			self.settimeout(None)
			log=datetime.now().strftime(f"{endereco} %Hh%Mmin %d.%m.%Y.txt")
			self.log=self.pastaLogs / log
			self.ativo=True
		except (socket.gaierror, socket.timeout):
			return "erro de conexão:\nNão foi possível se conectar com o servidor, por favor verifique se você digitou o endereço ou porta corretamente e se está conectado a internet."
		else:
			return ""
	def recebeMensagem(self):
		try:
			mensagem=self.recv(2048).decode('LATIN-1')
			if mensagem != None:
				return mensagem
		except:
			self.ativo=False

	def terminaCliente(self):
		self.ativo=False
		self.close()
	def salvaLog(self, log):
		with self.log.open(mode="a+") as arquivo:
			if log: arquivo.write(f'{log}\n')
