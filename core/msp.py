import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import ctypes
from pygame import mixer
from pathlib import Path
from threading import Thread
from urllib import request
from sound_lib import stream, output
from sound_lib.channel import Channel
from sound_lib.external import pybass
from core.log import gravaErro

class FluxoUrl(Channel):
    def __init__(self, url):
        requisicao = request.Request(url, headers={"User-Agent": "clientmud", "Icy-MetaData": "0"})
        self._resposta = request.urlopen(requisicao, timeout=10)
        self._proc_fecha = pybass.FILECLOSEPROC(self._fecha)
        self._proc_tamanho = pybass.FILELENPROC(self._tamanho)
        self._proc_le = pybass.FILEREADPROC(self._le)
        self._proc_busca = pybass.FILESEEKPROC(self._busca)
        self._procs = pybass.BASS_FILEPROCS(
            self._proc_fecha, self._proc_tamanho, self._proc_le, self._proc_busca
        )
        handle = pybass.BASS_StreamCreateFileUser(pybass.STREAMFILE_BUFFER, 0, self._procs, None)
        if not handle:
            codigo = pybass.BASS_ErrorGetCode()
            try:
                self._resposta.close()
            except Exception:
                pass
            raise RuntimeError(f"BASS_StreamCreateFileUser falhou (erro {codigo})")
        super().__init__(handle)

    def _fecha(self, user):
        try:
            self._resposta.close()
        except Exception:
            pass

    def _tamanho(self, user):
        return 0

    def _le(self, buffer, comprimento, user):
        try:
            dados = self._resposta.read(comprimento)
            if not dados:
                return 0xFFFFFFFF
            ctypes.memmove(buffer, dados, len(dados))
            return len(dados)
        except Exception:
            return 0xFFFFFFFF

    def _busca(self, offset, user):
        return False

    def stop(self):
        try:
            super().stop()
        except Exception:
            pass
        try:
            pybass.BASS_StreamFree(self.handle)
        except Exception:
            pass

class Msp:
    def __init__(self):
        self.pastaSons = False
        self.urlBase = None
        output.Output()
        self.soundLib = False
        self.volume_musica = 0
        self.volume_som = 0
        self.volume_base = 100
        self.sons = []
        self._cache_sons = {}
        try:
            mixer.pre_init(44100, -16, 2, 1024)
            mixer.init()
            mixer.set_num_channels(64)
        except Exception as e:
            gravaErro(e)

    def definePastaSons(self, sons=Path()):
        self.pastaSons = sons
        self.urlBase = None

    def defineUrlBase(self, url):
        url = (url or '').strip()
        if url.lower().startswith(('http://', 'https://', 'ftp://')):
            self.urlBase = url
        else:
            self.urlBase = None

    def music(self, musica, volume, loops=0, url=None):
        url = url or self.urlBase
        self.volume_base = volume
        path = Path(musica)
        if not path.suffix:
            musica += ".mp3"

        caminho_musica = self.pastaSons / musica

        volume_final = max(0, min(volume + self.volume_musica, 100))

        if caminho_musica.exists():
            self.musicOff()
            try:
                mixer.music.load(caminho_musica)
                mixer.music.set_volume(volume_final / 100)
                mixer.music.play(loops=loops)
                self.soundLib = False
            except Exception as e:
                try:
                    self.musica = stream.FileStream(file=str(caminho_musica))
                    self.musica.looping = bool(loops)
                    self.musica.volume = volume_final / 100
                    self.musica.play()
                    self.soundLib = True
                except Exception as e2:
                    gravaErro(e2)
        elif url:
            Thread(target=self._tocaMusicaUrl, args=(url, musica, volume_final, loops), daemon=True).start()

    def _tocaMusicaUrl(self, url, musica, volume_final, loops):
        if url.lower().endswith(Path(musica).name.lower()):
            candidatos = [url]
        else:
            candidatos = [f"{url.rstrip('/')}/{musica}", url]
        erro = None
        for candidato in candidatos:
            for abre in (FluxoUrl, lambda u: stream.URLStream(url=u)):
                try:
                    fluxo = abre(candidato)
                    self.musicOff()
                    try:
                        fluxo.looping = bool(loops)
                    except Exception:
                        pass
                    fluxo.volume = volume_final / 100
                    fluxo.play()
                    self.musica = fluxo
                    self.soundLib = True
                    return
                except Exception as e:
                    erro = e
        if erro:
            gravaErro(erro)

    def sound(self, som, volume, url=None, de_trigger=False):
        if not de_trigger:
            url = url or self.urlBase
        path = Path(som)
        if not path.suffix:
            som += ".wav"

        caminho_som = self.pastaSons / som

        volume_final = max(0, min(volume + self.volume_som, 100))

        if caminho_som.exists():
            self._tocaSomLocal(caminho_som, volume_final, de_trigger)
        elif url:
            Thread(target=self._baixaEtocaSom, args=(url, som, caminho_som, volume_final, de_trigger), daemon=True).start()

    def _tocaSomLocal(self, caminho_som, volume_final, de_trigger=False):
        try:
            chave = str(caminho_som)
            if chave not in self._cache_sons:
                self._cache_sons[chave] = mixer.Sound(caminho_som)
            som_obj = self._cache_sons[chave]
            som_obj.set_volume(volume_final / 100)
            canal = som_obj.play()
            if canal is not None:
                self.sons.append({'canal': canal, 'som': som_obj, 'de_trigger': de_trigger})
            self._limpaSonsParados()
        except Exception as e:
            try:
                som_obj = stream.FileStream(file=str(caminho_som))
                som_obj.volume = volume_final / 100
                som_obj.play()
                self.sons.append({'canal': som_obj, 'som': None, 'de_trigger': de_trigger})
                self._limpaSonsParados()
            except Exception as e2:
                gravaErro(e2)

    def _limpaSonsParados(self):
        ativos = []
        for item in self.sons:
            canal, som_obj = item['canal'], item['som']
            try:
                if som_obj is not None:
                    if canal.get_busy() and canal.get_sound() is som_obj:
                        ativos.append(item)
                elif getattr(canal, 'is_playing', True):
                    ativos.append(item)
            except Exception:
                pass
        if len(ativos) > 64:
            ativos = ativos[-64:]
        self.sons = ativos

    def _baixaEtocaSom(self, url, som, caminho_som, volume_final, de_trigger=False):
        try:
            caminho_som.resolve().relative_to(Path(self.pastaSons).resolve())
        except (ValueError, OSError):
            caminho_som = self.pastaSons / Path(som).name

        candidatos = []
        if url.lower().endswith(Path(som).name.lower()):
            candidatos.append(url)
        else:
            candidatos.append(f"{url.rstrip('/')}/{som}")
            candidatos.append(url)

        erro = None
        for candidato in candidatos:
            try:
                requisicao = request.Request(candidato, headers={"User-Agent": "clientmud"})
                with request.urlopen(requisicao, timeout=10) as resposta:
                    dados = resposta.read(20 * 1024 * 1024)
                caminho_som.parent.mkdir(parents=True, exist_ok=True)
                caminho_som.write_bytes(dados)
                self._tocaSomLocal(caminho_som, volume_final, de_trigger)
                return
            except Exception as e:
                erro = e
        if erro:
            gravaErro(erro)

    def soundOff(self, somente_mud=False):
        restantes = []
        for item in list(self.sons):
            if somente_mud and item['de_trigger']:
                restantes.append(item)
                continue
            canal, som_obj = item['canal'], item['som']
            try:
                if som_obj is not None:
                    if canal.get_sound() is som_obj:
                        canal.stop()
                else:
                    canal.stop()
            except Exception:
                pass
        self.sons = restantes
        if not somente_mud:
            try:
                mixer.stop()
            except Exception:
                pass

    def musicOff(self):
        try:
            mixer.music.unload()
        except Exception:
            pass
        if self.soundLib and hasattr(self, 'musica'):
            try:
                self.musica.stop()
            except Exception:
                pass
            self.soundLib = False

    def alteraVolume(self, tipo, valor):
        if tipo == 'musica':
            volume_atual = max(0, min(self.volume_base + self.volume_musica, 100))
            volume_atualizar = max(0, min(volume_atual + valor, 100))
            if volume_atualizar == volume_atual:
                return False
            self.volume_musica = volume_atualizar - self.volume_base


            if self.soundLib and hasattr(self, 'musica'):
                try:
                    self.musica.volume = volume_atualizar / 100
                except Exception:
                    pass
            else:
                try:
                    mixer.music.set_volume(volume_atualizar / 100)
                except Exception:
                    pass
            return True
        else:
            self.volume_som += valor
            if self.volume_som > 100:
                self.volume_som = 100
                return False
            elif self.volume_som < -100:
                self.volume_som = -100
                return False
            return True