"""Testa a troca de arquivos do atualizador com arquivos presos na memória.

O Client Mud e o atualizador moram na mesma pasta e compartilham python313.dll,
libssl, os .pyd e as DLLs do wx. Enquanto o atualizador roda, esses arquivos
estão carregados na memória, e o Windows não deixa apagar nem sobrescrever
arquivo carregado. Já saiu versão em que a troca falhava exatamente aí, em
silêncio, deixando o clientmud.exe novo ao lado das DLLs velhas, sem abrir.

Este teste reproduz esse cenário e é rodado pelo CI antes de gerar a release.
Rodar na mão: python testes/teste_atualizador.py
"""
import ctypes
import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SISTEMA = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32'
CARREGAVEIS = {'python313.dll': SISTEMA / 'winmm.dll', 'wx/libssl-3.dll': SISTEMA / 'version.dll'}


def carrega_atualizador():
    spec = importlib.util.spec_from_file_location('atualizador', RAIZ / 'atualizador.pyw')
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def monta(base):
    instalacao = base / 'instalacao'
    pacote = base / 'upgrade' / 'clientmud'
    (instalacao / 'wx').mkdir(parents=True)
    pacote.mkdir(parents=True)

    for rel, origem in CARREGAVEIS.items():
        (pacote / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, instalacao / rel)
        (pacote / rel).write_bytes(b'conteudo novo de ' + rel.encode() + os.urandom(64))

    (instalacao / 'clientmud.exe').write_bytes(b'cliente antigo')
    (pacote / 'clientmud.exe').write_bytes(b'cliente novo')
    (pacote / 'arquivo_novo.pyd').write_bytes(b'arquivo que ainda nao existia')
    (instalacao / 'config.json').write_text('{"gerais": {}}', encoding='utf-8')
    return instalacao, pacote


def instancia(modulo, instalacao):
    a = object.__new__(modulo.Atualizador)
    a.pasta_local = instalacao
    a.pasta_atualizacao = instalacao.parent / 'upgrade'
    a.quarentena = instalacao / modulo.NOME_QUARENTENA
    a.arquivo = a.pasta_atualizacao / 'clientmud.zip'
    return a


def conteudos(raiz, ignorar=()):
    return {
        str(p.relative_to(raiz)).lower(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(raiz.rglob('*'))
        if p.is_file() and not str(p.relative_to(raiz)).lower().startswith(ignorar)
    }


def segura_arquivos(instalacao):
    """Sobe um processo que carrega as DLLs e as mantém presas na memória."""
    processo = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), '--segurar', str(instalacao)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
    )
    for linha in processo.stdout:
        if linha.strip() == 'PRONTO':
            break
    return processo


def solta(processo):
    processo.stdin.write('\n')
    processo.stdin.flush()
    processo.wait(timeout=30)


def teste_troca_arquivo_carregado(modulo):
    with tempfile.TemporaryDirectory() as tmp:
        instalacao, pacote = monta(Path(tmp))
        esperado = conteudos(pacote)
        processo = segura_arquivos(instalacao)
        try:
            for rel in CARREGAVEIS:
                try:
                    os.unlink(instalacao / rel)
                except PermissionError:
                    pass
                else:
                    raise AssertionError(f'{rel} deveria estar preso na memória e não está')

            instancia(modulo, instalacao).aplicar_pacote(pacote)
        finally:
            solta(processo)

        obtido = conteudos(instalacao, ignorar=(modulo.NOME_QUARENTENA.lower(),))
        for rel, hash_novo in esperado.items():
            if obtido.get(rel) != hash_novo:
                raise AssertionError(f'{rel} não foi substituído pelo arquivo novo')
        if (instalacao / 'config.json').read_text(encoding='utf-8') != '{"gerais": {}}':
            raise AssertionError('os dados do usuário foram alterados')
    print('ok: arquivos carregados na memória foram substituídos')


def teste_desfaz_quando_falha(modulo):
    with tempfile.TemporaryDirectory() as tmp:
        instalacao, pacote = monta(Path(tmp))
        antes = conteudos(instalacao)
        with open(instalacao / 'clientmud.exe', 'rb'):
            try:
                instancia(modulo, instalacao).aplicar_pacote(pacote)
            except OSError:
                pass
            else:
                raise AssertionError('a troca deveria ter falhado')

        depois = conteudos(instalacao, ignorar=(modulo.NOME_QUARENTENA.lower(),))
        if depois != antes:
            raise AssertionError('a instalação não voltou ao estado original')
    print('ok: falha no meio da troca desfaz tudo')


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--segurar':
        ctypes.windll.kernel32.SetErrorMode(0x8003)
        presas = [ctypes.WinDLL(str(Path(sys.argv[2]) / rel)) for rel in CARREGAVEIS]
        print('PRONTO', flush=True)
        sys.stdin.readline()
        sys.exit(0)

    atualizador = carrega_atualizador()
    teste_troca_arquivo_carregado(atualizador)
    teste_desfaz_quando_falha(atualizador)
    print('todos os testes do atualizador passaram')
