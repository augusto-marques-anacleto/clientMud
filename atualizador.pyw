import requests
import shutil
import subprocess
import zipfile
import wx
from pathlib import Path
from threading import Thread
import sys
import os
import time
import re

class Atualizador:
	def __init__(self, pasta_local='.'):
		self.repo = 'augusto-marques-anacleto/clientMud'
		self.pasta_local = Path(pasta_local)
		self.pasta_atualizacao = self.pasta_local / 'upgrade'
		self.arquivo_versao = self.pasta_local / 'version'
		
		self.limpar_arquivos_antigos()
		
		self.janela_atualizador = JanelaAtualizador(self)
		self.verificar_atualizacao()

	def limpar_arquivos_antigos(self):
		try:
			for arquivo in self.pasta_local.glob("old_*"):
				try:
					arquivo.unlink()
				except:
					pass
		except:
			pass

	def extrair_tupla_versao(self, versao_str):
		numeros = re.findall(r'\d+', str(versao_str))
		return tuple(int(n) for n in numeros)

	def verificar_atualizacao(self):
		versao_atual = self.obter_versao_local()
		json_github = self.obter_ultima_versao_github()
		
		if json_github and not isinstance(json_github, Exception):
			tupla_local = self.extrair_tupla_versao(versao_atual)
			tupla_github = self.extrair_tupla_versao(json_github['tag_name'])
			
			if tupla_github > tupla_local:
				self.versao_github = json_github['tag_name']
				self.url_arquivo = json_github['assets'][0]['browser_download_url']
				self.arquivo = self.pasta_atualizacao / self.url_arquivo.split('/')[-1]
				
				novidades = json_github.get('body', 'Sem informações sobre as mudanças.')
				self.janela_atualizador.mostrar_dialogo_atualizacao(self.versao_github, novidades)
			else:
				wx.CallAfter(self.janela_atualizador.fechar)
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
			return '0.0.0'

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
		wx.CallAfter(self.janela_atualizador.fechar)

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

	def extrair_zip(self):
		with zipfile.ZipFile(self.arquivo, 'r') as arquivo_zip:
			arquivo_zip.extractall(self.pasta_atualizacao)

		self.aplicar_atualizacao_apos_sair()

	def aplicar_atualizacao_apos_sair(self):
		# Este processo (atualizador.exe) tem DLLs compartilhadas com o
		# clientmud.exe (python313.dll, as do wx, vcruntime, libssl...)
		# carregadas na memória, e o Windows não deixa sobrescrever um
		# arquivo em uso -- tentar trocar essas DLLs aqui dentro falha
		# silenciosamente e deixa o clientmud.exe novo ao lado de DLLs
		# antigas incompatíveis. Por isso a troca de arquivos é feita por um
		# script .bat que só roda depois que este processo tiver encerrado.
		pasta_local: Path = self.pasta_local
		keep_dirs = {"upgrade", "clientmud"}
		keep_files = {"version", "versao_atualizador.pyw", "config.json", "unins000.exe", "unins000.dat"}

		try:
			subprocess.run(["taskkill", "/F", "/IM", "clientmud.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		except Exception:
			pass

		self.atualizar_versao_local()

		src_com_pasta = pasta_local / "upgrade" / "clientmud"
		src = src_com_pasta if src_com_pasta.exists() and src_com_pasta.is_dir() else pasta_local / "upgrade"

		novos_nomes = set()
		if src.exists():
			for item in src.iterdir():
				if not (item.is_file() and item.suffix == '.zip'):
					novos_nomes.add(item.name)

		comandos = [
			"@echo off",
			"chcp 65001>nul",
			f'set "PID={os.getpid()}"',
			":esperar",
			'tasklist /FI "PID eq %PID%" 2>nul | find "%PID%" >nul',
			"if not errorlevel 1 (",
			"    ping -n 2 127.0.0.1 >nul",
			"    goto esperar",
			")",
		]

		for entry in pasta_local.iterdir():
			if entry.name.lower() in keep_dirs:
				continue
			if entry.is_dir():
				if entry.name not in novos_nomes:
					comandos.append(f'rmdir /s /q "{entry}" 2>nul')
			elif entry.name.lower() not in keep_files:
				comandos.append(f'del /f /q "{entry}" 2>nul')

		if src.exists():
			for item in src.iterdir():
				if item.is_file() and item.suffix == '.zip':
					continue
				dest = pasta_local / item.name
				comandos.append(f'if exist "{dest}\\" rmdir /s /q "{dest}" 2>nul')
				comandos.append(f'if exist "{dest}" del /f /q "{dest}" 2>nul')
				comandos.append(f'move /y "{item}" "{dest}" >nul')

		comandos.append(f'rmdir /s /q "{pasta_local / "upgrade"}" 2>nul')
		comandos.append(f'start "" "{pasta_local / "clientmud.exe"}"')
		comandos.append('del /f /q "%~f0"')

		bat_path = pasta_local / "aplicar_atualizacao.bat"
		bat_path.write_text("\r\n".join(comandos), encoding='utf-8')

		subprocess.Popen(
			["cmd", "/c", str(bat_path)],
			cwd=str(pasta_local),
			creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
			close_fds=True,
		)

		wx.CallAfter(self.janela_atualizador.fechar)

	def finalizar_atualizador(self):
		self.janela_atualizador.mostrar_mensagem('A atualização foi concluída com êxito, clique em OK para iniciar o programa.', 'Atualização Finalizada')
		self.atualizar_versao_local()
		exe = self.pasta_local / "clientmud.exe"
		if exe.exists():
			try:
				subprocess.Popen([str(exe)], shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
			except Exception:
				time.sleep(2)
				try:
					subprocess.Popen([str(exe)], cwd=str(self.pasta_local), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
				except Exception:
					pass
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

	def mostrar_dialogo_atualizacao(self, versao_github, novidades):
		dialogo = wx.Dialog(None, title=f'Nova Versão Disponível: {versao_github}', style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		painel = wx.Panel(dialogo)
		sizer_principal = wx.BoxSizer(wx.VERTICAL)

		lbl_info = wx.StaticText(painel, label=f"A versão {versao_github} está disponível. Confira o que mudou:")
		sizer_principal.Add(lbl_info, 0, wx.ALL, 10)

		txt_novidades = wx.TextCtrl(painel, value=novidades, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP)
		sizer_principal.Add(txt_novidades, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

		lbl_pergunta = wx.StaticText(painel, label="Deseja atualizar agora?")
		sizer_principal.Add(lbl_pergunta, 0, wx.ALL, 10)

		sizer_botoes = wx.BoxSizer(wx.HORIZONTAL)
		btn_sim = wx.Button(painel, wx.ID_YES, "&Sim, atualizar")
		btn_nao = wx.Button(painel, wx.ID_NO, "&Não, depois")
		
		btn_sim.Bind(wx.EVT_BUTTON, lambda evt: dialogo.EndModal(wx.ID_YES))
		btn_nao.Bind(wx.EVT_BUTTON, lambda evt: dialogo.EndModal(wx.ID_NO))

		sizer_botoes.Add(btn_sim, 0, wx.RIGHT, 5)
		sizer_botoes.Add(btn_nao, 0, wx.LEFT, 5)
		sizer_principal.Add(sizer_botoes, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)

		painel.SetSizer(sizer_principal)
		dialogo.SetSize((600, 450))
		dialogo.Center()
		
		txt_novidades.SetFocus()

		resultado = dialogo.ShowModal()
		dialogo.Destroy()

		if resultado == wx.ID_YES:
			subprocess.run(
				["taskkill", "/f", "/im", 'clientmud.exe'],
				stdout=subprocess.DEVNULL,
				stderr=subprocess.DEVNULL
			)

			self.Show()
			if not self.atualizador.pasta_atualizacao.exists():
				self.atualizador.pasta_atualizacao.mkdir()
			thread_arquivo = Thread(target=self.atualizador.baixar_arquivo)
			thread_arquivo.start()

		else:
			wx.CallAfter(self.fechar)

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