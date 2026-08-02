import subprocess

import wx

from gui.aba import PainelSessaoMud

class AbasMixin:
    """Gestão do notebook: troca, fechamento e criação de abas de conexão, e
    o despacho de ações da barra de menus para a aba ativa."""

    def aoTrocarAba(self, evento):
        self._anunciaAbaAtiva()
        evento.Skip()

    def _anunciaAbaAtiva(self):
        aba = self.get_aba_ativa()
        if aba:
            indice = self.notebook.GetSelection()
            if indice != wx.NOT_FOUND:
                titulo = self.notebook.GetPageText(indice)
                self.SetTitle(titulo)
                # Força o NVDA a ler o título da aba em voz alta
                wx.CallAfter(self.app.fale, titulo)
            wx.CallAfter(aba.entrada.SetFocus)
            # As configurações do personagem só existem em conexões por
            # personagem; em conexões rápidas/manuais não há personagem.
            self.item_config_personagem.Enable(bool(aba.json_personagem))
            aba.sincronizaLabelDesativarTudo()

    def fechaAba(self, aba):
        if not aba: return
        aba.aoFecharAba()
        if not aba.janelaFechada:
            return
        if aba in self.abas_abertas:
            self.abas_abertas.remove(aba)
        indice = self.notebook.FindPage(aba)
        if indice != wx.NOT_FOUND:
            self.notebook.DeletePage(indice)
        if self.notebook.GetPageCount() > 0:
            # Aba secundária: traz a aba anterior para frente
            self.notebook.ChangeSelection(max(indice - 1, 0))
            self._anunciaAbaAtiva()
            return
        # Era a última aba: encerra a janela e volta para a janela de conexões
        self.app.janela_principal = None
        wx.CallAfter(self.app.mostraDialogoEntrada)
        self.Destroy()

    def atualizaTituloAba(self, aba, nome_personagem):
        indice = self.notebook.FindPage(aba)
        if indice == wx.NOT_FOUND:
            return
        nome_mud = aba.nome_mud or ''
        titulo_aba = f"{nome_personagem} {nome_mud}, ClientMUD"
        self.notebook.SetPageText(indice, titulo_aba)
        if self.notebook.GetSelection() == indice:
            self.SetTitle(titulo_aba)

    def nova_aba_conexao(self, dados):
        aba = PainelSessaoMud(self.notebook, self, dados.get('endereco', 'MUD'), dados.get('json_personagem'))

        json_pers = dados.get('json_personagem') or {}
        nome_personagem = json_pers.get('nome', 'Sem Nome')

        nome_mud = json_pers.get('mud', '')
        if not nome_mud:
            endereco = dados.get('endereco', 'MUD')
            nome_mud = endereco.split('.')[0]

        titulo_aba = f"{nome_personagem} {nome_mud}, ClientMUD"

        self.notebook.AddPage(aba, titulo_aba, select=True)
        self.abas_abertas.append(aba)
        self.SetTitle(titulo_aba)
        aba.sincronizaLabelDesativarTudo()

        if 'endereco' in dados and 'porta' in dados:
            aba._iniciarConexaoThread(dados['endereco'], dados['porta'], dados.get('ssl', False))

        aba.entrada.SetFocus()

    def get_aba_ativa(self):
        indice = self.notebook.GetSelection()
        if indice != wx.NOT_FOUND:
            return self.notebook.GetPage(indice)
        return None

    def executar_na_aba(self, nome_metodo):
        aba = self.get_aba_ativa()
        if aba and hasattr(aba, nome_metodo):
            getattr(aba, nome_metodo)()
        elif aba and '.' in nome_metodo:
            obj, method = nome_metodo.split('.')
            if hasattr(aba, obj):
                sub_obj = getattr(aba, obj)
                if hasattr(sub_obj, method):
                    getattr(sub_obj, method)()

    def executar_na_aba_com_args(self, nome_metodo, *args):
        aba = self.get_aba_ativa()
        if aba and hasattr(aba, nome_metodo):
            getattr(aba, nome_metodo)(*args)

    def executar_na_aba_com_pasta(self, tipo_pasta):
        aba = self.get_aba_ativa()
        if aba:
            caminho = None
            if tipo_pasta == 'logs': caminho = aba.pasta_logs
            elif tipo_pasta == 'scripts': caminho = aba.pasta_scripts
            elif tipo_pasta == 'sons': caminho = aba.pasta_sons
            if caminho:
                subprocess.Popen(["explorer", str(caminho)])
