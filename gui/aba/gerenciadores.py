import re
import threading

import wx

from core.external_scripts import GerenciadorScriptsExternos
from gui.dialogs.keys import DialogoGerenciaKeys
from gui.dialogs.timers import DialogoGerenciaTimers, GerenciadorTimers
from gui.dialogs.triggers import DialogoGerenciaTriggers

class GerenciadoresMixin:
    """Abertura dos gerenciadores (triggers, timers, keys, macros, scripts) e
    ciclo de vida de timers e scripts externos desta aba."""

    def desativar_tudo(self):
        todas = self.triggers + self.timers + self.keys + self.macros
        if not todas: return
        algum_ativo = any(getattr(item, 'ativo', False) for item in todas)
        for item in todas:
            item.ativo = not algum_ativo
        if algum_ativo:
            self.app.fale("Tudo desativado.")
        else:
            self.app.fale("Tudo ativado.")
        self.sincronizaLabelDesativarTudo()
        if self.gerenciador_timers:
            self.gerenciador_timers.atualizar_timers([t.to_dict() for t in self.timers])
        self.salvaConfiguracoesPersonagem()

    def sincronizaLabelDesativarTudo(self):
        # Item de menu é único e compartilhado entre todas as abas.
        todas = self.triggers + self.timers + self.keys + self.macros
        algum_ativo = any(getattr(item, 'ativo', False) for item in todas)
        rotulo = "Desativar Tudo\tCtrl+Shift+D" if algum_ativo else "Ativar Tudo\tCtrl+Shift+D"
        self.frame_principal.item_desativar_tudo.SetItemLabel(rotulo)

    def abrirGerenciadorMacros(self):
        from gui.dialogs.macros import DialogoGerenciaMacros
        dlg = DialogoGerenciaMacros(self, self.macros)
        if dlg.ShowModal() == wx.ID_OK:
            if dlg.alteracoes_feitas:
                self.salvaConfiguracoesPersonagem()
        dlg.Destroy()

    def abrirGerenciadorTriggers(self):
        dlg = DialogoGerenciaTriggers(self, self.triggers)
        if dlg.ShowModal() == wx.ID_OK:
            if dlg.alteracoes_feitas:
                self.salvaConfiguracoesPersonagem()
        dlg.Destroy()

    def falaPorVoz(self):
        threading.Thread(target=self.ouvir_microfone_thread, daemon=True).start()

    def ouvir_microfone_thread(self):
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            try:
                r.adjust_for_ambient_noise(source, duration=0.1)
                self.app.fale("Comece a falar.")
                r.pause_threshold = 1.0
                r.non_speaking_duration = 1.0
                r.energy_threshold = 100
                r.dynamic_energy_threshold = True
                audio = r.listen(source, phrase_time_limit=None)
                texto = r.recognize_google(audio, language="pt-BR")

                substituicoes = [
                    (r'\s*ponto de interroga[çc][ãa]o', '?'),
                    (r'\s*ponto de exclama[çc][ãa]o', '!'),
                    (r'\s*ponto final', '.'),
                    (r'\s*ponto e v[íi]rgula', ';'),
                    (r'\s*dois pontos', ':'),
                    (r'\s*v[íi]rgula', ','),
                    (r'\s*retic[êe]ncias', '...')
                ]

                for padrao, simbolo in substituicoes:
                    texto = re.sub(padrao, simbolo, texto, flags=re.IGNORECASE)

                self.adicionaComandoLista(texto)
                self.processa_e_envia_comando(texto)
            except sr.UnknownValueError:
                self.app.fale("Não entendi o que foi dito.")
            except Exception as e:
                self.app.fale(f"Erro inesperado: {e}")

    def abrirGerenciadorTimers(self):
        dlg = DialogoGerenciaTimers(self, self.timers, self.gerenciador_timers)
        if dlg.ShowModal() == wx.ID_OK:
            if dlg.alteracoes_feitas:
                self.salvaConfiguracoesPersonagem()
        dlg.Destroy()

    def abrirGerenciadorKeys(self):
        dlg = DialogoGerenciaKeys(self, self.keys)
        if dlg.ShowModal() == wx.ID_OK:
            if dlg.alteracoes_feitas:
                self.salvaConfiguracoesPersonagem()
        dlg.Destroy()

    def inicia_gerenciador_timers(self):
        if self.gerenciador_timers and not self.gerenciador_timers.is_alive():
            self.gerenciador_timers = None
        if not self.gerenciador_timers and self.client.ativo:
            configs_para_thread = [t.to_dict() for t in self.timers]
            self.gerenciador_timers = GerenciadorTimers(configs_para_thread, self.client)
            self.gerenciador_timers.start()

    def para_gerenciador_timers(self):
        if self.gerenciador_timers:
            self.gerenciador_timers.parar()
            self.gerenciador_timers.join(timeout=1.0)
            self.gerenciador_timers = None

    def inicia_scripts_externos(self):
        self.gerenciador_scripts_ext.parar_todos()
        habilitados = GerenciadorScriptsExternos.carregar_habilitados(str(self.pasta_scripts))
        if habilitados:
            self.gerenciador_scripts_ext.iniciar(
                habilitados, str(self.pasta_scripts), self, self.app.async_loop
            )

    def abrirScriptsExternos(self):
        from gui.dialogs.external_scripts import DialogoScriptsExternos
        dlg = DialogoScriptsExternos(self, str(self.pasta_scripts))
        if dlg.ShowModal() == wx.ID_OK and self.client.ativo:
            self.inicia_scripts_externos()
        dlg.Destroy()
