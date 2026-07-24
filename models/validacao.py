"""Validação dos arquivos JSON de configuração (``config.json``) e de personagem.

Cada validador confere a presença e o tipo dos campos obrigatórios — aqueles que
não têm como assumir um valor padrão sensato, como o ``nome``, o ``endereço`` e a
``porta`` do personagem, ou o diretório de dados do ``config``. Os campos
opcionais (em geral caixas de seleção e listas) recebem um valor padrão quando
ausentes, sem que isso invalide o arquivo.

Os validadores devem ser chamados sempre que os respectivos JSONs forem lidos.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Personagem
# ---------------------------------------------------------------------------

# Campos opcionais do JSON do personagem e seus valores padrão. São, em sua
# maioria, caixas de seleção (booleanos) e listas de configurações, para os
# quais é seguro assumir um padrão quando ausentes.
PADROES_PERSONAGEM = {
    'senha': '',
    'login_automático': False,
    'conexao_segura': False,
    'reproduzir_sons_fora_janela': True,
    'ler_fora_janela': True,
    'usar_volume_padrao': False,
    'volume_padrao': 100,
    'ignorar_urls_msp': False,
    'modo_escuro': True,
    'triggers': [],
    'timers': [],
    'keys': [],
    'macros': [],
}


def valida_personagem(dados):
    """Valida (e normaliza) o JSON de um personagem.

    Retorna a tupla ``(valido, dados)``. Quando ``valido`` é ``True`` o
    dicionário ``dados`` já vem com os campos opcionais preenchidos com seus
    valores padrão. São obrigatórios ``nome``, ``endereço`` e ``porta``; sem
    eles o personagem não pode ser utilizado.
    """
    if not isinstance(dados, dict):
        return False, dados

    nome = dados.get('nome')
    if not isinstance(nome, str) or not nome.strip():
        return False, dados

    endereco = dados.get('endereço')
    if not isinstance(endereco, str) or not endereco.strip():
        return False, dados

    porta = dados.get('porta')
    # ``bool`` é subclasse de ``int``; precisa ser descartado explicitamente.
    if isinstance(porta, bool) or not isinstance(porta, int) or not (1 <= porta <= 65535):
        return False, dados

    for campo, padrao in PADROES_PERSONAGEM.items():
        dados.setdefault(campo, padrao)

    return True, dados


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Campos opcionais da seção ``gerais`` do ``config.json`` e seus valores padrão.
PADROES_CONFIG_GERAIS = {
    'toca-sons-fora-da-janela': True,
    'ler fora da janela': False,
    'ignorar-urls-msp': False,
    'verifica-atualizacoes-automaticamente': True,
    'ultima-conexao': [],
}


def valida_config(config):
    """Valida (e normaliza) o ``config.json``.

    Retorna a tupla ``(valido, config, alterado)``. É obrigatória a seção
    ``gerais`` contendo um ``diretorio-de-dados`` não vazio, além da lista
    ``personagens``. Os caminhos derivados (``logs``, ``scripts``, ``sons``) e
    demais campos opcionais são recompostos/preenchidos a partir de valores
    padrão quando ausentes, e ``alterado`` indica se algo foi normalizado (para
    que o chamador possa persistir o arquivo).
    """
    if not isinstance(config, dict):
        return False, config, False

    gerais = config.get('gerais')
    if not isinstance(gerais, dict):
        return False, config, False

    diretorio = gerais.get('diretorio-de-dados')
    if not isinstance(diretorio, str) or not diretorio.strip():
        return False, config, False

    if not isinstance(config.get('personagens'), list):
        return False, config, False

    alterado = False

    base = Path(diretorio) / 'clientmud'
    for campo, padrao in (('logs', base / 'logs'), ('scripts', base / 'scripts'), ('sons', base / 'sons')):
        valor = gerais.get(campo)
        if not isinstance(valor, str) or not valor.strip():
            gerais[campo] = str(padrao)
            alterado = True

    if not isinstance(gerais.get('pastas-dos-muds'), dict):
        gerais['pastas-dos-muds'] = {}
        alterado = True

    for campo, padrao in PADROES_CONFIG_GERAIS.items():
        if campo not in gerais:
            gerais[campo] = padrao
            alterado = True

    if not isinstance(config.get('configuracoes-globais'), dict):
        config['configuracoes-globais'] = {'triggers': [], 'timers': [], 'keys': [], 'macros': []}
        alterado = True

    return True, config, alterado
