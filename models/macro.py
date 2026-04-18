class Macro:
    def __init__(self, dicionario=None):
        dicionario = dicionario or {}
        self.id = dicionario.get('id', None)
        self.nome = dicionario.get('nome', '')
        self.comandos = dicionario.get('comandos', '')
        self.espera = float(dicionario.get('espera', 0.1))
        self.ativo = dicionario.get('ativo', True)
        self.escopo = dicionario.get('escopo', 0)

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'comandos': self.comandos,
            'espera': self.espera,
            'ativo': self.ativo,
            'escopo': self.escopo
        }