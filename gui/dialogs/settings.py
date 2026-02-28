import wx
import sys
from pathlib import Path

class DialogoConfiguracoes(wx.Dialog):
    def __init__(self):
        super().__init__(parent=None, title="Configurações")
        self.app = wx.GetApp()
        painel = wx.Panel(self)
        
        pastaExecutavel = Path(sys.executable)
        self.pastaInicial = str(pastaExecutavel.parent)

        wx.StaticText(painel, label='Pasta de dados.')
        
        self.campoTextoPasta = wx.TextCtrl(painel, value=self.pastaInicial)
        
        btnEscolhePasta = wx.Button(painel, label='&Escolher pasta de dados')
        btnEscolhePasta.Bind(wx.EVT_BUTTON, self.escolhePasta)
        
        self.reproducaoForaDaJanela = wx.CheckBox(painel, label='Reproduzir sons fora da janela do MUD')
        
        self.falaForaDaJanela = wx.CheckBox(painel, label='Ler as mensagens fora da janela do MUD')
        
        self.verificaAtualizacao = wx.CheckBox(painel, label='Verificar atualizações automaticamente ao iniciar')
        self.verificaAtualizacao.SetValue(True)
        
        btnFinaliza = wx.Button(painel, label='&Finalizar configuração.')
        btnFinaliza.Bind(wx.EVT_BUTTON, self.finalizaConfiguracao)


    def escolhePasta(self, evento):
        dialogo = wx.DirDialog(self, 'Escolha de pasta')
        if dialogo.ShowModal() == wx.ID_OK:
            self.pastaInicial = dialogo.GetPath()
            self.campoTextoPasta.SetValue(self.pastaInicial)
        dialogo.Destroy()

    def finalizaConfiguracao(self, evento):
        pasta = self.campoTextoPasta.GetValue()
        if pasta:
            pastaPath = Path(pasta)
            if pastaPath.exists():
                self.pastaInicial = pasta
                
                dic = {
                    'gerais': {
                        "toca-sons-fora-da-janela": self.reproducaoForaDaJanela.GetValue(),
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