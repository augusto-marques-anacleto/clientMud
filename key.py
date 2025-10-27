import uuid

class Key:
	def __init__(self, config_dict=None):
		if config_dict is None:
			config_dict = {}
		self.id = config_dict.get('id', str(uuid.uuid4()))
		self.nome = config_dict.get('nome', '')
		self.tecla = config_dict.get('tecla', '')
		self.comando = config_dict.get('comando', '')
		self.ativo = config_dict.get('ativo', True)

	def verifica(self, tecla_pressionada):
		"""Retorna True se a tecla pressionada corresponde ao atalho configurado."""
		return self.ativo and tecla_pressionada == self.tecla

	def to_dict(self):
		return {
			'id': self.id,
			'nome': self.nome,
			'tecla': self.tecla,
			'comando': self.comando,
			'ativo': self.ativo
		}
