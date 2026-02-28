import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
from pygame import mixer
from pathlib import Path
from sound_lib import stream, output
from core.log import gravaErro

class Msp:
    def __init__(self):
        self.pastaSons = False
        output.Output()
        self.soundLib = False
        self.volume_musica = 0
        self.volume_som = 0
        self.volume_base = 100
        try:
            mixer.pre_init(44100, -16, 2, 1024)
            mixer.init()
            mixer.set_num_channels(64)
        except Exception as e:
            gravaErro(e)

    def definePastaSons(self, sons=Path()):
        self.pastaSons = sons

    def music(self, musica, volume, loops=0):
        self.volume_base = volume
        path = Path(musica)
        if not path.suffix:
            musica += ".mp3"
            
        caminho_musica = self.pastaSons / musica
        
        volume_final = max(0, min(volume + self.volume_musica, 100))

        if caminho_musica.exists():
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

    def sound(self, som, volume):
        path = Path(som)
        if not path.suffix:
            som += ".wav"
            
        caminho_som = self.pastaSons / som
        
        volume_final = max(0, min(volume + self.volume_som, 100))

        if caminho_som.exists():
            try:
                som_obj = mixer.Sound(caminho_som)
                som_obj.set_volume(volume_final / 100)
                som_obj.play()
            except Exception as e:
                gravaErro(e)

    def musicOff(self):
        try:
            mixer.music.unload()
        except:
            pass
        if self.soundLib and hasattr(self, 'musica'):
            self.musica.stop()

    def alteraVolume(self, tipo, valor):
        if tipo == 'musica':
            self.volume_musica += valor
            if self.volume_musica > 100:
                self.volume_musica = 100
                return False
            elif self.volume_musica < -100:
                self.volume_musica = -100
                return False
            
            volume_atualizar = max(0, min(self.volume_base + self.volume_musica, 100))
            
            if self.soundLib and hasattr(self, 'musica'):
                try:
                    self.musica.volume = volume_atualizar / 100
                except:
                    pass
            else:
                try:
                    mixer.music.set_volume(volume_atualizar / 100)
                except:
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