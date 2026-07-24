import asyncio
import ssl
from pathlib import Path
from datetime import datetime
from threading import Lock
import telnetlib3
import wx
import queue

class Cliente:

    def __init__(self, async_loop):
        self.ativo = False
        self.arquivoLog = None
        self.nome = None
        self.pastaLog = None
        self.reader = None
        self.writer = None
        self.endereco = None
        self.porta = None
        self.task_leitura = None
        self.ssl_ativo = False
        self.async_loop = async_loop
        self.fila_mensagens = queue.Queue()
        self._lock_log = Lock()
        self.log = None
        self._log_pausado = False
        self._buffer_log_pendente = []

    @property
    def conexao_ativa(self):
        return self.ativo and self.reader is not None and not self.reader.at_eof()

    def conectaServidor(self, endereco, porta, usar_ssl=False):
        future = self.async_loop.run(
            self._conectaServidor(endereco, porta, usar_ssl)
        )
        return future.result()

    async def _conectaServidor(self, endereco, porta, usar_ssl=False):
        if self.nome is None:
            self.nome = endereco

        conectado = await self._abreConexao(endereco, porta, usar_ssl)

        if not conectado:
            await self._terminaCliente()
            return False

        self.ativo = True

        if self.pastaLog:
            log_name = datetime.now().strftime(f"{self.nome} %Hh %Mmin %d.%m.%Y.txt")
            self.log = self.pastaLog / log_name
            self.arquivoLog = self.log.open(mode="a+", encoding="utf-8")

        self.endereco = endereco
        self.porta = porta
        self.task_leitura = asyncio.get_running_loop().create_task(
            self.loopRecebimento()
        )
        return True

    async def _abreConexao(self, endereco, porta, usar_ssl):
        contexto = None
        if usar_ssl:
            contexto = ssl.create_default_context()
            contexto.check_hostname = False
            contexto.verify_mode = ssl.CERT_NONE

        try:
            self.reader, self.writer = await asyncio.wait_for(
                telnetlib3.open_connection(
                    host=endereco,
                    port=porta,
                    connect_minwait=0.05,
                    connect_maxwait=3.0,
                    encoding=None,
                    ssl=contexto,
                    server_hostname=endereco if usar_ssl else None
                ),
                timeout=5.0
            )
            self.ssl_ativo = usar_ssl
            return True
        except Exception:
            self.reader = None
            self.writer = None
            return False

    def enviaComando(self, comando):
        if not self.ativo: return
        self.async_loop.run(self._enviaComando(comando))

    async def _enviaComando(self, comando):
        try:
            if self.writer:
                comando_bytes = f"{comando}\r\n".encode('iso-8859-1', errors='replace')
                self.writer.write(comando_bytes)
                await self.writer.drain()
                asyncio.get_running_loop().run_in_executor(None, self.salvaLog, comando)
        except Exception:
            await self._terminaCliente()

    def definePastaLog(self, pastaLog, nome=None):
        self.nome = nome
        self.pastaLog = Path(pastaLog)

    def pausaLog(self):
        """Fecha o arquivo de log atual e passa a acumular em memória as
        mensagens que chegarem, para não perdê-las durante uma operação que
        precise do arquivo fechado (ex.: renomear a pasta do personagem).
        Retorna o caminho do log que estava aberto, ou None."""
        with self._lock_log:
            log_atual = self.log if (self.arquivoLog and not self.arquivoLog.closed) else None
            try:
                if self.arquivoLog and not self.arquivoLog.closed:
                    self.arquivoLog.close()
            except Exception:
                pass
            self.arquivoLog = None
            self._log_pausado = True
            return log_atual

    def retomaLog(self, caminho_log):
        """Reabre o log no caminho informado e grava as mensagens que chegaram
        enquanto o log estava pausado, preservando a ordem."""
        with self._lock_log:
            if caminho_log:
                self.log = Path(caminho_log)
            try:
                if self.log:
                    self.arquivoLog = self.log.open(mode="a+", encoding="utf-8")
                    for linha in self._buffer_log_pendente:
                        self.arquivoLog.write(f"{linha}\n")
                    self.arquivoLog.flush()
            except Exception:
                pass
            self._buffer_log_pendente = []
            self._log_pausado = False

    def terminaCliente(self):
        future = self.async_loop.run(self._terminaCliente())
        try:
            future.result(timeout=3.0)
        except Exception:
            pass

    async def _terminaCliente(self):
        if not self.ativo: return
        self.ativo = False
        try:
            tarefa_atual = asyncio.current_task()
            if self.task_leitura and self.task_leitura != tarefa_atual:
                self.task_leitura.cancel()
        except Exception:
            pass
        try:
            if self.arquivoLog and not self.arquivoLog.closed:
                self.arquivoLog.close()
        except Exception:
            pass
        try:
            if self.writer:
                self.writer.close()
                try:
                    await asyncio.wait_for(self.writer.wait_closed(), timeout=2.0)
                except (asyncio.TimeoutError, Exception):
                    pass
        except Exception:
            pass

    def salvaLog(self, log):
        if not log:
            return
        with self._lock_log:
            if self._log_pausado:
                self._buffer_log_pendente.append(log)
                return
            if self.arquivoLog and not self.arquivoLog.closed:
                try:
                    self.arquivoLog.write(f"{log}\n")
                    self.arquivoLog.flush()
                except OSError:
                    pass

    async def loopRecebimento(self):
        while self.ativo:
            try:
                mensagem_bruta = await self.reader.read(4096)

                if not mensagem_bruta:
                    break

                if isinstance(mensagem_bruta, bytes):
                    try:
                        mensagem = mensagem_bruta.decode('utf-8')
                    except UnicodeDecodeError:
                        mensagem = mensagem_bruta.decode('iso-8859-1', errors='replace')
                else:
                    mensagem = str(mensagem_bruta)

                self.fila_mensagens.put(mensagem)

            except Exception:
                break                
        if self.ativo:
            await self._terminaCliente()