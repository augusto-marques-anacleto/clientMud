import asyncio
import importlib.util
import json
from pathlib import Path
from threading import Lock

import wx


class ContextoScriptExterno:

    def __init__(self, app_ref, log_fn):
        self._app = app_ref
        self._log_fn = log_fn
        self._parar = False

    @property
    def conectado(self):
        if self._parar:
            return False
        cliente = getattr(self._app, 'client', None)
        return cliente is not None and cliente.ativo

    async def send(self, comando):
        if not self.conectado:
            return
        frame = getattr(self._app, 'janela_principal', None)
        if frame and not getattr(frame, 'janelaFechada', False):
            wx.CallAfter(frame.processa_e_envia_comando, str(comando))
        else:
            self._app.client.enviaComando(str(comando))

    def log(self, msg):
        self._log_fn(str(msg))

    def parar(self):
        self._parar = True


class GerenciadorScriptsExternos:

    def __init__(self):
        self._ctxs = {}
        self._tasks_asyncio = {}
        self._loop_ref = None
        self._lock = Lock()

    def iniciar(self, habilitados, pasta_scripts, app_ref, loop):
        self._loop_ref = loop
        pasta = Path(pasta_scripts)
        for nome in habilitados:
            caminho = pasta / nome
            if caminho.exists() and caminho.suffix == '.py':
                self._iniciar_um(nome, caminho, app_ref, loop)

    def _make_log(self, app_ref):
        def log(msg):
            frame = getattr(app_ref, 'janela_principal', None)
            if frame:
                saida = getattr(frame, 'saida', None)
                if saida:
                    try:
                        wx.CallAfter(saida.AppendText, f"{msg}\n")
                    except Exception:
                        pass
        return log

    def _iniciar_um(self, nome, caminho, app_ref, loop):
        with self._lock:
            if nome in self._ctxs:
                return

        log_fn = self._make_log(app_ref)
        ctx = ContextoScriptExterno(app_ref, log_fn)

        try:
            spec = importlib.util.spec_from_file_location(f"ext_{nome[:-3]}", str(caminho))
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
        except Exception as e:
            log_fn(f"[Scripts Externos] Erro ao carregar '{nome}': {e}")
            return

        if not hasattr(modulo, 'main') or not asyncio.iscoroutinefunction(modulo.main):
            log_fn(f"[Scripts Externos] '{nome}' não define 'async def main(ctx)'. Ignorado.")
            return

        with self._lock:
            self._ctxs[nome] = ctx

        asyncio.run_coroutine_threadsafe(
            self._executar(modulo.main, ctx, nome, log_fn),
            loop.loop,
        )
        log_fn(f"[Scripts Externos] '{nome}' iniciado.")

    async def _executar(self, fn_main, ctx, nome, log_fn):
        task = asyncio.current_task()
        with self._lock:
            self._tasks_asyncio[nome] = task
        try:
            await fn_main(ctx)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            err_msg = f"[Scripts Externos] '{nome}' encerrou com erro: {type(e).__name__}: {e}"
            wx.CallAfter(log_fn, err_msg)
        finally:
            with self._lock:
                self._tasks_asyncio.pop(nome, None)
                self._ctxs.pop(nome, None)

    def parar_todos(self):
        with self._lock:
            for ctx in self._ctxs.values():
                ctx.parar()
            tarefas = list(self._tasks_asyncio.values())
            self._ctxs.clear()
            self._tasks_asyncio.clear()

        if self._loop_ref:
            for task in tarefas:
                self._loop_ref.loop.call_soon_threadsafe(task.cancel)

    @staticmethod
    def listar_scripts(pasta_scripts):
        pasta = Path(pasta_scripts)
        if not pasta.exists():
            return []
        return sorted(f.name for f in pasta.iterdir() if f.suffix == '.py')

    @staticmethod
    def carregar_habilitados(pasta_scripts):
        cfg = Path(pasta_scripts) / 'scripts_externos.json'
        if cfg.exists():
            try:
                dados = json.loads(cfg.read_text('utf-8'))
                return dados.get('habilitados', [])
            except Exception:
                pass
        return []

    @staticmethod
    def salvar_habilitados(pasta_scripts, habilitados):
        pasta = Path(pasta_scripts)
        pasta.mkdir(parents=True, exist_ok=True)
        cfg = pasta / 'scripts_externos.json'
        cfg.write_text(
            json.dumps({'habilitados': habilitados}, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
