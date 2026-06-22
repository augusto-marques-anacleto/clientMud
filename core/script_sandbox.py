import ast
import re as _re
import wx

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

_RE_WAIT  = _re.compile(r'^#?wait\s+([\d.]+)\s*$',              _re.IGNORECASE)
_RE_PLAY  = _re.compile(r'^#?play\s+(\S+?)(?:\s+v=(\d+))?\s*$',  _re.IGNORECASE)
_RE_MUSIC = _re.compile(r'^#?music\s+(\S+?)(?:\s+v=(\d+))?\s*$', _re.IGNORECASE)
_RE_STOP  = _re.compile(r'^#?stop\s*$',                           _re.IGNORECASE)


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
    if not codigo or not codigo.strip():
        return "async def script():\n    pass\n"

    try:
        tree = ast.parse(codigo)
        for node in tree.body:
            if isinstance(node, ast.AsyncFunctionDef) and node.name == 'script':
                return codigo
    except SyntaxError:
        pass

    if not _re.search(r'^\s*#(?:wait|play|music|stop)\b', codigo, _re.IGNORECASE | _re.MULTILINE):
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

    linhas_py = ['async def script():']
    for linha in codigo.splitlines():
        for s in (seg.strip() for seg in linha.split(';')):
            if not s:
                continue
            sl = s.lower()
            if s.startswith('#') and not sl.startswith('#wait') and not sl.startswith('#play') and not sl.startswith('#music') and not sl.startswith('#stop'):
                continue
            m_wait  = _RE_WAIT.match(s)
            m_play  = _RE_PLAY.match(s)
            m_music = _RE_MUSIC.match(s)
            m_stop  = _RE_STOP.match(s)
            if m_wait:
                linhas_py.append(f"    await wait({m_wait.group(1)})")
            elif m_play:
                vol = m_play.group(2) or '100'
                linhas_py.append(f'    await play("{m_play.group(1)}", {vol})')
            elif m_music:
                vol = m_music.group(2) or '100'
                linhas_py.append(f'    await music("{m_music.group(1)}", {vol})')
            elif m_stop:
                linhas_py.append('    await stop()')
            else:
                esc = s.replace('\\', '\\\\').replace('"', '\\"')
                linhas_py.append(f'    await send("{esc}")')
    if len(linhas_py) == 1:
        linhas_py.append('    pass')
    return '\n'.join(linhas_py)


def compilar_seguro(codigo):
    codigo_proc = preprocessar(codigo)
    try:
        tree = ast.parse(codigo_proc)
    except SyntaxError as e:
        raise SyntaxError(f"Sintaxe inválida no script: {e}")
    _validar_ast(tree)
    return compile(tree, '<script>', 'exec')


def criar_namespace(ctx):
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
            wx.CallAfter(app.msp.sound, str(arquivo), int(v))

    async def music(arquivo, v=100):
        app = ctx._engine._app
        if app:
            wx.CallAfter(app.msp.music, str(arquivo), int(v))

    async def stop():
        app = ctx._engine._app
        if app:
            wx.CallAfter(app.msp.soundOff)

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
        'ctx': ctx,
        're': _re,
        'send': send,
        'wait': wait,
        'waitfor': waitfor,
        'cancelar_outros': cancelar_outros,
        'play': play,
        'music': music,
        'stop': stop,
        'setvar': setvar,
        'getvar': getvar,
        'grupo': grupo,
        'linha': linha,
        'ativar_grupo': ativar_grupo,
        'desativar_grupo': desativar_grupo,
    }
