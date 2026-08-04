import ctypes
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from threading import Thread

import requests
import wx

NOME_QUARENTENA = '.antigos'
NOME_MANIFESTO = '.instalados'
NOME_OBSOLETOS = '.obsoletos'
ATRIBUTO_OCULTO = 0x2

CAIXA_DE_MENSAGEM = ctypes.windll.user32.MessageBoxW
PERMITIR_PRIMEIRO_PLANO = ctypes.windll.user32.AllowSetForegroundWindow
ENUMERAR_JANELAS = ctypes.windll.user32.EnumWindows
DONO_DA_JANELA = ctypes.windll.user32.GetWindowThreadProcessId
JANELA_VISIVEL = ctypes.windll.user32.IsWindowVisible
TRAZER_PARA_FRENTE = ctypes.windll.user32.SetForegroundWindow
ALTERNAR_PARA_JANELA = ctypes.windll.user32.SwitchToThisWindow
EXIBIR_JANELA = ctypes.windll.user32.ShowWindow
SW_HIDE = 0
TIPO_VISITA = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

SEM_JANELA = subprocess.CREATE_NO_WINDOW


def esconder(caminho):
	try:
		ctypes.windll.kernel32.SetFileAttributesW(str(caminho), ATRIBUTO_OCULTO)
	except OSError:
		pass


def caminho_do_executavel():
	buffer = ctypes.create_unicode_buffer(32768)
	if ctypes.windll.kernel32.GetModuleFileNameW(None, buffer, len(buffer)) and buffer.value:
		return Path(buffer.value)
	return Path(sys.executable)


MODO_REINSTALAR = 'novo' in caminho_do_executavel().stem.lower()


def pasta_de_instalacao():
	executavel = caminho_do_executavel().resolve()
	if executavel.stem.lower().startswith('python'):
		return Path(__file__).resolve().parent
	return executavel.parent


class Atualizador:
	def __init__(self, pasta_local=None):
		self.repo = 'augusto-marques-anacleto/clientMud'
		self.pasta_local = Path(pasta_local).resolve() if pasta_local else pasta_de_instalacao()
		self.pasta_atualizacao = self.pasta_local / 'upgrade'
		self.quarentena = self.pasta_local / NOME_QUARENTENA
		self.arquivo_versao = self.pasta_local / 'version'
		self.arquivo_manifesto = self.pasta_local / NOME_MANIFESTO
		self.cliente_encerrado = False

		self.limpar_restos()

		self.janela_atualizador = JanelaAtualizador(self)
		self.identificador_janela = self.janela_atualizador.GetHandle()
		self.verificar_atualizacao()

	def limpar_restos(self):
		shutil.rmtree(self.quarentena, ignore_errors=True)
		shutil.rmtree(self.pasta_atualizacao, ignore_errors=True)
		try:
			for arquivo in self.pasta_local.glob('old_*'):
				try:
					arquivo.unlink()
				except OSError:
					pass
		except OSError:
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

			if MODO_REINSTALAR or tupla_github > tupla_local:
				self.versao_github = json_github['tag_name']
				pacote = self._encontra_pacote(json_github.get('assets', []))
				if not pacote:
					self.download_erro('a nova versão não tem um pacote disponível para download.')
					return
				self.url_arquivo = pacote['browser_download_url']
				self.arquivo = self.pasta_atualizacao / pacote['name']

				novidades = json_github.get('body', 'Sem informações sobre as mudanças.')
				self.janela_atualizador.mostrar_dialogo_atualizacao(self.versao_github, novidades)
			else:
				wx.CallAfter(self.janela_atualizador.fechar)
		else:
			wx.CallAfter(wx.GetApp().ExitMainLoop)
			sys.exit(2)

	def _encontra_pacote(self, assets):
		for asset in assets:
			if asset.get('name', '').lower() == 'clientmud.zip':
				return asset
		for asset in assets:
			if asset.get('name', '').lower().endswith('.zip'):
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
						if total_size:
							wx.CallAfter(self.janela_atualizador.atualizar_progresso, int((baixado / total_size) * 100))
			if total_size and baixado != total_size:
				raise RuntimeError('o download foi interrompido antes de terminar.')
		except Exception as e:
			wx.CallAfter(self.download_erro, e)
			return
		self.iniciar_instalacao()

	def download_erro(self, erro):
		self.janela_atualizador.mostrar_mensagem(f'Não foi possível baixar a atualização, erro: {erro}.', 'Erro na Atualização', wx.ICON_ERROR)
		shutil.rmtree(self.pasta_atualizacao, ignore_errors=True)
		if self.cliente_encerrado:
			self.iniciar_cliente()
		wx.CallAfter(self.janela_atualizador.fechar)

	def iniciar_instalacao(self):
		wx.CallAfter(self.janela_atualizador.mensagem_tela.SetLabel, 'Aplicando atualização.')
		try:
			raiz = self.extrair_pacote()
			anteriores = self.ler_manifesto()
			self.encerrar_cliente()
			instalados = self.aplicar_pacote(raiz)
			self.garantir_versao()
			self.remover_obsoletos(anteriores + self.ler_obsoletos_do_pacote(), instalados)
		except Exception as e:
			wx.CallAfter(self.falha_na_atualizacao, e)
			return
		self.concluir()

	def extrair_pacote(self):
		if not self.arquivo.exists():
			raise RuntimeError('o arquivo baixado não foi encontrado')
		with zipfile.ZipFile(self.arquivo) as pacote:
			corrompido = pacote.testzip()
			if corrompido:
				raise RuntimeError(f'o download chegou corrompido no arquivo {corrompido}')
			entradas = [info for info in pacote.infolist() if not info.is_dir()]
			pacote.extractall(self.pasta_atualizacao)

		for info in entradas:
			extraido = self.pasta_atualizacao / info.filename
			if not extraido.exists() or extraido.stat().st_size != info.file_size:
				raise RuntimeError(f'a extração ficou incompleta em {info.filename}, verifique o espaço livre em disco')

		raiz = self.pasta_atualizacao / 'clientmud'
		if not raiz.is_dir():
			raiz = self.pasta_atualizacao
		if not (raiz / 'clientmud.exe').exists():
			raise RuntimeError('o pacote baixado não contém o clientmud.exe')
		return raiz

	def encerrar_cliente(self):
		self.cliente_encerrado = True
		try:
			subprocess.run(['taskkill', '/F', '/IM', 'clientmud.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=SEM_JANELA)
		except OSError:
			return
		for _ in range(40):
			try:
				saida = subprocess.run(
					['tasklist', '/FI', 'IMAGENAME eq clientmud.exe', '/NH'],
					capture_output=True, text=True, errors='ignore', creationflags=SEM_JANELA,
				).stdout
			except OSError:
				return
			if 'clientmud.exe' not in saida.lower():
				return
			time.sleep(0.25)

	def aplicar_pacote(self, raiz):
		arquivos = []
		for origem in raiz.rglob('*'):
			if origem.is_dir() or origem == self.arquivo:
				continue
			relativo = origem.relative_to(raiz)
			arquivos.append((origem, self.pasta_local / relativo, origem.stat().st_size))

		if not arquivos:
			raise RuntimeError('o pacote baixado está vazio')

		self.quarentena.mkdir(parents=True, exist_ok=True)
		esconder(self.quarentena)

		diario = []
		try:
			for origem, destino, _ in arquivos:
				destino.parent.mkdir(parents=True, exist_ok=True)
				if destino.exists():
					guardado = self.quarentena / destino.relative_to(self.pasta_local)
					guardado.parent.mkdir(parents=True, exist_ok=True)
					os.replace(destino, guardado)
					diario.append(('guardado', destino, guardado))
				os.replace(origem, destino)
				diario.append(('instalado', destino, origem))

			for _, destino, tamanho in arquivos:
				if not destino.exists() or destino.stat().st_size != tamanho:
					raise RuntimeError(f'o arquivo {destino.name} não ficou igual ao do pacote')
		except Exception:
			self.desfazer(diario)
			raise

		return {str(destino.relative_to(self.pasta_local)) for _, destino, _ in arquivos}

	def garantir_versao(self):
		try:
			if self.arquivo_versao.read_bytes().strip() == self.versao_github.encode():
				return
		except OSError:
			pass
		try:
			self.arquivo_versao.write_bytes(self.versao_github.encode())
		except OSError:
			pass

	def ler_manifesto(self):
		try:
			return self.arquivo_manifesto.read_text(encoding='utf-8-sig').split('\n')
		except OSError:
			return []

	def ler_obsoletos_do_pacote(self):
		try:
			return (self.pasta_local / NOME_OBSOLETOS).read_text(encoding='utf-8-sig').split('\n')
		except OSError:
			return []

	def remover_obsoletos(self, anteriores, instalados):
		pastas_mexidas = set()
		for relativo in anteriores:
			relativo = relativo.strip()
			if not relativo or relativo in instalados:
				continue
			caminho = self.pasta_local / relativo
			if not caminho.is_file():
				continue
			try:
				caminho.unlink()
			except OSError:
				try:
					guardado = self.quarentena / relativo
					guardado.parent.mkdir(parents=True, exist_ok=True)
					os.replace(caminho, guardado)
				except OSError:
					continue
			pastas_mexidas.add(caminho.parent)

		for pasta in sorted(pastas_mexidas, key=lambda p: len(p.parts), reverse=True):
			while pasta != self.pasta_local and pasta.is_dir():
				try:
					pasta.rmdir()
				except OSError:
					break
				pasta = pasta.parent

		try:
			self.arquivo_manifesto.write_text('\n'.join(sorted(instalados)), encoding='utf-8')
			esconder(self.arquivo_manifesto)
		except OSError:
			pass
		esconder(self.pasta_local / NOME_OBSOLETOS)

	def desfazer(self, diario):
		for acao, destino, reserva in reversed(diario):
			try:
				if acao == 'instalado':
					os.replace(destino, reserva)
				else:
					os.replace(reserva, destino)
			except OSError:
				pass

	def falha_na_atualizacao(self, erro):
		self.janela_atualizador.mostrar_mensagem(
			f'Não foi possível aplicar a atualização, erro: {erro}.\n\n'
			'Nada foi alterado, o Client Mud continua funcionando na versão atual. '
			'Feche o cliente e tente de novo, ou baixe a versão nova em '
			'https://github.com/augusto-marques-anacleto/clientmud/releases',
			'Erro na Atualização', wx.ICON_ERROR,
		)
		shutil.rmtree(self.pasta_atualizacao, ignore_errors=True)
		if self.cliente_encerrado:
			self.iniciar_cliente()
		wx.CallAfter(self.janela_atualizador.fechar)

	def iniciar_cliente(self):
		executavel = self.pasta_local / 'clientmud.exe'
		try:
			processo = subprocess.Popen([str(executavel)], cwd=str(self.pasta_local), close_fds=True)
		except OSError:
			return
		try:
			PERMITIR_PRIMEIRO_PLANO(processo.pid)
		except OSError:
			pass
		self.trazer_cliente_para_frente(processo.pid)

	def trazer_cliente_para_frente(self, pid):
		limite = time.time() + 8
		while time.time() < limite:
			encontradas = []

			def visita(janela, _):
				dono = ctypes.c_ulong()
				DONO_DA_JANELA(janela, ctypes.byref(dono))
				if dono.value == pid and JANELA_VISIVEL(janela):
					encontradas.append(janela)
				return True

			try:
				ENUMERAR_JANELAS(TIPO_VISITA(visita), 0)
			except OSError:
				return
			if encontradas:
				TRAZER_PARA_FRENTE(encontradas[0])
				ALTERNAR_PARA_JANELA(encontradas[0], True)
				return
			time.sleep(0.3)

	def concluir(self):
		shutil.rmtree(self.pasta_atualizacao, ignore_errors=True)
		CAIXA_DE_MENSAGEM(
			0,
			'A reinstalação foi concluída com êxito, clique em OK para iniciar o programa.'
			if MODO_REINSTALAR else
			'A atualização foi concluída com êxito, clique em OK para iniciar o programa.',
			'Reinstalação Finalizada' if MODO_REINSTALAR else 'Atualização Finalizada',
			0x40,
		)
		shutil.rmtree(self.quarentena, ignore_errors=True)
		try:
			EXIBIR_JANELA(self.identificador_janela, SW_HIDE)
		except OSError:
			pass
		self.iniciar_cliente()
		os._exit(0)


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
		if MODO_REINSTALAR:
			titulo = f'Reinstalar o Client Mud {versao_github}'
			informacao = (f'Isto vai reinstalar o Client Mud na versão {versao_github}, repondo qualquer '
				'arquivo faltando ou trocado. Seus personagens, configurações, scripts, sons e logs '
				'não são afetados.')
			pergunta = 'Deseja reinstalar agora?'
			rotulo_sim = '&Sim, reinstalar'
		else:
			titulo = f'Nova Versão Disponível: {versao_github}'
			informacao = f'A versão {versao_github} está disponível. Confira o que mudou:'
			pergunta = 'Deseja atualizar agora?'
			rotulo_sim = '&Sim, atualizar'

		dialogo = wx.Dialog(None, title=titulo, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		painel = wx.Panel(dialogo)
		sizer_principal = wx.BoxSizer(wx.VERTICAL)

		lbl_info = wx.StaticText(painel, label=informacao)
		sizer_principal.Add(lbl_info, 0, wx.ALL, 10)

		txt_novidades = wx.TextCtrl(painel, value=novidades, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_BESTWRAP)
		sizer_principal.Add(txt_novidades, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

		lbl_pergunta = wx.StaticText(painel, label=pergunta)
		sizer_principal.Add(lbl_pergunta, 0, wx.ALL, 10)

		sizer_botoes = wx.BoxSizer(wx.HORIZONTAL)
		btn_sim = wx.Button(painel, wx.ID_YES, rotulo_sim)
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
			self.Show()
			self.atualizador.pasta_atualizacao.mkdir(parents=True, exist_ok=True)
			esconder(self.atualizador.pasta_atualizacao)
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
