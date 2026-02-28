import os
from pathlib import Path
from time import sleep
from datetime import datetime
from lib.telnetlib import Telnet

class Cliente(Telnet):
    def __init__(self):
        super().__init__()
        self.ativo = False
        self.arquivoLog = None
        self.nome = None
        self.pastaLog = None

    def enviaComando(self, comando):
        try:
            self.write(f'{comando}\r\n'.encode("latin-1", errors="replace"))
            self.salvaLog(comando)
        except:
            self.terminaCliente()

    def conectaServidor(self, endereco, porta):
        if self.nome is None: self.nome = endereco
        self.connect_timeout = 3.0
        try:
            self.open(endereco, porta)
            self.ativo = True
            if self.pastaLog:
                log_name = datetime.now().strftime(f"{self.nome} %Hh %Mmin %d.%m.%Y.txt")
                self.log = self.pastaLog / log_name
                self.arquivoLog = self.log.open(mode="a+", encoding="utf-8")
            self.endereco = endereco
            self.porta = porta
            return True
        except Exception:
            self.terminaCliente()
            return False

    def recebeMensagem(self):
        try:
            mensagem = self.read_very_eager()
            return mensagem if mensagem else None
        except:
            self.terminaCliente()
            return None

    def definePastaLog(self, pastaLog, nome=None):
        self.nome = nome
        self.pastaLog = Path(pastaLog)

    def terminaCliente(self):
        self.ativo = False
        try:
            if self.arquivoLog and not self.arquivoLog.closed:
                self.arquivoLog.close()
        except:
            pass
        try:
            self.close()
        except:
            pass

    def salvaLog(self, log):
        if log and self.arquivoLog and not self.arquivoLog.closed:
            try:
                self.arquivoLog.write(f'{log}\n')
                self.arquivoLog.flush()
            except OSError:
                pass