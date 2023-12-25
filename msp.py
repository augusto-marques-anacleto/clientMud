import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

from pygame import mixer
mixer.init()
mixer.set_num_channels(120)
from pathlib import Path

class Msp():

	def __init__(self):
		mixer.init()
		self.pastaSons = False
	def definePastaSons(self, sons=Path()):
		self.pastaSons = sons


	def music(self, musica, v, l=0):
		path=Path(musica)
		if not path.suffix:
			musica+=".mp3"
			del(path)
		musica=self.pastaSons / musica
		if musica.exists():
			mixer.music.load(musica)
			mixer.music.set_volume(v/100)
			mixer.music.play(loops=l)
	def sound(self, som, v):
		path=Path(som)
		if not path.suffix:
			som+=".wav"
			del(path)
		som = self.pastaSons / som
		if som.exists():
			try:
				som=mixer.Sound(som)
				som.set_volume(v/100)
				som.play()
			except:
				return ""

	def musicOff(self):
		mixer.music.unload()