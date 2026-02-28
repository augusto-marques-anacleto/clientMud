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
                    
                for arquivo_temp in pasta_temp.glob('*.json'):
                    shutil.copy2(arquivo_temp, self.base_dir / arquivo_temp.name)
                    
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
                                
            return True, "Backup restaurado com sucesso!"
        except Exception as e:
            return False, f"Falha ao restaurar backup: {e}"