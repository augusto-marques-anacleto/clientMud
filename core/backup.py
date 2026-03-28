import os
import shutil
import zipfile
import tempfile
import json
from pathlib import Path

class GerenciadorBackup:
    def __init__(self, diretorio_base):
        self.base_dir = Path(diretorio_base)
        self.dados_dir = self.base_dir
        
        config_path = self.base_dir / 'config.json'
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    dir_dados = data.get('gerais', {}).get('diretorio-de-dados')
                    if dir_dados:
                        self.dados_dir = Path(dir_dados)
            except:
                pass

    def exportar(self, caminho_destino):
        try:
            with zipfile.ZipFile(caminho_destino, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for arquivo in self.base_dir.glob('*.json'):
                    zipf.write(arquivo, arquivo.name)
                    
                pasta_clientmud = self.dados_dir / 'clientmud'
                if pasta_clientmud.exists():
                    for root, _, files in os.walk(pasta_clientmud):
                        for file in files:
                            if file.endswith('.json'):
                                caminho_completo = Path(root) / file
                                caminho_relativo = caminho_completo.relative_to(self.dados_dir)
                                zipf.write(caminho_completo, str(caminho_relativo))
            return True, "Backup gerado com sucesso!"
        except Exception as e:
            return False, f"Falha ao gerar backup: {e}"

    def importar(self, caminho_zip):
        try:
            if not zipfile.is_zipfile(caminho_zip):
                return False, "O arquivo não é um backup válido."
                
            with tempfile.TemporaryDirectory() as temp_dir:
                pasta_temp = Path(temp_dir)
                
                with zipfile.ZipFile(caminho_zip, 'r') as zipf:
                    zipf.extractall(pasta_temp)

                config_temp_path = pasta_temp / 'config.json'
                
                if config_temp_path.exists():
                    try:
                        with open(config_temp_path, 'r', encoding='utf-8') as f:
                            config_data = json.load(f)
                        
                        dir_backup_str = config_data.get('gerais', {}).get('diretorio-de-dados')
                        if dir_backup_str:
                            dir_backup = Path(dir_backup_str)
                            if dir_backup.exists():
                                self.dados_dir = dir_backup
                    except:
                        pass

                novas_pastas_muds = {}
                pasta_clientmud_temp = pasta_temp / 'clientmud'
                
                if pasta_clientmud_temp.exists():
                    for root, _, files in os.walk(pasta_clientmud_temp):
                        for file in files:
                            if file.endswith('.json'):
                                arquivo_json = Path(root) / file
                                caminho_relativo = arquivo_json.relative_to(pasta_temp)
                                destino_final = self.dados_dir / caminho_relativo
                                
                                destino_final.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(arquivo_json, destino_final)
                                
                                if 'muds' in caminho_relativo.parts and file != 'mud.json':
                                    nome_perso = file[:-5]
                                    novas_pastas_muds[nome_perso] = str(destino_final.parent)

                if config_temp_path.exists():
                    try:
                        with open(config_temp_path, 'r', encoding='utf-8') as f:
                            config_data = json.load(f)
                            
                        if 'gerais' not in config_data:
                            config_data['gerais'] = {}
                            
                        config_data['gerais']['diretorio-de-dados'] = str(self.dados_dir)
                        config_data['gerais']['logs'] = str(self.dados_dir / 'clientmud' / 'logs')
                        config_data['gerais']['scripts'] = str(self.dados_dir / 'clientmud' / 'scripts')
                        config_data['gerais']['sons'] = str(self.dados_dir / 'clientmud' / 'sons')
                        
                        if novas_pastas_muds:
                            config_data['gerais']['pastas-dos-muds'] = novas_pastas_muds
                            
                        with open(self.base_dir / 'config.json', 'w', encoding='utf-8') as f:
                            json.dump(config_data, f, indent=4, ensure_ascii=False)
                    except Exception:
                        shutil.copy2(config_temp_path, self.base_dir / 'config.json')

                for arquivo_temp in pasta_temp.glob('*.json'):
                    if arquivo_temp.name != 'config.json':
                        shutil.copy2(arquivo_temp, self.base_dir / arquivo_temp.name)
                                
            return True, "Backup restaurado com sucesso!"
        except Exception as e:
            return False, f"Falha ao restaurar backup: {e}"