import os
import subprocess
import sys


def reinicia_aplicativo(reabrir=True):
    """Encerra o aplicativo e, opcionalmente, o reabre.

    Detecta se está rodando a partir do código-fonte (``.py``/``.pyw``) ou do
    executável empacotado e monta o comando de reabertura de acordo. Quando
    ``reabrir`` é ``False``, apenas encerra o processo atual.
    """
    if reabrir:
        rodando_pelo_python = sys.argv[0].lower().endswith('.py') or sys.argv[0].lower().endswith('.pyw')

        if rodando_pelo_python:
            caminho_script = os.path.abspath(sys.argv[0])
            comando = [sys.executable, caminho_script] + sys.argv[1:]
            pasta_trabalho = os.path.dirname(caminho_script) or os.getcwd()
        else:
            pasta_trabalho = os.getcwd()
            nome_exe = "clientmud.exe" if sys.platform == 'win32' else "clientmud"
            caminho_exe = os.path.join(pasta_trabalho, nome_exe)
            comando = [caminho_exe] + sys.argv[1:]

        subprocess.Popen(
            comando,
            cwd=pasta_trabalho,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    sys.exit(0)
