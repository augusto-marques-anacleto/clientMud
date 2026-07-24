import wx
import subprocess

class MenuMixin:
    """Construção da barra de menus e ligação dos itens aos handlers."""

    def menuBar(self):
        geralMenu = wx.Menu()
        interrompeMusica = geralMenu.Append(wx.ID_ANY, "&Interromper música em reprodução\tCtrl-M")
        self.Bind(wx.EVT_MENU, lambda e: self.app.msp.musicOff(), interrompeMusica)
        geralMenu.AppendSeparator()
        encerraPrograma = geralMenu.Append(wx.ID_EXIT, "&Sair.")
        self.Bind(wx.EVT_MENU, self.fechaApp, encerraPrograma)

        menuPastas = wx.Menu()
        geral = menuPastas.Append(wx.ID_ANY, "Abrir Pasta Geral\tCtrl-G")
        self.Bind(wx.EVT_MENU, lambda e: subprocess.Popen(["explorer", str(self.pasta_geral)]), geral)
        logs = menuPastas.Append(wx.ID_ANY, "abrir pasta de logs\tCtrl-L")
        self.Bind(wx.EVT_MENU, lambda e: subprocess.Popen(["explorer", str(self.pasta_logs)]), logs)
        scripts = menuPastas.Append(wx.ID_ANY, "Abrir Pasta de Scripts\tCtrl-R")
        self.Bind(wx.EVT_MENU, lambda e: subprocess.Popen(["explorer", str(self.pasta_scripts)]), scripts)
        sons = menuPastas.Append(wx.ID_ANY, "Abrir Pasta de Sons\tCtrl-S")
        self.Bind(wx.EVT_MENU, lambda e: subprocess.Popen(["explorer", str(self.pasta_sons)]), sons)

        menuFerramentas = wx.Menu()
        self.item_desativar_tudo = menuFerramentas.Append(wx.ID_ANY, "Desativar Tudo\tCtrl+Shift+D")
        self.Bind(wx.EVT_MENU, self.desativar_tudo, self.item_desativar_tudo)
        menuFerramentas.AppendSeparator()
        menuBackup = wx.Menu()
        exportarBackup = menuBackup.Append(wx.ID_ANY, "Exportar configurações e personagens\tCtrl-Shift-E")
        self.Bind(wx.EVT_MENU, self.ao_exportar_backup, exportarBackup)

        importarBackup = menuBackup.Append(wx.ID_ANY, "Importar configurações e personagens\tCtrl-Shift-I")
        self.Bind(wx.EVT_MENU, self.ao_importar_backup, importarBackup)

        menuFerramentas.AppendSubMenu(menuBackup, "&Backup")
        menuSons = wx.Menu()
        baixarSons = menuSons.Append(wx.ID_ANY, "Baixar pacote de sons via Link\tCtrl-B")
        self.Bind(wx.EVT_MENU, self.iniciarDownloadSons, baixarSons)

        importarSonsLocal = menuSons.Append(wx.ID_ANY, "Importar pacote de sons local (ZIP)\tCtrl-p")
        self.Bind(wx.EVT_MENU, self.iniciarImportacaoLocal, importarSonsLocal)

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
        self.Bind(wx.EVT_MENU, lambda e: self.alteraVolume('musica', 10), id=id_musica_mais)
        self.Bind(wx.EVT_MENU, lambda e: self.alteraVolume('musica', -10), id=id_musica_menos)
        self.Bind(wx.EVT_MENU, lambda e: self.alteraVolume('som', 10), id=id_som_mais)
        self.Bind(wx.EVT_MENU, lambda e: self.alteraVolume('som', -10), id=id_som_menos)
        menuFerramentas.AppendSubMenu(menuAudio, "&Audio")

        menuMacros = wx.Menu()
        self.id_iniciar_gravacao = wx.NewIdRef()
        self.item_iniciar_gravacao = menuMacros.Append(self.id_iniciar_gravacao, "Iniciar Gravação\tCtrl+Shift+G")
        self.Bind(wx.EVT_MENU, self.inicia_gravacao, id=self.id_iniciar_gravacao)

        self.id_pausar_gravacao = wx.NewIdRef()
        self.item_pausar_gravacao = menuMacros.Append(self.id_pausar_gravacao, "Pausar Gravação\tCtrl+Shift+P")
        self.item_pausar_gravacao.Enable(False)
        self.Bind(wx.EVT_MENU, self.pausa_retoma_gravacao, id=self.id_pausar_gravacao)

        self.id_ignorar_ultimo = wx.NewIdRef()
        self.item_ignorar_ultimo = menuMacros.Append(self.id_ignorar_ultimo, "Ignorar Último Comando\tCtrl+Shift+J")
        self.item_ignorar_ultimo.Enable(False)
        self.Bind(wx.EVT_MENU, self.ignora_ultimo_comando, id=self.id_ignorar_ultimo)

        self.id_interromper_gravacao = wx.NewIdRef()
        self.item_interromper_gravacao = menuMacros.Append(self.id_interromper_gravacao, "Interromper Gravação\tCtrl+Shift+F")
        self.item_interromper_gravacao.Enable(False)
        self.Bind(wx.EVT_MENU, self.interrompe_gravacao, id=self.id_interromper_gravacao)

        menuMacros.AppendSeparator()

        gerenciarMacros = menuMacros.Append(wx.ID_ANY, "Gerenciar &Macros / Rotas...\tCtrl-U")
        self.Bind(wx.EVT_MENU, self.abrirGerenciadorMacros, gerenciarMacros)

        menuFerramentas.AppendSubMenu(menuMacros, "M&acros e Rotas")

        menuGerenciarKeys = menuFerramentas.Append(wx.ID_ANY, 'Gerenciar atalhos...\tCtrl-K')
        self.Bind(wx.EVT_MENU, self.abrirGerenciadorKeys, menuGerenciarKeys)
        menuGerenciarTriggers = menuFerramentas.Append(wx.ID_ANY, "Gerenciar &Triggers...\tCtrl-T")
        self.Bind(wx.EVT_MENU, self.abrirGerenciadorTriggers, menuGerenciarTriggers)
        menuGerenciarTimers = menuFerramentas.Append(wx.ID_ANY, "Gerenciar &Timers...\tCtrl-I")
        self.Bind(wx.EVT_MENU, self.abrirGerenciadorTimers, menuGerenciarTimers)

        menuScriptsExternos = menuFerramentas.Append(wx.ID_ANY, "Scripts &Externos...\tCtrl+Shift+X")
        self.Bind(wx.EVT_MENU, self.abrirScriptsExternos, menuScriptsExternos)

        self.menuHistoricos = wx.Menu()
        menuFerramentas.AppendSubMenu(self.menuHistoricos, "&Históricos\tCtrl-H")

        ditado = menuFerramentas.Append(wx.ID_ANY, "Escrever por voz\tCtrl-O")
        self.Bind(wx.EVT_MENU, self.falaPorVoz, ditado)

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
