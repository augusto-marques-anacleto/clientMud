import re

_RE_CMD_REPEAT = re.compile(r'^#(\d+)\s+(.+)')
_RE_URL = re.compile(r'(https?://[^\s]+)')

def _aplica_vars_macro(texto, args):
    for i in range(len(args), 0, -1):
        texto = texto.replace(f'%{i}', args[i - 1])
    return texto.replace('%0', ' '.join(args))
