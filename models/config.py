import json
from shutil import rmtree
from pathlib import Path
from core.log import gravaErro

def chave_personagem(nome, mud):
    return f"{nome}@{mud}"

def nome_de_chave(chave):
    return chave.split('@')[0] if '@' in chave else chave

def mud_de_chave(chave):
    return chave.split('@', 1)[1] if '@' in chave else ''

def display_de_chave(chave):
    if '@' not in chave:
        return chave
    nome, mud = chave.split('@', 1)
    return f"{nome} - {mud}"

def _migra_personagens(config_dict):
    if not config_dict:
        return False
    personagens = config_dict.get('personagens', [])
    pastas = config_dict.get('gerais', {}).get('pastas-dos-muds', {})
    precisa = any('@' not in p for p in personagens) or any('@' not in k for k in pastas)
    if not precisa:
        return False
    novos_personagens = []
    novos_pastas = {}
    mapa = {}
    for entrada in personagens:
        if '@' in entrada:
            novos_personagens.append(entrada)
            mapa[entrada] = entrada
        else:
            pasta_str = pastas.get(entrada, '')
            mud = Path(pasta_str).parent.name if pasta_str else ''
            nova_chave = chave_personagem(entrada, mud) if mud else entrada
            novos_personagens.append(nova_chave)
            mapa[entrada] = nova_chave
    for k, v in pastas.items():
        nova_chave = mapa.get(k)
        if nova_chave:
            novos_pastas[nova_chave] = v
        elif '@' in k:
            novos_pastas[k] = v
        else:
            mud = Path(v).parent.name if v else ''
            novos_pastas[chave_personagem(k, mud) if mud else k] = v
    config_dict['personagens'] = novos_personagens
    config_dict['gerais']['pastas-dos-muds'] = novos_pastas
    return True

def carrega_json_seguro(caminho, valor_padrao=None):
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return json.load(f)
    except UnicodeDecodeError:
        try:
            with open(caminho, 'r', encoding='latin-1') as f:
                dados = json.load(f)
            with open(caminho, 'w', encoding='utf-8') as f_novo:
                json.dump(dados, f_novo, indent=4, ensure_ascii=False)
            return dados
        except (FileNotFoundError, json.JSONDecodeError, IOError):
            return valor_padrao
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        return valor_padrao

class Config:
    def __init__(self):
        self.config = self.carregaJson()

    def carregaJson(self):
        self.config = carrega_json_seguro('config.json', False)
        if self.config and _migra_personagens(self.config):
            self.atualizaJson()
        return self.config

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

    def atualizaConfigsConexaoManual(self, triggers, timers, keys, macros):
        if triggers or timers or keys or macros:
            self.carregaJson()
            if 'configuracoes-conexoes-manuais' not in self.config:
                self.config['configuracoes-conexoes-manuais'] = {}
            
            self.config['configuracoes-conexoes-manuais']['triggers'] = triggers
            self.config['configuracoes-conexoes-manuais']['timers'] = timers
            self.config['configuracoes-conexoes-manuais']['keys'] = keys
            self.config['configuracoes-conexoes-manuais']['macros'] = macros
            self.atualizaJson()

    def carregaGlobalConfig(self):
        self.carregaJson()
        return self.config.get('configuracoes-globais', {})

    def salvaGlobalConfig(self, triggers, timers, keys, macros):
        self.carregaJson()
        self.config['configuracoes-globais'] = {
            'triggers': triggers,
            'timers': timers,
            'keys': keys,
            'macros': macros
        }
        self.atualizaJson()

    def carregaMudConfig(self, nome_mud):
        pasta_mud = Path(self.config['gerais']['diretorio-de-dados']) / "clientmud" / "muds" / nome_mud
        arquivo_mud = pasta_mud / "mud.json"
        
        if arquivo_mud.exists():
            return carrega_json_seguro(arquivo_mud, {})
        return {}

    def salvaMudConfig(self, nome_mud, triggers, timers, keys, macros):
        pasta_mud = Path(self.config['gerais']['diretorio-de-dados']) / "clientmud" / "muds" / nome_mud
        if not pasta_mud.exists():
            return False
        arquivo_mud = pasta_mud / "mud.json"
        dados = {
            'triggers': triggers,
            'timers': timers,
            'keys': keys,
            'macros': macros
        }
        try:
            with open(arquivo_mud, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
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
        return Path(pasta_base_str) / f'{nome_de_chave(personagem)}.json'

class GerenciaPersonagens:
    def __init__(self, config_obj=None, gerencia_pastas=None):
        self.config = config_obj
        self.pastas = gerencia_pastas

    def criaPersonagem(self, **kwargs):
        nome = kwargs.get('nome')
        mud = kwargs.pop('mud', '')
        chave = chave_personagem(nome, mud) if mud else nome
        pastaPersonagem = str(kwargs.pop('pasta', ''))
        pastaSons = str(kwargs.pop('pastaSons', ''))
        self.pastas.criaPastasPersonagem(pastaPersonagem, pastaSons)
        self.config.adicionaPersonagem(chave, pastaPersonagem)

        dic = {
            'triggers': [],
            'timers': [],
            'keys': [],
            'macros': []
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
        
        return carrega_json_seguro(caminho_personagem, None)

    def renomeiaPersonagem(self, chave_antigo, nome_novo):
        caminho_antigo = self.pastas.obtemCaminhoArquivoPersonagem(chave_antigo)
        if not caminho_antigo or not caminho_antigo.exists(): return False

        nome_antigo = nome_de_chave(chave_antigo)
        mud = mud_de_chave(chave_antigo)
        chave_novo = chave_personagem(nome_novo, mud) if mud else nome_novo

        pasta_antiga = caminho_antigo.parent
        pasta_nova = pasta_antiga.parent / nome_novo

        try:
            pasta_antiga.rename(pasta_nova)

            arquivo_json_antigo = pasta_nova / f"{nome_antigo}.json"
            arquivo_json_novo = pasta_nova / f"{nome_novo}.json"
            if arquivo_json_antigo.exists():
                arquivo_json_antigo.rename(arquivo_json_novo)

            if chave_antigo in self.config.config['personagens']:
                idx = self.config.config['personagens'].index(chave_antigo)
                self.config.config['personagens'][idx] = chave_novo

            if chave_antigo in self.config.config['gerais']['pastas-dos-muds']:
                del self.config.config['gerais']['pastas-dos-muds'][chave_antigo]
            self.config.config['gerais']['pastas-dos-muds'][chave_novo] = str(pasta_nova)

            self.config.atualizaJson()
            return True
        except Exception as e:
            gravaErro(e)
            return False

    def removePersonagem(self, personagem):
        self.pastas.removePastaPersonagem(personagem)
        self.config.removePersonagem(personagem)

    def atualizaPersonagem(self, chave, dic):
        caminho_arquivo = self.pastas.obtemCaminhoArquivoPersonagem(chave)
        if not caminho_arquivo:
            return False
        try:
            dic_limpo = {k: v for k, v in dic.items() if not k.startswith('_')}
            with open(caminho_arquivo, "w", encoding='utf-8') as arquivo:
                json.dump(dic_limpo, arquivo, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            gravaErro(e)
            return False