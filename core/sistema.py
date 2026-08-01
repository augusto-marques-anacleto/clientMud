import contextlib
import io
import os
import subprocess
import sys


def _le_configuracao_voz_orca(chave):
    """Lê uma chave do perfil de voz padrão do Orca (gsettings/dconf).
    Retorna None se o Orca não estiver instalado, não tiver essa
    configuração definida, ou em qualquer outra plataforma."""
    if sys.platform != 'linux':
        return None
    try:
        resultado = subprocess.run(
            ['gsettings', 'get', 'org.gnome.Orca.Voice:/org/gnome/orca/default/voices/default/', chave],
            capture_output=True, text=True, timeout=2
        )
    except Exception:
        return None
    if resultado.returncode != 0:
        return None
    valor = resultado.stdout.strip()
    if valor.startswith("'") and valor.endswith("'"):
        valor = valor[1:-1]
    return valor or None


def _idioma_e_taxa_do_orca():
    """Descobre o idioma e a taxa de fala que o próprio Orca está usando
    (para servir de padrão quando o usuário não escolheu nada manualmente
    na tela de sintetizador); cai para o idioma do sistema e taxa neutra se
    o Orca não estiver disponível."""
    idioma = _le_configuracao_voz_orca('family-lang')
    dialeto = _le_configuracao_voz_orca('family-dialect')
    if not idioma:
        idioma = os.environ.get('LANG', 'pt_BR.UTF-8').split('.')[0].split('_')[0]
        dialeto = dialeto or os.environ.get('LANG', 'pt_BR.UTF-8').split('.')[0].split('_')[-1]
    codigo_idioma = f'{idioma}-{dialeto}' if dialeto and dialeto != idioma else idioma

    taxa_str = _le_configuracao_voz_orca('rate')
    try:
        taxa = int(taxa_str) if taxa_str is not None else 0
    except ValueError:
        taxa = 0
    taxa = max(-100, min(100, taxa))
    return codigo_idioma, taxa


def _configura_cliente_speechd(cliente, preferencias=None):
    """Aplica idioma/taxa/volume/módulo/voz na conexão. Qualquer valor não
    definido explicitamente em `preferencias` (dict vindo de
    gerais.voz-linux no config.json) cai para o que o Orca já usa, para que
    a fala do ClientMUD combine com a do leitor de tela por padrão, sem
    exigir nenhuma configuração manual."""
    preferencias = preferencias or {}
    codigo_idioma, taxa_auto = _idioma_e_taxa_do_orca()

    taxa = preferencias.get('taxa')
    taxa = int(taxa) if taxa is not None else taxa_auto
    taxa = max(-100, min(100, taxa))

    volume = preferencias.get('volume')
    volume = max(-100, min(100, int(volume))) if volume is not None else 0

    modulo = preferencias.get('modulo') or None
    voz = preferencias.get('voz') or None

    if hasattr(cliente, 'set_language'):
        try:
            cliente.set_language(codigo_idioma)
        except Exception:
            pass
    if hasattr(cliente, 'set_rate'):
        try:
            cliente.set_rate(taxa)
        except Exception:
            pass
    if hasattr(cliente, 'set_volume'):
        try:
            cliente.set_volume(volume)
        except Exception:
            pass
    if modulo and hasattr(cliente, 'set_output_module'):
        try:
            cliente.set_output_module(modulo)
        except Exception:
            pass
    if voz and hasattr(cliente, 'set_synthesis_voice'):
        try:
            cliente.set_synthesis_voice(voz)
        except Exception:
            pass


def listar_modulos_saida():
    """Lista os módulos sintetizadores disponíveis no speech-dispatcher
    (ex.: espeak-ng, festival). Retorna lista vazia fora do Linux ou se o
    speech-dispatcher não estiver disponível."""
    if sys.platform != 'linux':
        return []
    try:
        import speechd
        cliente = speechd.SSIPClient('clientmud-consulta')
        try:
            return list(cliente.list_output_modules())
        finally:
            cliente.close()
    except Exception:
        return []


def listar_vozes(modulo=None):
    """Lista as vozes disponíveis (nome, idioma, variante) para o módulo
    informado (ou o módulo padrão do speech-dispatcher, se não informado)."""
    if sys.platform != 'linux':
        return []
    try:
        import speechd
        cliente = speechd.SSIPClient('clientmud-consulta')
        try:
            if modulo:
                cliente.set_output_module(modulo)
            return list(cliente.list_synthesis_voices())
        finally:
            cliente.close()
    except Exception:
        return []


def testar_voz(texto, preferencias=None):
    """Fala um texto de teste usando as preferências informadas, sem afetar
    as conexões de fala já em uso pelo restante do aplicativo. Usado pelo
    botão 'Testar' da tela de sintetizador."""
    if sys.platform != 'linux':
        return
    try:
        import speechd
        cliente = speechd.SSIPClient('clientmud-teste-voz')
        _configura_cliente_speechd(cliente, preferencias)
        cliente.speak(texto)
    except Exception:
        pass


def cria_saida_voz(preferencias_linux=None):
    """Cria a saída de fala principal (accessible_output2), usada para
    avisos pontuais da interface (confirmações, menus, diálogos etc).
    Silencia o aviso inofensivo que a biblioteca imprime no console quando
    um backend opcional (ex.: eSpeak puro) não está instalado mas também
    não será usado."""
    from accessible_output2 import outputs
    with contextlib.redirect_stdout(io.StringIO()):
        saida = outputs.auto.Auto()

    if sys.platform != 'win32':
        # No Linux, o accessible_output2 fala diretamente pelo
        # speech-dispatcher (o mesmo motor que o Orca usa por trás), mas
        # numa conexão própria que por padrão não herda nem o idioma, a
        # velocidade, o volume, o módulo ou a voz configurados no Orca ou
        # pelo usuário -- sem isso, tudo sai em inglês e numa velocidade que
        # não bate com a que o usuário já escolheu.
        for saida_individual in getattr(saida, 'outputs', []):
            cliente = getattr(saida_individual, '_client', None)
            if cliente is not None:
                _configura_cliente_speechd(cliente, preferencias_linux)

    return saida


def cria_leitor_de_mensagens(saida_padrao, preferencias_linux=None):
    """Retorna a função usada para ler automaticamente o texto que chega do
    MUD (opção 'ler mensagens automaticamente' / leitura fora da janela).

    No Windows, o NVDA/JAWS gerencia sua própria fila de fala internamente,
    então o texto do jogo e os avisos do próprio leitor de tela nunca
    competem entre si. No Linux não existe esse gerenciamento único: o
    Orca fala através do speech-dispatcher e o ClientMUD, ao chamar
    accessible_output2, abre uma conexão *separada* e não coordenada com o
    mesmo speech-dispatcher. A conexão usa prioridade 'text' (a mesma que o
    Orca usa por padrão), com fila normal -- nada é descartado. Quem evita a
    fila crescer sem limite num MUD falante é o lado do chamador
    (core/processor.py), que agrupa linhas que chegam juntas numa fala só e
    interrompe apenas o agrupamento anterior *dele mesmo*, nunca a fala do
    Orca (o comando CANCEL do SSIP só afeta mensagens do próprio cliente que
    o emitiu).

    A função retornada tem um atributo `.parar` (só no Linux) que interrompe
    a fala em andamento dessa conexão -- usado pela tecla configurável de
    'interromper leitura'."""
    if sys.platform != 'linux':
        return saida_padrao.speak

    try:
        import speechd
        cliente = speechd.SSIPClient('clientmud-mensagens-mud')
        _configura_cliente_speechd(cliente, preferencias_linux)
    except Exception:
        return saida_padrao.speak

    def fala(texto, interrupt=False, *args, **kwargs):
        try:
            if interrupt:
                cliente.cancel()
            cliente.speak(texto)
        except Exception:
            pass

    def parar():
        try:
            cliente.cancel()
        except Exception:
            pass

    fala.parar = parar
    return fala


def abrir_pasta(caminho):
    """Abre o gerenciador de arquivos do sistema operacional na pasta informada."""
    caminho = str(caminho)
    if sys.platform == 'win32':
        subprocess.Popen(["explorer", caminho])
    elif sys.platform == 'darwin':
        subprocess.Popen(["open", caminho])
    else:
        subprocess.Popen(["xdg-open", caminho])
