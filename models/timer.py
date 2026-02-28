import uuid

class Timer:
    def __init__(self, config_dict=None):
        if config_dict is None:
            config_dict = {}
            
        self.id = config_dict.get('id', str(uuid.uuid4()))
        self.nome = config_dict.get('nome', '')
        self.comando = config_dict.get('comando', '')
        self.intervalo = config_dict.get('intervalo', 60)
        self.ativo = config_dict.get('ativo', False)
        self.escopo = config_dict.get('escopo', 0)

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'comando': self.comando,
            'intervalo': self.intervalo,
            'ativo': self.ativo,
            'escopo': self.escopo
        }