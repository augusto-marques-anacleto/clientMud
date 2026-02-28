import json
from shutil import rmtree
from pathlib import Path
from core.log import gravaErro

class Config:
    def __init__(self):
        self.config = self.carregaJson()

    def carregaJson(self):
        try:
            with open('config.json', 'r', encoding='utf-8') as arquivo:
                self.config = json.load(arquivo)
                return self.config
        except (FileNotFoundError, json.JSONDecodeError):
            return False

    def atualizaJson(self, config=None):
        if self.config:
            config = self.config
        with open("config.json", "w", encoding='utf-8') as arquivo:
            json.dump(config, arquivo, indent=4, ensure_ascii=False)
            self.config = config

    def adicionaPersonagem(self, personagem, pasta):
        if personagem not in self.config['personagens']:
            self.config['personagens'].append(personagem)
            self.config['gerais']['pastas-dos-muds'][personagem] = pasta
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
            self.carregaJson()
            if 'configuracoes-conexoes-manuais' not in self.config:
                self.config['configuracoes-conexoes-manuais'] = {}
            
            self.config['configuracoes-conexoes-manuais']['triggers'] = triggers
            self.config['configuracoes-conexoes-manuais']['timers'] = timers
            self.config['configuracoes-conexoes-manuais']['keys'] = keys
            self.atualizaJson()

    def carregaGlobalConfig(self):
        self.carregaJson()
        return self.config.get('configuracoes-globais', {})

    def salvaGlobalConfig(self, triggers, timers, keys):
        self.carregaJson()
        self.config['configuracoes-globais'] = {
            'triggers': triggers,
            'timers': timers,
            'keys': keys
        }
        self.atualizaJson()

    def carregaMudConfig(self, nome_mud):
        pasta_mud = Path(self.config['gerais']['diretorio-de-dados']) / "clientmud" / "muds" / nome_mud
        arquivo_mud = pasta_mud / "mud.json"
        if arquivo_mud.exists():
            try:
                with open(arquivo_mud, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def salvaMudConfig(self, nome_mud, triggers, timers, keys):
        pasta_mud = Path(self.config['gerais']['diretorio-de-dados']) / "clientmud" / "muds" / nome_mud
        if not pasta_mud.exists():
            return False
        arquivo_mud = pasta_mud / "mud.json"
        dados = {
            'triggers': triggers,
            'timers': timers,
            'keys': keys
        }
        try:
            with open(arquivo_mud, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=4, ensure_ascii=False)
            return True
        except:
            return False

class GerenciaPastas:
    def __init__(self, config_obj):
        self.config = config_obj
        if self.config.config: 
            self.pasta = self.config.config.get('gerais', {}).get('diretorio-de-dados')
        else: 
            self.pasta = None

    def criaPastaGeral(self):
        if self.config and not self.pasta: 
            self.pasta = self.config.config.get('gerais', {}).get('diretorio-de-dados')
        
        pastaGeral = Path(self.pasta) / "clientmud"
        pastaMuds = pastaGeral / "muds"
        if not pastaGeral.exists():
            pastaGeral.mkdir(parents=True)
            (pastaGeral / "logs").mkdir(parents=True, exist_ok=True)
            (pastaGeral / "scripts").mkdir(parents=True, exist_ok=True)
            (pastaGeral / "sons").mkdir(parents=True, exist_ok=True)
            pastaMuds.mkdir(parents=True, exist_ok=True)

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

class GerenciaPersonagens:
    def __init__(self, config_obj=None, gerencia_pastas=None):
        self.config = config_obj
        self.pastas = gerencia_pastas

    def criaPersonagem(self, **kwargs):
        nome = kwargs.get('nome')
        pastaPersonagem = str(kwargs.pop('pasta', ''))
        pastaSons = str(kwargs.pop('pastaSons', ''))
        self.pastas.criaPastasPersonagem(pastaPersonagem, pastaSons)
        self.config.adicionaPersonagem(nome, pastaPersonagem)
        
        dic = {
            'triggers': [],
            'timers': [],
            'keys': []
        }
        dic.update(kwargs)
        
        caminho_arquivo = Path(pastaPersonagem) / f'{nome}.json'
        try:
            with open(caminho_arquivo, "w", encoding='utf-8') as arquivo:
                json.dump(dic, arquivo, indent=4, ensure_ascii=False)
            return True
        except IOError as e:
            gravaErro(e)
            return False

    def carregaPersonagem(self, personagem):
        caminho_personagem = self.pastas.obtemCaminhoArquivoPersonagem(personagem)
        if not caminho_personagem or not caminho_personagem.exists(): 
            return None
            
        pasta_base_personagem = caminho_personagem.parent
        pasta_sons = pasta_base_personagem.parent / 'sons'
        self.pastas.criaPastasPersonagem(str(pasta_base_personagem), str(pasta_sons))
        
        try:
            with open(caminho_personagem, encoding='utf-8') as arquivo:
                dados_personagem = json.load(arquivo)
            return dados_personagem
        except UnicodeDecodeError:
            try:
                with open(caminho_personagem, encoding='cp1252') as arquivo:
                    dados_personagem = json.load(arquivo)
                with open(caminho_personagem, "w", encoding='utf-8') as arquivo_novo:
                    json.dump(dados_personagem, arquivo_novo, indent=4, ensure_ascii=False)
                return dados_personagem
            except (json.JSONDecodeError, IOError):
                return None
        except (json.JSONDecodeError, IOError):
            return None

    def renomeiaPersonagem(self, nome_antigo, nome_novo):
        caminho_antigo = self.pastas.obtemCaminhoArquivoPersonagem(nome_antigo)
        if not caminho_antigo or not caminho_antigo.exists(): return False
        
        pasta_antiga = caminho_antigo.parent
        pasta_nova = pasta_antiga.parent / nome_novo
        
        try:
            pasta_antiga.rename(pasta_nova)
            
            arquivo_json_antigo = pasta_nova / f"{nome_antigo}.json"
            arquivo_json_novo = pasta_nova / f"{nome_novo}.json"
            if arquivo_json_antigo.exists():
                arquivo_json_antigo.rename(arquivo_json_novo)
            
            if nome_antigo in self.config.config['personagens']:
                idx = self.config.config['personagens'].index(nome_antigo)
                self.config.config['personagens'][idx] = nome_novo
            
            if nome_antigo in self.config.config['gerais']['pastas-dos-muds']:
                del self.config.config['gerais']['pastas-dos-muds'][nome_antigo]
            self.config.config['gerais']['pastas-dos-muds'][nome_novo] = str(pasta_nova)
            
            self.config.atualizaJson()
            return True
        except Exception as e:
            gravaErro(e)
            return False

    def removePersonagem(self, personagem):
        self.pastas.removePastaPersonagem(personagem)
        self.config.removePersonagem(personagem)

    def atualizaPersonagem(self, nome, dic):
        caminho_arquivo = self.pastas.obtemCaminhoArquivoPersonagem(nome)
        if not caminho_arquivo: return False
        with open(caminho_arquivo, "w", encoding='utf-8') as arquivo:
            json.dump(dic, arquivo, indent=4, ensure_ascii=False)
            return True