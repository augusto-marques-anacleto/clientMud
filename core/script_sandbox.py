import ast
import re as _re

BUILTINS_SEGUROS = {
    '__name__': '__script__',
    'True': True, 'False': False, 'None': None,
    'print': print,
    'range': range, 'len': len,
    'int': int, 'float': float, 'str': str, 'bool': bool,
    'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
    'abs': abs, 'min': min, 'max': max, 'round': round, 'sum': sum,
    'sorted': sorted, 'reversed': reversed,
    'enumerate': enumerate, 'zip': zip,
    'any': any, 'all': all,
    'isinstance': isinstance, 'repr': repr, 'format': format,
    'Exception': Exception, 'ValueError': ValueError,
    'TypeError': TypeError, 'TimeoutError': TimeoutError,
    'KeyError': KeyError, 'IndexError': IndexError,
    'StopIteration': StopIteration,
}

_NOMES_PROIBIDOS = frozenset({
    'eval', 'exec', 'compile', 'open', '__import__',
    'globals', 'locals', 'vars', 'dir', 'breakpoint',
    'input', 'memoryview', 'object', 'type',
})

_RE_WAIT = _re.compile(r'^#?wait\s+([\d.]+)\s*$', _re.IGNORECASE)
_RE_PLAY = _re.compile(r'^#?play\s+(\S+?)(?:\s+v=(\d+))?\s*$', _re.IGNORECASE)


def _validar_ast(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise ValueError("'import' não é permitido em scripts.")
        if isinstance(node, ast.Attribute) and isinstance(node.attr, str):
            if node.attr.startswith('__') and node.attr.endswith('__'):
                raise ValueError(f"Acesso a dunder proibido: '{node.attr}'")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in _NOMES_PROIBIDOS:
                raise ValueError(f"Chamada proibida: '{node.func.id}'")


def preprocessar(codigo):
    """
    Converte o código para async def script(): em 3 modos progressivos.

    Modo 1 — Já define 'async def script' (com ou sem ctx) → passa direto
    Modo 2 — Python válido sem def script → envolve em async def script():
    Modo 3 — Modo simples: cada linha é um comando ou 'wait N'
    """
    if not codigo or not codigo.strip():
        return "async def script():\n    pass\n"

    # Modo 1: o usuário escreveu a função explicitamente
    try:
        tree = ast.parse(codigo)
        for node in tree.body:
            if isinstance(node, ast.AsyncFunctionDef) and node.name == 'script':
                return codigo
    except SyntaxError:
        pass

    # Modo 2: Python válido, envolve em wrapper async
    indentado = '\n'.join(
        ('    ' + l) if l.strip() else ''
        for l in codigo.splitlines()
    )
    codigo_wrapped = f"async def script():\n{indentado}\n    pass\n"
    try:
        ast.parse(codigo_wrapped)
        return codigo_wrapped
    except SyntaxError:
        pass

    # Modo 3: modo simples linha-a-linha
    linhas_py = ['async def script():']
    for linha in codigo.splitlines():
        for s in (seg.strip() for seg in linha.split(';')):
            if not s:
                continue
            sl = s.lower()
            if s.startswith('#') and not sl.startswith('#wait') and not sl.startswith('#play'):
                continue
            m_wait = _RE_WAIT.match(s)
            m_play = _RE_PLAY.match(s)
            if m_wait:
                linhas_py.append(f"    await wait({m_wait.group(1)})")
            elif m_play:
                vol = m_play.group(2) or '100'
                linhas_py.append(f'    await play("{m_play.group(1)}", {vol})')
            else:
                esc = s.replace('\\', '\\\\').replace('"', '\\"')
                linhas_py.append(f'    await send("{esc}")')
    if len(linhas_py) == 1:
        linhas_py.append('    pass')
    return '\n'.join(linhas_py)


def compilar_seguro(codigo):
    """Pré-processa, valida AST e compila. Lança SyntaxError ou ValueError."""
    codigo_proc = preprocessar(codigo)
    try:
        tree = ast.parse(codigo_proc)
    except SyntaxError as e:
        raise SyntaxError(f"Sintaxe inválida no script: {e}")
    _validar_ast(tree)
    return compile(tree, '<script>', 'exec')


def criar_namespace(ctx):
    """
    Namespace seguro para exec().

    Funções disponíveis no script (sem precisar de ctx):
        send(cmd)               — envia comando ao MUD
        wait(n)                 — pausa não-bloqueante em segundos
        waitfor(regex, timeout) — aguarda linha do MUD; retorna MatchResult
        setvar(chave, valor)    — salva variável global persistente
        getvar(chave, padrao)   — lê variável global (retorna padrao se não existir)
        grupo(i)                — captura i do padrão da trigger (0, 1, 2...)
        linha()                 — linha completa que disparou a trigger
        cancelar_outros()       — cancela outras instâncias deste script
        ativar_grupo(nome)      — ativa todos os triggers do grupo
        desativar_grupo(nome)   — desativa todos os triggers do grupo

    O objeto ctx ainda está disponível para scripts antigos.
    """

    async def send(comando):
        await ctx.send(comando)

    async def wait(segundos):
        await ctx.wait(segundos)

    async def waitfor(padrao, timeout=30):
        return await ctx.wait_for(padrao, timeout)

    async def cancelar_outros(nome_trigger=None):
        await ctx.cancelar_outros(nome_trigger)

    async def play(arquivo, v=100):
        app = ctx._engine._app
        if app:
            app.msp.sound(str(arquivo), int(v))

    def setvar(chave, valor):
        ctx.vars[chave] = valor

    def getvar(chave, padrao=None):
        return ctx.vars.get(chave, padrao)

    def grupo(i):
        return ctx.grupos[i] if 0 <= i < len(ctx.grupos) else ''

    def linha():
        return ctx.linha

    def ativar_grupo(nome_grupo):
        app = ctx._engine._app
        if not app:
            return
        frame = getattr(app, 'janela_principal', None)
        if not frame:
            return
        for t in frame.triggers:
            if getattr(t, 'grupo', '') == nome_grupo:
                t.ativo = True

    def desativar_grupo(nome_grupo):
        app = ctx._engine._app
        if not app:
            return
        frame = getattr(app, 'janela_principal', None)
        if not frame:
            return
        for t in frame.triggers:
            if getattr(t, 'grupo', '') == nome_grupo:
                t.ativo = False

    return {
        '__builtins__': BUILTINS_SEGUROS,
        # compatibilidade com scripts antigos
        'ctx': ctx,
        # módulo
        're': _re,
        # funções livres
        'send': send,
        'wait': wait,
        'waitfor': waitfor,
        'cancelar_outros': cancelar_outros,
        'play': play,
        'setvar': setvar,
        'getvar': getvar,
        'grupo': grupo,
        'linha': linha,
        'ativar_grupo': ativar_grupo,
        'desativar_grupo': desativar_grupo,
    }
