import json
from shutil import rmtree
from pathlib import Path
class Config:
	def __init__(self):
		self.config=self.carregaJson()
	def carregaJson(self):
		try:
			with open('config.json') as arquivo:
				self.config= json.load(arquivo)
				return self.config
		except:
			return  False
	def atualizaJson(self, config=None):
		if self.config:
			config=self.config
		with open("config.json", "w") as arquivo:
			json.dump(config, arquivo, indent=4, ensure_ascii=False)
			self.config=config
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
		config = Config()
		self.config = config
		if self.config.config:
			self.pasta = self.config.config.get('gerais', {}).get('diretorio-de-dados')

	def criaPastaGeral(self):
		pastaGeral = Path(self.pasta) / "clientmud"
		pastaMuds = pastaGeral / "muds"
		if not pastaGeral.exists():
			pastaGeral.mkdir(parents=True)
			(pastaGeral / "logs").mkdir()
			(pastaGeral / "scripts").mkdir()
			(pastaGeral / "sons").mkdir()

		if not pastaMuds.exists():
			pastaMuds.mkdir()
	def criaPastaPersonagem(self, pastaMud, pastaLogs, pastaScripts, pastaSons):
		listaDePastas = [
			Path(pastaMud),
			Path(pastaLogs),
			Path(pastaScripts),
			Path(pastaSons)
		]
		for pasta in listaDePastas:
			if not pasta.exists():
				pasta.mkdir(parents=True)
	def removePastaPersonagem(self, personagem):
		pastaPersonagem = Path(Config().config['gerais']['pastas-dos-muds'][personagem])
		if pastaPersonagem.exists():
			rmtree(pastaPersonagem)
	def obtemPastaPersonagem(self, pasta, personagem):
		return Path(pasta) / f"{personagem}.json"

class gerenciaPersonagens:
	def __init__(self):
		self.config=Config()
		self.pastas=gerenciaPastas()
	def criaPersonagem(self, **kwargs):
		pastaPersonagem = str(kwargs.get('pasta'))
		pastaLogs = str(kwargs.get('pastaLogs'))
		pastaScripts = str(kwargs.get('pastaScripts'))
		pastaSons =str(kwargs.get('pastaSons'))
		nome = kwargs.get('nome')
		senha = kwargs.get('senha')
		endereco = kwargs.get('endereco')
		porta = kwargs.get('porta')
		login = kwargs.get('login')
		reproducao = kwargs.get('sons')
		leitura = kwargs.get('leitura')
		self.pastas.criaPastaPersonagem(pastaPersonagem, pastaLogs, pastaScripts, pastaSons)
		self.config.adicionaPersonagem(nome,pastaPersonagem)
		self.config.atualizaJson()
		dic ={
			'pasta': str(pastaPersonagem),
			'logs': str(pastaLogs),
			'scripts': str(pastaScripts),
			'sons': str(pastaSons),
			'nome': nome,
			'senha': senha,
			'endereço': endereco,
			'porta': porta,
			'login automático': login,
			'Reproduzir sons fora da janela do mud': reproducao,
			'ler fora da janela': leitura
		}

		with open(Path(pastaPersonagem) / f"{nome}.json", "w") as arquivo:
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
	def atualizaPersonagem(self, nome, dic):
		with open(self.pastaPersonagem / f"{nome}.json", "w") as arquivo:
			json.dump(dic, arquivo, indent=4, ensure_ascii=False)