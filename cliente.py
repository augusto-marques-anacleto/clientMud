import os
from telnetlib import Telnet
from pathlib import Path
from time import sleep
from datetime import datetime
if os.name == 'nt': # 'nt' é o nome para Windows
    import msvcrt
else:
    msvcrt = None # Garante que msvcrt não seja usado em outros OS
class Cliente(Telnet):
        def __init__(self):
                self.ativo = False
        def enviaComando(self, comando):
                try:
                        self.write(f'{comando}\r\n'.encode("latin-1", errors="replace"))
#                        self.salvaLog(comando)
                except:
                        self.close()
        def conectaServidor(self, endereco, porta):
                if self.nome==None:
                        self.nome=endereco
                try:
                        super().__init__(endereco, porta)
                        self.connect_timeout = 3.0
                        self.ativo=True
                except:
                        return False
                else:
                        log=datetime.now().strftime(f"{self.nome} %Hh %Mmin %d.%m.%Y.txt")
                        self.log=self.pastaLog / log
                        self.arquivoLog = self.log.open(mode="a+")
                        self.endereco = endereco
                        self.porta = porta
                        return True
        def recebeMensagem(self):
                try:
                        mensagem = self.read_very_eager()
                        if mensagem:
                                return mensagem
                        else:
                                return mensagem
                except:
                        self.ativo=False
                        self.eof = True
                        self.close()
        def definePastaLog(self, pastaLog, nome=None):
                self.nome = nome
                self.pastaLog= Path(pastaLog)
        def terminaCliente(self):
                self.ativo=False
                self.close()
        def salvaLog(self, log):
                if log:
                        self.arquivoLog.write(f'{log}\n')
                        self.arquivoLog.flush()
                        if os.name == 'posix':
                                os.fsync(self.arquivoLog.fileno()) # Garante que os dados vão para o disco físico em POSIX
                        elif os.name == 'nt' and msvcrt:
                                # Em Windows, fdatasync é mais confiável que apenas flush() para garantia de disco.
                                # fdatasync no msvcrt faz o commit do buffer do SO para o disco.
                                msvcrt.fdatasync(self.arquivoLog.fileno())
