import os
from telnetlib import Telnet
from pathlib import Path
from time import sleep
from datetime import datetime

class Cliente(Telnet):
	def __init__(self):
		self.ativo = False
		self.arquivoLog = None

	def enviaComando(self, comando):
		try:
			self.write(f'{comando}\r\n'.encode("latin-1", errors="replace"))
			self.salvaLog(comando)
		except:
			self.terminaCliente()

	def conectaServidor(self, endereco, porta):
		if self.nome == None:
			self.nome = endereco
		try:
			super().__init__(endereco, porta, timeout=3.0)
			self.ativo = True
		except:
			return False
		else:
			log = datetime.now().strftime(f"{self.nome} %Hh %Mmin %d.%m.%Y.txt")
			self.log = self.pastaLog / log
			self.arquivoLog = self.log.open(mode="a+")
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
			self.terminaCliente()
			return None

	def definePastaLog(self, pastaLog, nome=None):
		self.nome = nome
		self.pastaLog = Path(pastaLog)

	def terminaCliente(self):
		self.ativo = False
		try:
			if self.arquivoLog and not self.arquivoLog.closed:
				self.arquivoLog.close()
		except:
			pass
		try:
			self.close()
		except:
			pass

	def salvaLog(self, log):
		if log and self.arquivoLog and not self.arquivoLog.closed:
			try:
				self.arquivoLog.write(f'{log}\n')
				self.arquivoLog.flush()
			except OSError:
				pass