import wx
import sys
from pathlib import Path
from gui.theme import aplica_tema_se_ativo

class DialogoConfiguracoes(wx.Dialog):
    def __init__(self):
        super().__init__(parent=None, title="Configurações")
        self.app = wx.GetApp()
        painel = wx.Panel(self)
        
        self.pastaInicial = str(Path.cwd())
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        texto_pasta = wx.StaticText(painel, label='Pasta de dados.')
        sizer.Add(texto_pasta, 0, wx.ALL, 5)
        
        self.campoTextoPasta = wx.TextCtrl(painel, value=self.pastaInicial)
        sizer.Add(self.campoTextoPasta, 0, wx.EXPAND | wx.ALL, 5)
        
        btnEscolhePasta = wx.Button(painel, label='&Escolher pasta de dados')
        btnEscolhePasta.Bind(wx.EVT_BUTTON, self.escolhePasta)
        sizer.Add(btnEscolhePasta, 0, wx.ALL, 5)
        
        self.reproducaoForaDaJanela = wx.CheckBox(painel, label='Reproduzir sons fora da janela do MUD')
        sizer.Add(self.reproducaoForaDaJanela, 0, wx.ALL, 5)
        
        self.falaForaDaJanela = wx.CheckBox(painel, label='Ler as mensagens fora da janela do MUD')
        sizer.Add(self.falaForaDaJanela, 0, wx.ALL, 5)
        
        self.verificaAtualizacao = wx.CheckBox(painel, label='Verificar atualizações automaticamente ao iniciar')
        self.verificaAtualizacao.SetValue(True)
        sizer.Add(self.verificaAtualizacao, 0, wx.ALL, 5)
        
        btnFinaliza = wx.Button(painel, label='&Finalizar configuração.')
        btnFinaliza.Bind(wx.EVT_BUTTON, self.finalizaConfiguracao)
        sizer.Add(btnFinaliza, 0, wx.ALL, 5)

        painel.SetSizer(sizer)
        sizer.Fit(self)
        self.Center()

        aplica_tema_se_ativo(self)

    def escolhePasta(self, evento):
        dialogo = wx.DirDialog(self, 'Escolha de pasta')
        if dialogo.ShowModal() == wx.ID_OK:
            self.pastaInicial = dialogo.GetPath()
            self.campoTextoPasta.SetValue(self.pastaInicial)
        dialogo.Destroy()

    def finalizaConfiguracao(self, evento):
        pasta = self.campoTextoPasta.GetValue()
        if pasta:
            pastaPath = Path(pasta).resolve()
            if pastaPath.exists():
                self.pastaInicial = str(pastaPath)
                
                dic = {
                    'gerais': {
                        "toca-sons-fora-da-janela": self.reproducaoForaDaJanela.GetValue(),
                        'ignorar-urls-msp': False,
                        'ler fora da janela': self.falaForaDaJanela.GetValue(),
                        'verifica-atualizacoes-automaticamente': self.verificaAtualizacao.GetValue(),
                        "ultima-conexao": [],
                        "diretorio-de-dados": self.pastaInicial,
                        "logs": str(Path(pastaPath, "clientmud", "logs")),
                        "scripts": str(Path(pastaPath, "clientmud", "scripts")),
                        "sons": str(Path(pastaPath, "clientmud", "sons")),
                        "pastas-dos-muds": {}
                    },
                    'personagens': []
                }
                
                self.app.config.atualizaJson(dic)
                self.app.pastas.config = self.app.config
                self.app.pastas.criaPastaGeral()
                
                wx.MessageBox("As configurações foram finalizadas com êxito. O aplicativo será encerrado agora. Por favor, inicie-o novamente.", "Configuração Concluída", wx.OK | wx.ICON_INFORMATION)
                self.Destroy()
                sys.exit()
            else:
                wx.MessageBox("Por favor, digite uma pasta válida.", "Erro", wx.ICON_ERROR)

class DialogoConfiguracoesGerais(wx.Dialog):
    def __init__(self, pai=None):
        super().__init__(parent=pai, title="Configurações gerais")
        self.app = wx.GetApp()
        painel = wx.Panel(self)
        self.Bind(wx.EVT_CHAR_HOOK, self.teclaPressionada)

        gerais = self.app.config.config.get('gerais', {})

        self.verificaAtualizacao = wx.CheckBox(painel, label='&Verificar atualizações automaticamente ao iniciar')
        self.verificaAtualizacao.SetValue(gerais.get('verifica-atualizacoes-automaticamente', True))

        self.ignorarUrlsMsp = wx.CheckBox(painel, label='&Ignorar sons e músicas baixados de links enviados pelos MUDs (parâmetro U do MSP)')
        self.ignorarUrlsMsp.SetValue(gerais.get('ignorar-urls-msp', False))

        btnSalvar = wx.Button(painel, wx.ID_OK, label='&Salvar')
        btnSalvar.Bind(wx.EVT_BUTTON, self.salva)

        wx.Button(painel, wx.ID_CANCEL, label='&Cancelar')

        aplica_tema_se_ativo(self)
        self.verificaAtualizacao.SetFocus()

    def teclaPressionada(self, evento):
        if evento.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
        else:
            evento.Skip()

    def salva(self, evento):
        gerais = self.app.config.config['gerais']
        gerais['verifica-atualizacoes-automaticamente'] = self.verificaAtualizacao.GetValue()
        gerais['ignorar-urls-msp'] = self.ignorarUrlsMsp.GetValue()
        self.app.config.atualizaJson()
        self.EndModal(wx.ID_OK)