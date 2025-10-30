import re
import uuid

class Trigger:
	def __init__(self, config_dict=None):
		if config_dict is None:
			config_dict = {}
		
		self.id = config_dict.get('id', str(uuid.uuid4()))
		self.nome = config_dict.get('nome', '')
		self._padrao = config_dict.get('padrao', '')
		self._tipo_match = config_dict.get('tipo_match', 'padrao')
		self.acao = config_dict.get('acao', 'comando')
		self.valor_acao = config_dict.get('valor_acao', '')
		self.ativo = config_dict.get('ativo', True)
		self.ignorar_historico_principal = config_dict.get('ignorar_historico_principal', False)
		
		self.som_acao = config_dict.get('som_acao', '')
		self.som_volume = config_dict.get('som_volume', 100)
		
		self.regex_compilado = None
		self.modo_smart_capture = False

		if self._tipo_match == 'inicio':
			if '*' not in self._padrao: self._padrao = f"{self._padrao} *"
			self._tipo_match = 'padrao'
		elif self._tipo_match == 'fim':
			if '*' not in self._padrao: self._padrao = f"* {self._padrao}"
			self._tipo_match = 'padrao'
		elif self._tipo_match == 'meio':
			if '*' not in self._padrao: self._padrao = f"* {self._padrao} *"
			self._tipo_match = 'padrao'

		self._recompile_regex()

	@property
	def padrao(self):
		return self._padrao

	@padrao.setter
	def padrao(self, value):
		self._padrao = value
		self._recompile_regex()

	@property
	def tipo_match(self):
		return self._tipo_match

	@tipo_match.setter
	def tipo_match(self, value):
		self._tipo_match = value
		self._recompile_regex()

	def _recompile_regex(self):
		self.regex_compilado = None
		self.modo_smart_capture = False
		if not self._padrao:
			return

		if self._tipo_match == 'regex':
			try:
				self.regex_compilado = re.compile(self._padrao)
			except re.error:
				self.regex_compilado = None
			return

		if self._tipo_match == 'padrao':
			regex_pattern = ""
			tem_coringa = re.search(r'(?<!\\)[*&@?]', self._padrao)
			
			if tem_coringa:
				try:
					parts = re.split(r'(\\[*&@?]|\*|&|@|\?)', self._padrao)
					for part in parts:
						if part == '*':
							regex_pattern += '(.*?)'
						elif part == '&':
							regex_pattern += r'(\d+)'
						elif part == '@':
							regex_pattern += r'([a-zA-ZáéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ]+)'
						elif part == '?':
							regex_pattern += '(.)'
						elif part == r'\*':
							regex_pattern += r'\*'
						elif part == r'\&':
							regex_pattern += r'\&'
						elif part == r'\@':
							regex_pattern += r'\@'
						elif part == r'\?':
							regex_pattern += r'\?'
						elif part:
							regex_pattern += re.escape(part)
					
					if not self._padrao.startswith('*') and not self._padrao.startswith(r'\*'):
						regex_pattern = '^' + regex_pattern
					
					if not self._padrao.endswith('*') and not self._padrao.endswith(r'\*'):
						regex_pattern = regex_pattern + '$'
						
					self.regex_compilado = re.compile(regex_pattern)
				except re.error:
					self.regex_compilado = None
			else:
				try:
					padrao_escapado = re.escape(self._padrao)
					regex_pattern = f"^(.*?){padrao_escapado}(.*?)?$"
					self.regex_compilado = re.compile(regex_pattern)
					self.modo_smart_capture = True
				except re.error:
					self.regex_compilado = None

	def verifica(self, linha):
		if not self.ativo or not self.regex_compilado:
			return None
		
		match = self.regex_compilado.search(linha)
		if not match:
			return None

		if self.modo_smart_capture:
			g1 = match.group(1)
			g2 = match.group(2)
			captura = (g1 or g2 or '').strip()
			return (captura,)
		else:
			return match.groups()

	def to_dict(self):
		return {
			'id': self.id,
			'nome': self.nome,
			'padrao': self._padrao,
			'tipo_match': self._tipo_match,
			'acao': self.acao,
			'valor_acao': self.valor_acao,
			'ativo': self.ativo,
			'ignorar_historico_principal': self.ignorar_historico_principal,
			'som_acao': self.som_acao,
			'som_volume': self.som_volume
		}