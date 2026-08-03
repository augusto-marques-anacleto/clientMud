import requests
import shutil
import subprocess
import wx
from pathlib import Path
from threading import Thread
import sys
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
				instalador = self._encontra_instalador(json_github.get('assets', []))
				if not instalador:
					self.download_erro('A versão nova não tem um instalador disponível.')
					return
				self.url_arquivo = instalador['browser_download_url']
				self.arquivo = self.pasta_atualizacao / instalador['name']

				novidades = json_github.get('body', 'Sem informações sobre as mudanças.')
				self.janela_atualizador.mostrar_dialogo_atualizacao(self.versao_github, novidades)
			else:
				wx.CallAfter(self.janela_atualizador.fechar)
		else:
			wx.CallAfter(wx.GetApp().ExitMainLoop)
			sys.exit(2)

	def _encontra_instalador(self, assets):
		# Busca por nome em vez de assets[0]: a ordem dos assets na release
		# ja quebrou o atualizador antes (ver historico do release.yml).
		for asset in assets:
			nome = asset.get('name', '').lower()
			if nome.startswith('instalador') and nome.endswith('.exe'):
				return asset
		for asset in assets:
			if asset.get('name', '').lower().endswith('.exe'):
				return asset
		return None

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
		if self.pasta_atualizacao.exists():
			shutil.rmtree(self.pasta_atualizacao)
		wx.CallAfter(wx.GetApp().ExitMainLoop)
		subprocess.run('clientmud.exe')
		wx.CallAfter(self.janela_atualizador.fechar)

	def iniciar_instalacao(self):
		self.janela_atualizador.mensagem_tela.SetLabel('Aplicando atualização.')
		if not self.arquivo.exists():
			self.download_erro('Arquivo não encontrado.')
			return
		self.rodar_instalador()

	def rodar_instalador(self):
		# O instalador (Inno Setup) e um executavel independente, sem
		# nenhuma DLL em comum com o atualizador.exe -- ao contrario de uma
		# atualizacao feita por este proprio processo (que tem
		# python313.dll, as DLLs do wx etc. carregadas na memoria e nao
		# consegue sobrescreve-las), rodar o instalador nunca esbarra em
		# arquivo em uso. So e preciso disparar o instalador silencioso e
		# encerrar este processo logo em seguida, soltando essas DLLs antes
		# que o instalador precise troca-las.
		#
		# Nao escrevemos o version aqui: o proprio pacote instalado ja traz
		# um arquivo version com o valor correto (Copy-Item no release.yml),
		# entao o instalador e a unica fonte de verdade -- escrever aqui
		# tambem so criava risco de inconsistencia entre os dois.
		try:
			subprocess.run(["taskkill", "/F", "/IM", "clientmud.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		except Exception:
			pass
		try:
			pasta_alvo = self.pasta_local.resolve()
			subprocess.Popen(
				[str(self.arquivo), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f'/DIR={pasta_alvo}'],
				close_fds=True,
			)
		except Exception as e:
			wx.CallAfter(self.download_erro, e)
			return
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