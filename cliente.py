import socket
from pathlib import Path
from datetime import datetime
class Cliente(socket.socket):
	def __init__(self):
		self.ativo=False


	def enviaComando(self, comando):
		try:
			self.send(f'{comando}\n'.encode('latin-1'))
			self.salvaLog(comando)
		except OSError:
			self.ativo=False
			self.close()
	def conectaServidor(self, endereco, porta):
		if self.nome==None:
			self.nome=endereco
		try:
			super().__init__(socket.AF_INET, socket.SOCK_STREAM)
			self.settimeout(3.0)
			self.connect((endereco, porta))
			self.settimeout(None)
			log=datetime.now().strftime(f"{self.nome} %Hh %Mmin %d.%m.%Y.txt")
			self.log=self.pastaLog / log
			self.ativo=True
		except (socket.gaierror, socket.timeout):
			return "erro de conexão:\nNão foi possível se conectar com o servidor, por favor verifique se você digitou o endereço ou porta corretamente e se está conectado a internet."
		else:
			return ""
	def recebeMensagem(self):
		try:
			mensagem=self.recv(2048).decode('LATIN-1')
			if mensagem != "":
				self.salvaLog(mensagem)
				return mensagem
			else:
				self.ativo=False
				self.close()
				return "conexão finalizada."
		except:
			self.ativo=False
			self.close()

	def definePastaLog(self, pastaLog, nome=None):
		self.nome = nome
		self.pastaLog= Path(pastaLog)
	def terminaCliente(self):
		self.ativo=False
		self.close()
	def salvaLog(self, log):
		with self.log.open(mode="a+") as arquivo:
			if log: arquivo.write(f'{log}\n')