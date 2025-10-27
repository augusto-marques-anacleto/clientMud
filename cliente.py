from telnetlib import Telnet
from pathlib import Path
from time import sleep
from datetime import datetime
class Cliente(Telnet):
	def __init__(self):
		self.ativo = False
	def enviaComando(self, comando):
		try:
			self.write(f'{comando}\r\n')
			self.salvaLog(comando)
		except:
			self.close()
	def conectaServidor(self, endereco, porta):
		if self.nome==None:
			self.nome=endereco
		try:
			super().__init__(endereco, porta)
			self.connect_timeout = 3.0
			self.ativo=True
		except:
			return False
		else:
			log=datetime.now().strftime(f"{self.nome} %Hh %Mmin %d.%m.%Y.txt")
			self.log=self.pastaLog / log
			self.endereco = endereco
			self.porta = porta
			return True
	def recebeMensagem(self):
		try:
			mensagem = self.read_very_eager()
			if mensagem:
				return mensagem
			else:
				return mensagem
		except:
			self.ativo=False
			self.eof = True
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