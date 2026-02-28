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
        self.escopo = config_dict.get('escopo', 0)
        self.som_acao = config_dict.get('som_acao', '')
        self.som_volume = config_dict.get('som_volume', 100)
        
        self.regex_compilado = None

        self._normalizar_tipo_match()
        self._recompile_regex()

    def _normalizar_tipo_match(self):
        if self._tipo_match in ('inicio', 'fim', 'meio'):
            if self._tipo_match == 'inicio' and '*' not in self._padrao:
                self._padrao = f"{self._padrao} *"
            elif self._tipo_match == 'fim' and '*' not in self._padrao:
                self._padrao = f"* {self._padrao}"
            elif self._tipo_match == 'meio' and '*' not in self._padrao:
                self._padrao = f"* {self._padrao} *"
            self._tipo_match = 'padrao'

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
        
        if not self._padrao:
            return

        if self._tipo_match == 'regex':
            try:
                self.regex_compilado = re.compile(self._padrao)
            except re.error:
                self.regex_compilado = None
            return

        if self._tipo_match == 'padrao':
            try:
                tem_coringa = re.search(r'(?<!\\)[*&@?]', self._padrao)
                
                if tem_coringa:
                    regex_pattern = "^"
                    parts = re.split(r'(\\[*&@?]|\*|&|@|\?)', self._padrao)
                    for part in parts:
                        if part == '*': regex_pattern += '(.*?)'
                        elif part == '&': regex_pattern += r'(\d+)'
                        elif part == '@': regex_pattern += r'([^\W\d_]+)'
                        elif part == '?': regex_pattern += '(.)'
                        elif part in (r'\*', r'\&', r'\@', r'\?'): regex_pattern += re.escape(part[-1])
                        elif part: regex_pattern += re.escape(part)
                    
                    regex_pattern += '$'
                    self.regex_compilado = re.compile(regex_pattern)
                else:
                    padrao_escapado = re.escape(self._padrao)
                    regex_pattern = f"^{padrao_escapado}$"
                    self.regex_compilado = re.compile(regex_pattern)
            except re.error:
                self.regex_compilado = None

    def verifica(self, linha):
        if not self.ativo or not self.regex_compilado:
            return None
        
        match = self.regex_compilado.match(linha)
        if not match:
            return None

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
            'som_volume': self.som_volume,
            'escopo': self.escopo
        }