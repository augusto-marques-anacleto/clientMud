import subprocess
from pathlib import Path

import wx

from gui.dialogs.settings import DialogoConfiguracoesGerais
from gui.dialogs.connection import DialogoEditaPersonagem

class MenuMixin:
    """Construção da barra de menus (compartilhada por todas as abas) e
    ligação dos itens aos handlers."""

    def menuBar(self):
        geralMenu = wx.Menu()
        novaConexao = geralMenu.Append(wx.ID_ANY, "Nova Conexão...\tCtrl-N")
        self.Bind(wx.EVT_MENU, lambda e: self.app.mostraDialogoEntrada(), novaConexao)

        fecharAba = geralMenu.Append(wx.ID_ANY, "Fechar Aba\tCtrl-W")
        self.Bind(wx.EVT_MENU, lambda e: self.fechaAba(self.get_aba_ativa()), fecharAba)
        geralMenu.AppendSeparator()

        interrompeMusica = geralMenu.Append(wx.ID_ANY, "&Interromper música em reprodução\tCtrl-M")
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba('msp.musicOff'), interrompeMusica)
        geralMenu.AppendSeparator()

        configuracoesGerais = geralMenu.Append(wx.ID_ANY, "Configurações &gerais...\tCtrl+Shift+C")
        self.Bind(wx.EVT_MENU, self.abrirConfiguracoesGerais, configuracoesGerais)

        self.item_config_personagem = geralMenu.Append(wx.ID_ANY, "Configurações do &personagem...\tCtrl+Shift+N")
        self.Bind(wx.EVT_MENU, self.abrirConfiguracoesPersonagem, self.item_config_personagem)
        geralMenu.AppendSeparator()

        encerraPrograma = geralMenu.Append(wx.ID_EXIT, "&Sair.")
        self.Bind(wx.EVT_MENU, self.fechaApp, encerraPrograma)

        menuPastas = wx.Menu()
        geral = menuPastas.Append(wx.ID_ANY, "Abrir Pasta Geral\tCtrl-G")
        self.Bind(wx.EVT_MENU, lambda e: subprocess.Popen(["explorer", str(Path(self.app.config.config['gerais']['diretorio-de-dados']) / "clientmud")]), geral)

        logs = menuPastas.Append(wx.ID_ANY, "abrir pasta de logs\tCtrl-L")
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba_com_pasta('logs'), logs)

        scripts = menuPastas.Append(wx.ID_ANY, "Abrir Pasta de Scripts\tCtrl-R")
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba_com_pasta('scripts'), scripts)

        sons = menuPastas.Append(wx.ID_ANY, "Abrir Pasta de Sons\tCtrl-S")
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba_com_pasta('sons'), sons)

        menuFerramentas = wx.Menu()
        self.item_desativar_tudo = menuFerramentas.Append(wx.ID_ANY, "Desativar Tudo\tCtrl+Shift+D")
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba('desativar_tudo'), self.item_desativar_tudo)
        menuFerramentas.AppendSeparator()

        menuBackup = wx.Menu()
        exportarBackup = menuBackup.Append(wx.ID_ANY, "Exportar configurações e personagens\tCtrl-Shift-E")
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba('ao_exportar_backup'), exportarBackup)

        importarBackup = menuBackup.Append(wx.ID_ANY, "Importar configurações e personagens\tCtrl-Shift-I")
        self.Bind(wx.EVT_MENU, self.ao_importar_backup, importarBackup)

        menuFerramentas.AppendSubMenu(menuBackup, "&Backup")

        menuSons = wx.Menu()
        baixarSons = menuSons.Append(wx.ID_ANY, "Baixar pacote de sons via Link\tCtrl-B")
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba('iniciarDownloadSons'), baixarSons)

        importarSonsLocal = menuSons.Append(wx.ID_ANY, "Importar pacote de sons local (ZIP)\tCtrl-p")
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba('iniciarImportacaoLocal'), importarSonsLocal)

        menuFerramentas.AppendSubMenu(menuSons, "Gerenciar &Sons do Personagem")

        menuAudio = wx.Menu()
        id_musica_mais = wx.NewIdRef()
        id_musica_menos = wx.NewIdRef()
        id_som_mais = wx.NewIdRef()
        id_som_menos = wx.NewIdRef()
        menuAudio.Append(id_musica_mais, "Aumentar volume Música\tCtrl+PgUp")
        menuAudio.Append(id_musica_menos, "Diminuir Volume Música\tCtrl+PgDn")
        menuAudio.Append(id_som_mais, "Aumentar Volume Sons\tCtrl+Shift+PgUp")
        menuAudio.Append(id_som_menos, "Diminuir Volume Sons\tCtrl+Shift+PgDn")
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba_com_args('alteraVolume', 'musica', 10), id=id_musica_mais)
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba_com_args('alteraVolume', 'musica', -10), id=id_musica_menos)
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba_com_args('alteraVolume', 'som', 10), id=id_som_mais)
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba_com_args('alteraVolume', 'som', -10), id=id_som_menos)
        menuFerramentas.AppendSubMenu(menuAudio, "&Audio")

        menuMacros = wx.Menu()
        self.id_iniciar_gravacao = wx.NewIdRef()
        self.item_iniciar_gravacao = menuMacros.Append(self.id_iniciar_gravacao, "Iniciar Gravação\tCtrl+Shift+G")
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba('inicia_gravacao'), id=self.id_iniciar_gravacao)

        self.id_pausar_gravacao = wx.NewIdRef()
        self.item_pausar_gravacao = menuMacros.Append(self.id_pausar_gravacao, "Pausar Gravação\tCtrl+Shift+P")
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba('pausa_retoma_gravacao'), id=self.id_pausar_gravacao)

        self.id_ignorar_ultimo = wx.NewIdRef()
        self.item_ignorar_ultimo = menuMacros.Append(self.id_ignorar_ultimo, "Ignorar Último Comando\tCtrl+Shift+J")
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba('ignora_ultimo_comando'), id=self.id_ignorar_ultimo)

        self.id_interromper_gravacao = wx.NewIdRef()
        self.item_interromper_gravacao = menuMacros.Append(self.id_interromper_gravacao, "Interromper Gravação\tCtrl+Shift+F")
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba('interrompe_gravacao'), id=self.id_interromper_gravacao)

        menuMacros.AppendSeparator()
        gerenciarMacros = menuMacros.Append(wx.ID_ANY, "Gerenciar &Macros / Rotas...\tCtrl-U")
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba('abrirGerenciadorMacros'), gerenciarMacros)
        menuFerramentas.AppendSubMenu(menuMacros, "M&acros e Rotas")

        menuGerenciarKeys = menuFerramentas.Append(wx.ID_ANY, 'Gerenciar atalhos...\tCtrl-K')
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba('abrirGerenciadorKeys'), menuGerenciarKeys)

        menuGerenciarTriggers = menuFerramentas.Append(wx.ID_ANY, "Gerenciar &Triggers...\tCtrl-T")
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba('abrirGerenciadorTriggers'), menuGerenciarTriggers)

        menuGerenciarTimers = menuFerramentas.Append(wx.ID_ANY, "Gerenciar &Timers...\tCtrl-I")
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba('abrirGerenciadorTimers'), menuGerenciarTimers)

        menuScriptsExternos = menuFerramentas.Append(wx.ID_ANY, "Scripts &Externos...\tCtrl+Shift+X")
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba('abrirScriptsExternos'), menuScriptsExternos)

        ditado = menuFerramentas.Append(wx.ID_ANY, "Escrever por voz\tCtrl-O")
        self.Bind(wx.EVT_MENU, lambda e: self.executar_na_aba('falaPorVoz'), ditado)

        menuAjuda = wx.Menu()
        ajuda = menuAjuda.Append(wx.ID_ANY, "&Ajuda\tF1")
        self.Bind(wx.EVT_MENU, self.abrirAjuda, ajuda)
        menuAjuda.AppendSeparator()
        checarAtualizacoes = menuAjuda.Append(wx.ID_ANY, "Checar &Atualizações")
        self.Bind(wx.EVT_MENU, self.checarAtualizacoes, checarAtualizacoes)
        menuAjuda.AppendSeparator()
        sobre = menuAjuda.Append(wx.ID_ABOUT, "&Sobre o ClientMUD")
        self.Bind(wx.EVT_MENU, self.abrirSobre, sobre)

        menuBar = wx.MenuBar()
        menuBar.Append(geralMenu, "&Geral")
        menuBar.Append(menuPastas, "&Pastas")
        menuBar.Append(menuFerramentas, "&Ferramentas")
        menuBar.Append(menuAjuda, "&Ajuda")
        self.SetMenuBar(menuBar)

    def abrirConfiguracoesGerais(self, evento):
        dialogo = DialogoConfiguracoesGerais(self)
        dialogo.ShowModal()
        dialogo.Destroy()

    def abrirConfiguracoesPersonagem(self, evento):
        aba = self.get_aba_ativa()
        if not aba or not aba.json_personagem:
            return
        chave = aba._chave_personagem or aba.json_personagem.get('_chave') or aba.json_personagem.get('nome')
        dialogo = DialogoEditaPersonagem(self, chave, ao_renomear=aba.renomeiaPersonagemConectado)
        if dialogo.ShowModal() == wx.ID_OK:
            aba.aplicaEdicaoPersonagem(dialogo.chave_nova, dialogo.novo_dic)
        dialogo.Destroy()

    def aplicaConfiguracoesGeraisEmTodasAbas(self):
        for aba in self.abas_abertas:
            if not aba.janelaFechada:
                aba.aplicaConfiguracoesSessao()
