import asyncio
import inspect
import re
import uuid
import wx
from collections import deque
from threading import Lock

from core.script_sandbox import compilar_seguro, criar_namespace


class ScriptVars:

    def __init__(self):
        self._d = {}
        self._lock = Lock()

    def __getitem__(self, k):
        with self._lock:
            return self._d[k]

    def __setitem__(self, k, v):
        with self._lock:
            self._d[k] = v

    def __contains__(self, k):
        with self._lock:
            return k in self._d

    def get(self, k, default=None):
        with self._lock:
            return self._d.get(k, default)

    def clear(self):
        with self._lock:
            self._d.clear()

    def items(self):
        with self._lock:
            return list(self._d.items())


class MatchResult:

    def __init__(self, linha, grupos):
        self.linha = linha
        self.grupos = list(grupos)
        self._seq = 0

    def __getitem__(self, i):
        return self.grupos[i] if 0 <= i < len(self.grupos) else ''

    def __len__(self):
        return len(self.grupos)

    def __repr__(self):
        return f"MatchResult({self.linha!r}, {self.grupos})"


class _Sub:
    __slots__ = ('regex', 'future')

    def __init__(self, regex, future):
        self.regex = regex
        self.future = future


class ScriptContext:

    def __init__(self, engine, grupos, linha, nome_trigger, id_exec):
        self._engine = engine
        self.grupos = list(grupos) if grupos else []
        self.linha = linha
        self.nome_trigger = nome_trigger
        self.id_exec = id_exec
        self._last_buf_seq = engine._buf_seq

    @property
    def vars(self):
        return self._engine.vars

    async def send(self, comando):
        app = self._engine._app
        if not app:
            return
        frame = getattr(app, 'janela_principal', None)
        for cmd in str(comando).split(';'):
            cmd = cmd.strip()
            if not cmd:
                continue
            if frame and not getattr(frame, 'janelaFechada', False):
                wx.CallAfter(frame.processa_e_envia_comando, cmd)
            else:
                app.client.enviaComando(cmd)

    async def wait(self, segundos):
        await asyncio.sleep(max(0.0, float(segundos)))

    async def wait_for(self, padrao, timeout=30):
        try:
            regex = re.compile(padrao, re.IGNORECASE)
        except re.error as e:
            raise ValueError(f"Padrão regex inválido '{padrao}': {e}")

        for seq, buf_linha in self._engine._buf:
            if seq <= self._last_buf_seq:
                continue
            m = regex.search(buf_linha)
            if m:
                result = MatchResult(buf_linha, m.groups())
                result._seq = seq
                self._last_buf_seq = seq
                return result

        self._last_buf_seq = self._engine._buf_seq
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        sub = _Sub(regex=regex, future=future)
        self._engine._subs.append(sub)
        try:
            result = await asyncio.wait_for(asyncio.shield(future), timeout=float(timeout))
            self._last_buf_seq = result._seq
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"wait_for('{padrao}') expirou após {timeout}s")
        finally:
            try:
                self._engine._subs.remove(sub)
            except ValueError:
                pass

    async def cancelar_outros(self, nome_trigger=None):
        nome = nome_trigger or self.nome_trigger
        await self._engine._cancelar_por_nome(nome, exceto=self.id_exec)


class ScriptEngine:

    MAX_CONCORRENTES = 30
    TIMEOUT_PADRAO = 7200

    def __init__(self, async_loop):
        self._loop = async_loop
        self._app = None
        self._tasks = {}
        self._tlock = Lock()
        self._subs = []
        self._buf = deque(maxlen=200)
        self._buf_seq = 0
        self._cache_compilado = {}
        self.vars = ScriptVars()

    def set_app(self, app):
        self._app = app

    def disparar(self, codigo, grupos, linha, nome_trigger='', concorrencia='nova'):
        id_exec = str(uuid.uuid4())[:8]
        with self._tlock:
            n_ativos = sum(1 for t in self._tasks.values() if t is None or not t.done())
            if n_ativos >= self.MAX_CONCORRENTES:
                return

            rodando = [
                (tid, t) for tid, t in self._tasks.items()
                if t is not None and getattr(t, '_nome_trigger', '') == nome_trigger and not t.done()
            ]
            if concorrencia == 'ignorar' and rodando:
                return
            if concorrencia == 'reiniciar':
                for _, t in rodando:
                    self._loop.loop.call_soon_threadsafe(t.cancel)

            self._tasks[id_exec] = None

        ctx = ScriptContext(
            engine=self,
            grupos=grupos,
            linha=linha,
            nome_trigger=nome_trigger,
            id_exec=id_exec,
        )
        asyncio.run_coroutine_threadsafe(
            self._executar(codigo, ctx, nome_trigger, id_exec),
            self._loop.loop,
        )

    def publicar_linha(self, linha):
        if not self._subs:
            return
        asyncio.run_coroutine_threadsafe(self._notificar(linha), self._loop.loop)

    def cancelar_tudo(self):
        with self._tlock:
            tasks = list(self._tasks.values())
        for t in tasks:
            if t is not None and not t.done():
                self._loop.loop.call_soon_threadsafe(t.cancel)
        asyncio.run_coroutine_threadsafe(self._zera_subs(), self._loop.loop)

    async def _notificar(self, linha):
        self._buf_seq += 1
        seq = self._buf_seq
        self._buf.append((seq, linha))

        rem = []
        for sub in self._subs:
            if sub.future.done():
                rem.append(sub)
                continue
            m = sub.regex.search(linha)
            if m:
                result = MatchResult(linha, m.groups())
                result._seq = seq
                sub.future.set_result(result)
                rem.append(sub)
        for sub in rem:
            try:
                self._subs.remove(sub)
            except ValueError:
                pass

    async def _executar(self, codigo, ctx, nome_trigger, id_exec):
        task = asyncio.current_task()
        if task:
            task._nome_trigger = nome_trigger
        with self._tlock:
            self._tasks[id_exec] = task

        try:
            if codigo not in self._cache_compilado:
                self._cache_compilado[codigo] = compilar_seguro(codigo)
            codigo_compilado = self._cache_compilado[codigo]
        except (SyntaxError, ValueError) as e:
            wx.CallAfter(self._log_erro, nome_trigger, str(e))
            with self._tlock:
                self._tasks.pop(id_exec, None)
            return

        namespace = criar_namespace(ctx)
        try:
            exec(codigo_compilado, namespace)
            fn = namespace.get('script')
            if fn is None:
                return
            try:
                tem_params = bool(inspect.signature(fn).parameters)
            except (ValueError, TypeError):
                tem_params = False
            if asyncio.iscoroutinefunction(fn):
                coro = fn(ctx) if tem_params else fn()
                await asyncio.wait_for(coro, timeout=self.TIMEOUT_PADRAO)
            else:
                fn(ctx) if tem_params else fn()
        except asyncio.TimeoutError:
            wx.CallAfter(self._log_erro, nome_trigger,
                         f"Timeout de {self.TIMEOUT_PADRAO}s atingido.")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            wx.CallAfter(self._log_erro, nome_trigger, f"{type(e).__name__}: {e}")
        finally:
            with self._tlock:
                self._tasks.pop(id_exec, None)

    async def _cancelar_por_nome(self, nome_trigger, exceto=None):
        with self._tlock:
            alvos = [
                t for tid, t in self._tasks.items()
                if t is not None and getattr(t, '_nome_trigger', '') == nome_trigger
                and tid != exceto
                and not t.done()
            ]
        for t in alvos:
            t.cancel()

    async def _zera_subs(self):
        for sub in list(self._subs):
            if not sub.future.done():
                sub.future.cancel()
        self._subs.clear()

    def _log_erro(self, nome_trigger, msg):
        app = self._app
        if not app:
            return
        frame = getattr(app, 'janela_principal', None)
        if not frame:
            return
        saida = getattr(frame, 'saida', None)
        if not saida:
            return
        try:
            saida.AppendText(f"[Script '{nome_trigger}'] ERRO: {msg}\n")
            saida.SetInsertionPointEnd()
        except RuntimeError:
            pass
