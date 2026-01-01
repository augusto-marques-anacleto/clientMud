import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
from pygame import mixer
from pathlib import Path
from sound_lib import stream, output
from log import gravaErro

class Msp:
    def __init__(self):
        self.pastaSons = False
        output.Output()
        self.soundLib = False
        self.volume_musica = 0
        self.volume_som = 0
        self.volume_base= 100
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
            del(path)
        musica = self.pastaSons / musica
        
        volume_final = volume + self.volume_musica
        if volume_final < 0: volume_final = 0
        if volume_final > 100: volume_final = 100

        if musica.exists():
            try:
                mixer.music.load(musica)
                mixer.music.set_volume(volume_final/100)
                mixer.music.play(loops=loops)
                self.soundLib = False
            except Exception as e:
                self.musica = stream.FileStream(file=str(musica))
                self.musica.looping = loops
                self.musica.volume = volume_final/100
                self.musica.play()
                self.soundLib = True
                gravaErro(e)

    def sound(self, som, volume):
        path = Path(som)
        if not path.suffix:
            som += ".wav"
            del(path)
        som = self.pastaSons / som
        
        volume_final = volume + self.volume_som
        if volume_final < 0: volume_final = 0
        if volume_final > 100: volume_final = 100

        if som.exists():
            try:
                som = mixer.Sound(som)
                som.set_volume(volume_final/100)
                som.play()
            except Exception as e:
                gravaErro(e)

    def musicOff(self):
        try:
            mixer.music.unload()
        except:
            pass
        if self.soundLib:
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
            
            volume_atualizar = self.volume_base+ self.volume_musica
            if volume_atualizar < 0: volume_atualizar = 0
            if volume_atualizar > 100: volume_atualizar = 100
            
            if self.soundLib:
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