import json
from shutil import rmtree
from path_lib import Path
class Config:
	def _init_(self):
		self.config=self.carregaJson()
	def carregaJson(self):
		try:
			with open('config.json') as arquivo:
				return json.load(arquivo)
		except:
			return False
	def atualizaJson(self, config=self.config):
		with open("config.json", "w") as arquivo:
			json.dump(config, arquivo, indent=4)
	def adicionaPersonagem(self, personagem):
		if personagem not in self.config['personagens']:
			self.config['personagens'].append(personagem)
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
        self.pasta = config.config['gerais']['diretorio-de-dados']
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
    pasta_sons = None  # Inicialize com um valor padrão
    if not pastaMud.exists():
        pastaMud.mkdir()
        pasta_sons = (pastaMud / "sons").mkdir()
        (pastaMud / "scripts").mkdir()
    pastaPersonagem = pastaMud / personagem

    listaDePastas = ['logs', 'scripts', 'sons']
    if not criaSons:
        listaDePastas.remove('sons')
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
        pastaPersonagem = Path(self.pasta) / "clientmud" / "muds" / personagem
        if pastaPersonagem.exists():
            rmtree(pastaPersonagem)
class personagens
	def __init__(self):
		self.pastas=gerenciaPastas()
		self.config=Config()
	def criaPersonagem(self, **kwargs):
		pasta, logs, scripts, pastaSons = self.pastas.criaPastaPersonagem(kwargs.get('pasta'), kwargs.get('nome'), kwargs.get('sons'))
		self.config.adicionaPersonagem(kwargs.get('nome'))
		dic = {'pasta': pasta, 'logs': logs, 'scripts': scripts, 'sons': pastaSons, 'nome': kwargs.get('nome'), 'senha': kwargs.get('senha'), 'endereço': kwargs.get('endereco'), 'porta': kwargs.get('porta'), 'cria pasta de sons': kwargs.get('sons'), 'login automático': kwargs.get('login')}

		with open(self.pastaPersonagem / f"{kwargs.get('nome')}.json", "w") as arquivo:
			json.dump(dic, arquivo, indent=4, ensure_ascii=False)