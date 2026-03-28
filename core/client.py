import asyncio
from pathlib import Path
from datetime import datetime
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
        self.async_loop = async_loop
        self.fila_mensagens = queue.Queue()

    def conectaServidor(self, endereco, porta):
        future = self.async_loop.run(
            self._conectaServidor(endereco, porta)
        )
        return future.result() 

    async def _conectaServidor(self, endereco, porta):
        if self.nome is None:
            self.nome = endereco

        try:
            self.reader, self.writer = await asyncio.wait_for(
                telnetlib3.open_connection(
                    host=endereco,
                    port=porta,
                    connect_minwait=0.05,
                    connect_maxwait=3.0,
                    encoding=None
                ),
                timeout=5.0
            )

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

        except Exception:
            await self._terminaCliente()
            return False

    def enviaComando(self, comando):
        if not self.ativo:
            return
        self.async_loop.run(self._enviaComando(comando))

    async def _enviaComando(self, comando):
        try:
            if self.writer:
                comando_bytes = f"{comando}\r\n".encode('iso-8859-1', errors='replace')
                self.writer.write(comando_bytes)
                await self.writer.drain()
                self.salvaLog(comando)
        except Exception:
            await self._terminaCliente()

    def definePastaLog(self, pastaLog, nome=None):
        self.nome = nome
        self.pastaLog = Path(pastaLog)

    def terminaCliente(self):
        self.async_loop.run(self._terminaCliente())

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
                await self.writer.wait_closed()
        except Exception:
            pass

    def salvaLog(self, log):
        if log and self.arquivoLog and not self.arquivoLog.closed:
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
                    mensagem = mensagem_bruta.decode('iso-8859-1', errors='replace')
                else:
                    mensagem = str(mensagem_bruta)

                self.fila_mensagens.put(mensagem)

            except Exception:
                break                
        if self.ativo:
            await self._terminaCliente()