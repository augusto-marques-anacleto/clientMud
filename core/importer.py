import os
import shutil
import zipfile
import tempfile
import requests
import re
import time
from pathlib import Path

class SoundImporter:
    def __init__(self, pasta_sons):
        self.pasta_sons = Path(pasta_sons)
        self.cancelar = False

    def limpar_url(self, texto):
        inicio = texto.find('http')
        if inicio == -1:
            return texto.strip()
            
        texto = texto[inicio:]
        url_limpa = ""
        
        for char in texto:
            if char in (' ', '<', '>', '"', "'"):
                break
            if char not in ('\n', '\r', '\t'):
                url_limpa += char
            
        return url_limpa

    def extrair_id_drive(self, url):
        match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
        if match: return match.group(1)
        match = re.search(r'id=([a-zA-Z0-9_-]+)', url)
        if match: return match.group(1)
        return None

    def baixar_da_url(self, url_bruta, caminho_destino, callback_progresso):
        self.cancelar = False
        url = self.limpar_url(url_bruta)
        
        if not url:
            return False

        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        try:
            if 'drive.usercontent.google.com' in url or 'confirm=' in url:
                resposta = session.get(url, stream=True, timeout=(10, 30))
            else:
                drive_id = self.extrair_id_drive(url)
                if drive_id:
                    url_download = f"https://drive.google.com/uc?export=download&id={drive_id}"
                    resposta = session.get(url_download, stream=True, timeout=(10, 30))
                    
                    if 'text/html' in resposta.headers.get('Content-Type', ''):
                        form_match = re.search(r'(<form[^>]*id=["\']download-form["\'].*?</form>)', resposta.text, re.DOTALL | re.IGNORECASE)
                        
                        if form_match:
                            html_form = form_match.group(1)
                            action_match = re.search(r'action=["\']([^"\']+)["\']', html_form, re.IGNORECASE)
                            action_url = action_match.group(1) if action_match else url_download
                            
                            if action_url.startswith('/'):
                                action_url = "https://drive.google.com" + action_url
                                
                            params = {}
                            for input_tag in re.findall(r'<input[^>]+>', html_form, re.IGNORECASE):
                                name_match = re.search(r'name=["\']([^"\']+)["\']', input_tag, re.IGNORECASE)
                                value_match = re.search(r'value=["\']([^"\']*)["\']', input_tag, re.IGNORECASE)
                                if name_match:
                                    params[name_match.group(1)] = value_match.group(1) if value_match else ''
                                    
                            resposta = session.get(action_url, params=params, stream=True, timeout=(10, 30))
                        else:
                            match = re.search(r'confirm=([a-zA-Z0-9_-]+)', resposta.text)
                            if match:
                                token = match.group(1)
                                params = {'id': drive_id, 'confirm': token}
                                resposta = session.get(url_download, params=params, stream=True, timeout=(10, 30))
                else:
                    if 'dropbox.com' in url:
                        url = url.replace('dl=0', 'dl=1')
                    resposta = session.get(url, stream=True, timeout=(10, 30))

            resposta.raise_for_status()
            
            if 'text/html' in resposta.headers.get('Content-Type', ''):
                return False
            
            tamanho_total = int(resposta.headers.get('content-length', 0))
            baixado = 0
            inicio = time.time()
            ultimo_tempo_ui = 0

            with open(caminho_destino, 'wb') as f:
                for chunk in resposta.iter_content(chunk_size=1048576):
                    if self.cancelar:
                        return False
                    if chunk:
                        f.write(chunk)
                        baixado += len(chunk)
                        
                        if callback_progresso:
                            agora = time.time()
                            if agora - ultimo_tempo_ui >= 0.5 or baixado == tamanho_total:
                                ultimo_tempo_ui = agora
                                decorrido = agora - inicio
                                
                                if tamanho_total > 0:
                                    porcentagem = int((baixado / tamanho_total) * 100)
                                    if decorrido > 0:
                                        velocidade_bps = baixado / decorrido
                                        velocidade_mbps = velocidade_bps / (1024 * 1024)
                                        restante_bytes = tamanho_total - baixado
                                        eta_segundos = restante_bytes / velocidade_bps if velocidade_bps > 0 else 0
                                        minutos, segundos = divmod(int(eta_segundos), 60)
                                        detalhe = f"{velocidade_mbps:.1f} MB/s, restante: {minutos}m {segundos}s"
                                    else:
                                        detalhe = ""
                                else:
                                    porcentagem = 0
                                    if decorrido > 0:
                                        velocidade_bps = baixado / decorrido
                                        velocidade_mbps = velocidade_bps / (1024 * 1024)
                                        mb_baixado = baixado / (1024 * 1024)
                                        detalhe = f"{mb_baixado:.1f} MB baixados ({velocidade_mbps:.1f} MB/s)"
                                    else:
                                        detalhe = f"{baixado / (1024 * 1024):.1f} MB baixados"
                                        
                                callback_progresso("baixando", porcentagem, detalhe)
                                
            return True
        except Exception:
            return False

    def extrair_e_copiar(self, caminho_zip, callback_progresso):
        self.cancelar = False
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                pasta_temp = Path(temp_dir)
                
                with zipfile.ZipFile(caminho_zip, 'r') as zip_ref:
                    infos = zip_ref.infolist()
                    total_arquivos = len(infos)
                    ultimo_tempo_ui = 0
                    
                    for i, info in enumerate(infos):
                        if self.cancelar: return False
                        if info.is_dir(): continue
                        
                        nome = info.filename
                        if not info.flag_bits & 0x800:
                            try:
                                bytes_reais = nome.encode('cp437')
                                try:
                                    nome = bytes_reais.decode('utf-8')
                                except UnicodeDecodeError:
                                    nome = bytes_reais.decode('cp850')
                            except Exception:
                                pass
                                
                        caminho_arquivo_temp = pasta_temp / nome
                        caminho_arquivo_temp.parent.mkdir(parents=True, exist_ok=True)
                        
                        with open(caminho_arquivo_temp, 'wb') as f_out:
                            f_out.write(zip_ref.read(info.filename))
                            
                        if callback_progresso:
                            agora = time.time()
                            if agora - ultimo_tempo_ui >= 0.5 or i == total_arquivos - 1:
                                ultimo_tempo_ui = agora
                                porcentagem = int(((i + 1) / total_arquivos) * 100)
                                callback_progresso("extraindo", porcentagem, f"Arquivo {i+1} de {total_arquivos}")

                conteudo_temp = list(pasta_temp.iterdir())
                pasta_origem = conteudo_temp[0] if len(conteudo_temp) == 1 and conteudo_temp[0].is_dir() else pasta_temp
                
                arquivos_para_mover = []
                for root, dirs, files in os.walk(pasta_origem):
                    for file in files:
                        arquivos_para_mover.append(Path(root) / file)
                        
                total_itens = len(arquivos_para_mover)
                ultimo_tempo_ui = 0
                
                for i, caminho_arquivo in enumerate(arquivos_para_mover):
                    if self.cancelar: return False
                    
                    caminho_relativo = caminho_arquivo.relative_to(pasta_origem)
                    destino_final = self.pasta_sons / caminho_relativo
                    
                    destino_final.parent.mkdir(parents=True, exist_ok=True)
                    
                    if destino_final.exists():
                        try:
                            destino_final.unlink()
                        except:
                            pass
                            
                    try:
                        shutil.move(str(caminho_arquivo), str(destino_final))
                    except:
                        pass
                    
                    if callback_progresso:
                        agora = time.time()
                        if agora - ultimo_tempo_ui >= 0.5 or i == total_itens - 1:
                            ultimo_tempo_ui = agora
                            porcentagem = int(((i + 1) / total_itens) * 100)
                            callback_progresso("copiando", porcentagem, f"Movendo {i+1} de {total_itens}")
            return True
        except Exception:
            return False