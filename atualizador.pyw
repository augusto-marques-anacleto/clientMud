import requests
import shutil
import subprocess
import zipfile
import wx
from pathlib import Path
from threading import Thread
import sys

class Atualizador:
    def __init__(self, pasta_local='.'):
        self.repo = 'augusto-marques-anacleto/clientMud'
        self.pasta_local = Path(pasta_local)
        self.pasta_atualizacao = self.pasta_local / 'upgrade'
        self.arquivo_versao = self.pasta_local / 'version'
        self.janela_atualizador = JanelaAtualizador(self)
        self.verificar_atualizacao()

    def verificar_atualizacao(self):
        versao_atual = self.obter_versao_local()
        json_github = self.obter_ultima_versao_github()
        if json_github and not isinstance(json_github, Exception):
            if versao_atual != json_github['tag_name']:
                self.versao_github = json_github['tag_name']
                self.url_arquivo = json_github['assets'][0]['browser_download_url']
                self.arquivo = self.pasta_atualizacao / self.url_arquivo.split('/')[-1]
                self.janela_atualizador.mostrar_dialogo_atualizacao(self.versao_github)
            else:
                sys.exit(0)
        else:
            wx.CallAfter(wx.GetApp().ExitMainLoop)
            sys.exit(2)

    def obter_ultima_versao_github(self):
        url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            return False
        except Exception as e:
            return e

    def obter_versao_local(self):
        try:
            with open(self.arquivo_versao, 'r') as file:
                return file.read().strip()
        except Exception:
            return 'v_0.0'

    def atualizar_versao_local(self):
        with open(self.arquivo_versao, 'w') as file:
            file.write(self.versao_github)

    def baixar_arquivo(self):
        try:
            with requests.get(self.url_arquivo, stream=True) as r:
                total_size = int(r.headers.get('content-length', 0))
                with open(self.arquivo, 'wb') as f:
                    baixado = 0
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        baixado += len(chunk)
                        wx.CallAfter(self.janela_atualizador.atualizar_progresso, int((baixado / total_size) * 100))
            self.iniciar_instalacao()
        except Exception as e:
            wx.CallAfter(self.download_erro, e)

    def download_erro(self, erro):
        self.janela_atualizador.mostrar_mensagem(f'Não foi possível baixar a atualização, erro: {erro}.', 'Erro na Atualização', wx.ICON_ERROR)
        shutil.rmtree(self.pasta_atualizacao)
        wx.CallAfter(wx.GetApp().ExitMainLoop)
        subprocess.run('clientmud.exe')
        sys.exit(2)

    def iniciar_instalacao(self):
        self.janela_atualizador.mensagem_tela.SetLabel('Aplicando atualização.')
        if self.arquivo.exists():
            if self.arquivo.suffix == '.exe':
                self.move_exe()
            elif self.arquivo.suffix == '.zip':
                self.extrair_zip()
        else:
            self.download_erro('Arquivo não encontrado.')

    def move_exe(self):
        arquivo_antigo = self.pasta_local / self.arquivo.name
        if arquivo_antigo.exists():
            arquivo_antigo.unlink()
        shutil.move(self.arquivo, self.pasta_local)
        self.finalizar_atualizador()
        sys.exit()

    def extrair_zip(self):
        with zipfile.ZipFile(self.arquivo, 'r') as arquivo_zip:
            arquivo_zip.extractall(self.pasta_atualizacao)
        self.criar_e_executar_bat()

    def criar_e_executar_bat(self):
        bat_content = f"""@echo off
taskkill /IM atualizador.exe /F > nul 2>&1
cd /d "{self.pasta_local}"
REM Excluir todas as pastas, exceto "upgrade" e "clientmud"
for /d %%D in (*) do (
    if /I not "%%~nxD"=="upgrade" if /I not "%%~nxD"=="clientmud" (
        rd /s /q "%%D"
    )
)
REM Excluir todos os arquivos, exceto os especificados
for %%F in (*) do (
    if /I not "%%~nxF"=="version" if /I not "%%~nxF"=="versao_atualizador.pyw" if /I not "%%~nxF"=="config.json" if /I not "%%~nxF"=="atualizador.bat" (
        del /q "%%F"
    )
)
REM Mover conteúdo de "upgrade\\clientmud" para a pasta local
robocopy "upgrade\\clientmud" "{self.pasta_local}" /e /move > nul 2>&1
REM Iniciar "clientmud.exe"
start "" "clientmud.exe"
timeout /t 2 /nobreak > nul
REM Excluir a pasta "upgrade"
rd /s /q "upgrade"
del /q "atualizador.bat"
"""
        bat_path = self.pasta_local / 'atualizador.bat'
        with open(bat_path, 'w') as bat_file:
            bat_file.write(bat_content)
        self.finalizar_atualizador()
        subprocess.run([str(bat_path)], shell=True)
        sys.exit()

    def finalizar_atualizador(self):
        self.janela_atualizador.mostrar_mensagem('A atualização foi concluída com êxito, clique em OK para iniciar o programa.', 'Atualização Finalizada')
        self.atualizar_versao_local()
        wx.CallAfter(self.janela_atualizador.fechar)

class JanelaAtualizador(wx.Frame):
    def __init__(self, atualizador):
        super().__init__(None, title="Atualizador Client Mud")
        self.atualizador = atualizador
        self.painel = wx.Panel(self)
        self.mensagem_tela = wx.StaticText(self.painel, label='Baixando Atualização')
        self.progresso = wx.Gauge(self.painel, range=100)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.mensagem_tela, 0, wx.ALL, 5)
        sizer.Add(self.progresso, 0, wx.ALL | wx.EXPAND, 5)
        self.painel.SetSizer(sizer)
        self.Fit()

    def mostrar_dialogo_atualizacao(self, versao_github):
        dialogo = wx.MessageDialog(None, f'Nova versão disponível: {versao_github}\nDeseja atualizar agora?', 'Nova Versão Disponível', wx.YES_NO | wx.ICON_QUESTION)
        resultado = dialogo.ShowModal()
        if resultado == wx.ID_YES:
            subprocess.run(
                ["taskkill", "/f", "/im", 'clientmud.exe'],
                stdout=subprocess.DEVNULL,  # Redireciona a saída padrão para DEVNULL
                stderr=subprocess.DEVNULL   # Redireciona a saída de erro para DEVNULL
            )

            self.Show()
            if not self.atualizador.pasta_atualizacao.exists():
                self.atualizador.pasta_atualizacao.mkdir()
            thread_arquivo = Thread(target=self.atualizador.baixar_arquivo)
            thread_arquivo.start()

        else:
            sys.exit()

    def atualizar_progresso(self, progresso):
        self.progresso.SetValue(progresso)

    def mostrar_mensagem(self, mensagem='', titulo='Atualizador', estilo=wx.ICON_INFORMATION):
        wx.MessageBox(mensagem, titulo, estilo)

    def fechar(self):
        self.Close(True)
        wx.CallAfter(wx.GetApp().ExitMainLoop)

if __name__ == "__main__":
    app = wx.App()
    atualizador = Atualizador()
    app.MainLoop()
