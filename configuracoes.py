import json
from shutil import rmtree
from pathlib import Path
from log import gravaErro
class Config:
        def __init__(self):
                self.config=self.carregaJson()
        def carregaJson(self):
                try:
                        with open('config.json') as arquivo:
                                self.config= json.load(arquivo)
                                return self.config
                except (FileNotFoundError, json.JSONDecodeError):
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
                        return True
                return False
        def removePersonagem(self, personagem):
                if personagem in self.config['personagens']:
                        self.config['personagens'].remove(personagem)
                        del self.config['gerais']['pastas-dos-muds'][personagem]
                        self.atualizaJson()
                        return True
                return False
        def atualizaConfigsConexaoManual(self, triggers, timers, keys):
                if triggers or timers or keys:
                        with open("config.json", "r") as arquivo:
                                jsonConfig = json.load(arquivo)
                                jsonConfig['configuracoes-conexoes-manuais'] = {}
                                if triggers:
                                        jsonConfig['configuracoes-conexoes-manuais']['triggers'] = triggers
                                if timers:
                                        jsonConfig['configuracoes-conexoes-manuais']['timers'] = timers
                                if keys:
                                        jsonConfig['configuracoes-conexoes-manuais']['keys'] = keys
                        with open("config.json", "w") as arquivo:
                                json.dump(jsonConfig, arquivo, indent=4, ensure_ascii=False)

class gerenciaPastas:
        def __init__(self, config):
                self.config = config
                if self.config.config: self.pasta = self.config.config.get('gerais', {}).get('diretorio-de-dados')
                else: self.pasta = None
        def criaPastaGeral(self):
                if self.config and not self.pasta: self.pasta = self.config.config.get('gerais', {}).get('diretorio-de-dados')
                pastaGeral = Path(self.pasta) / "clientmud"
                pastaMuds = pastaGeral / "muds"
                if not pastaGeral.exists():
                        pastaGeral.mkdir(parents=True)
                        (pastaGeral / "logs").mkdir(parents = True, exist_ok=True)
                        (pastaGeral / "scripts").mkdir(parents = True, exist_ok=True)
                        (pastaGeral / "sons").mkdir(parents=True, exist_ok=True)
                        pastaMuds.mkdir(parents = True, exist_ok=True)
        def criaPastasPersonagem(self, pasta_personagem, pasta_sons_mud):
                pasta_personagem = Path(pasta_personagem)
                (pasta_personagem / "logs").mkdir(parents=True, exist_ok=True)
                (pasta_personagem / "scripts").mkdir(parents=True, exist_ok=True)
                Path(pasta_sons_mud).mkdir(parents=True, exist_ok=True)

        def removePastaPersonagem(self, personagem):
                pastaPersonagem = Path(self.config.config['gerais']['pastas-dos-muds'][personagem])
                if pastaPersonagem.exists():
                        rmtree(pastaPersonagem)
        def obtemCaminhoArquivoPersonagem(self, personagem):
                pasta_base_str = self.config.config['gerais']['pastas-dos-muds'].get(personagem)
                if not pasta_base_str: return None
                return Path(pasta_base_str) / f'{personagem}.json'

class gerenciaPersonagens:
        def __init__(self, config=None, gerencia_pastas = None):
                self.config = config
                self.pastas=gerencia_pastas
        def criaPersonagem(self, **kwargs):
                nome = kwargs.get('nome')
                pastaPersonagem = str(kwargs.get('pasta'))
                pastaSons =str(kwargs.get('pastaSons'))
                self.pastas.criaPastasPersonagem(pastaPersonagem, pastaSons)
                self.config.adicionaPersonagem(nome,pastaPersonagem)
                dic ={
                        'nome': nome,
                        'senha': kwargs.get('senha'),
                        'endereço': kwargs.get('endereço'),
                        'porta': kwargs.get('porta'),
                        'login_automático': kwargs.get('login_automático'),
                        'reproduzir_sons_fora_janela': kwargs.get('reproduzir_sons_fora_janela'),
                        'ler_fora_janela': kwargs.get('ler_fora_janela'),
                        'triggers': [],
                        'timers': [],
                        'keys': []
                }
                caminho_arquivo = Path(pastaPersonagem) / f'{nome}.json'
                if not caminho_arquivo: return False
                try:
                        with open(caminho_arquivo, "w") as arquivo:
                                json.dump(dic, arquivo, indent=4, ensure_ascii=False)
                        return True
                except IOError as e:
                        gravaErro(e)
                        return False

        def carregaPersonagem(self, personagem):
                caminho_personagem = self.pastas.obtemCaminhoArquivoPersonagem(personagem)
                if not caminho_personagem or not caminho_personagem.exists(): return None
                try:
                        with open(caminho_personagem) as arquivo:
                                dados_personagem = json.load(arquivo)
                        return dados_personagem
                except (json.JSONDecodeError, IOError):
                        return None
        def removePersonagem(self, personagem):
                self.pastas.removePastaPersonagem(personagem)
                self.config.removePersonagem(personagem)
        def atualizaPersonagem(self, nome, dic):
                caminho_arquivo = self.pastas.obtemCaminhoArquivoPersonagem(nome)
                if not caminho_arquivo: return False
                with open(caminho_arquivo, "w") as arquivo:
                        json.dump(dic, arquivo, indent=4, ensure_ascii=False)
                        return True
