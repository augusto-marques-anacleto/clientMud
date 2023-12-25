import json
from shutil import rmtree
from pathlib import Path
class Config:
	def __init__(self):
		self.config=self.carregaJson()
	def carregaJson(self):
		try:
			with open('config.json') as arquivo:
				return json.load(arquivo)
		except:
			return  False
	def atualizaJson(self, config=None):
		if self.config:
			config=self.config
		with open("config.json", "w") as arquivo:
			json.dump(config, arquivo, indent=4, ensure_ascii=False)
	def adicionaPersonagem(self, personagem, pasta):
		if personagem not in self.config['personagens']:
			self.config['personagens'].append(personagem)
			self.config['gerais']['pastas-dos-muds'][personagem]=pasta

			self.atualizaJson()
		else:
			return False
	def removePersonagem(self, personagem):
		if personagem in self.config['personagens']:
			self.config['personagens'].remove(personagem)
			self.atualizaJson()
		else:
			return False
class gerenciaPastas:
	def __init__(self):
		if Config().config:
			self.pasta = Config().config['gerais']['diretorio-de-dados']
	def criaPastaGeral(self):
		pastaGeral = Path(self.pasta) / "clientmud"
		pastaMuds = pastaGeral / "muds"
		if not pastaGeral.exists():
			pastaGeral.mkdir(parents=True)
			(pastaGeral / "sons").mkdir()
			(pastaGeral / "logs").mkdir()
		if not pastaMuds.exists():
			pastaMuds.mkdir()
	def criaPastaPersonagem(self, pastaMud, personagem, criaSons):
		pastaMuds = Path(self.pasta) / "clientmud" / "muds"
		if not pastaMuds.exists():
			pastaMuds.mkdir(parents=True)
		pastaMud = Path(pastaMuds / pastaMud)
		pasta_sons=pastaMud / 'sons'

		if not pastaMud.exists():
			pastaMud.mkdir()
			(pastaMud / "scripts").mkdir()
		pastaPersonagem = pastaMud / personagem

		listaDePastas = ['logs', 'scripts', 'sons']
		if not criaSons:
			listaDePastas.remove('sons')
			if not pasta_sons.exists():

				pasta_sons.mkdir()
		if not pastaPersonagem.exists():
			pastaPersonagem.mkdir()
			for pasta in listaDePastas:
				(pastaPersonagem / pasta).mkdir()
		if criaSons:
			pasta_sons = pastaPersonagem / 'sons'
		pastaLogs = pastaPersonagem / 'logs'
		pastaScripts = pastaPersonagem / 'scripts'
		return pastaPersonagem, pastaLogs, pastaScripts, pasta_sons
	def removePastaPersonagem(self, personagem):
		pastaPersonagem = Path(self.pasta) / "clientmud" / "muds" /Config().config['gerais']['pastas-dos-muds'][personagem]/ personagem 
		if pastaPersonagem.exists():
			rmtree(str(pastaPersonagem))
	def obtemPastaPersonagem(self, pasta, personagem):
		return Path(self.pasta) / "clientmud" / "muds" /pasta/ personagem / f"{personagem}.json"

class gerenciaPersonagens:
	def __init__(self):
		self.config=Config()
		self.pastas=gerenciaPastas()
	def criaPersonagem(self, **kwargs):
		self.pastaPersonagem, logs, scripts, pastaSons = self.pastas.criaPastaPersonagem(kwargs.get('pasta'), kwargs.get('nome'), kwargs.get('sons'))
		self.config.adicionaPersonagem(kwargs.get('nome'), kwargs.get('pasta'))
		self.config.atualizaJson()
		dic = {'pasta': kwargs.get('pasta'), 'logs': str(logs), 'scripts': str(scripts), 'sons': str(pastaSons), 'nome': kwargs.get('nome'), 'senha': kwargs.get('senha'), 'endereço': kwargs.get('endereco'), 'porta': kwargs.get('porta'), 'cria pasta de sons': kwargs.get('sons'), 'login automático': kwargs.get('login')}

		with open(self.pastaPersonagem / f"{kwargs.get('nome')}.json", "w") as arquivo:
			json.dump(dic, arquivo, indent=4, ensure_ascii=False)
	def carregaPersonagem(self, personagem):
		caminho_personagem = self.pastas.obtemPastaPersonagem(self.config.config['gerais']['pastas-dos-muds'][personagem], personagem)
		with open(caminho_personagem) as arquivo:
			dados_personagem = json.load(arquivo)
		return dados_personagem
	def removePersonagem(self, personagem):
		self.config.removePersonagem(personagem)
		self.pastas.removePastaPersonagem(personagem)
		del self.config.config['gerais']['pastas-dos-muds'][personagem]
		self.config.atualizaJson()
	def carregaClasse(self):
		self.config=Config()
		self.pastas=gerenciaPastas()
