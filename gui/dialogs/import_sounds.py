import wx
import wx.lib.newevent
from threading import Thread
import tempfile
import os
from core.importer import SoundImporter

EvtProgresso, EVT_PROGRESSO = wx.lib.newevent.NewEvent()
EvtFim, EVT_FIM = wx.lib.newevent.NewEvent()

class ThreadTrabalho(Thread):
    def __init__(self, janela_progresso, importer, url=None, caminho_local=None):
        super().__init__(daemon=True)
        self.janela = janela_progresso
        self.importer = importer
        self.url = url
        self.caminho_local = caminho_local

    def callback_progresso(self, status, porcentagem, detalhe=""):
        wx.PostEvent(self.janela, EvtProgresso(status=status, porcentagem=porcentagem, detalhe=detalhe))

    def run(self):
        sucesso = False
        if self.caminho_local:
            sucesso = self.importer.extrair_e_copiar(self.caminho_local, self.callback_progresso)
        elif self.url:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
                caminho_temp = temp_file.name
                
            download_ok = self.importer.baixar_da_url(self.url, caminho_temp, self.callback_progresso)
            
            if download_ok and not self.importer.cancelar:
                sucesso = self.importer.extrair_e_copiar(caminho_temp, self.callback_progresso)
                
            try:
                os.unlink(caminho_temp)
            except:
                pass

        wx.PostEvent(self.janela, EvtFim(sucesso=sucesso, cancelado=self.importer.cancelar))

class JanelaProgresso(wx.Frame):
    def __init__(self, parent, importer, url=None, caminho_local=None):
        super().__init__(parent, title="Gerenciador de Sons", style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))
        self.importer = importer
        
        painel = wx.Panel(self)
        
        self.texto_status = wx.StaticText(painel, label="Iniciando processo...")
        self.barra_progresso = wx.Gauge(painel, range=100)
        
        self.btn_cancelar = wx.Button(painel, wx.ID_CANCEL, label="Cancelar")
        self.btn_cancelar.Bind(wx.EVT_BUTTON, self.ao_cancelar)
        
        self.Bind(EVT_PROGRESSO, self.atualiza_progresso)
        self.Bind(EVT_FIM, self.ao_finalizar)
        self.Bind(wx.EVT_CLOSE, self.ao_cancelar)
        self.Bind(wx.EVT_CHAR_HOOK, self.tecla_pressionada)

        self.Show()
        self.btn_cancelar.SetFocus()
        
        ThreadTrabalho(self, self.importer, url, caminho_local).start()

    def tecla_pressionada(self, evento):
        if evento.GetKeyCode() == wx.WXK_ESCAPE:
            self.ao_cancelar(None)
        else:
            evento.Skip()

    def atualiza_progresso(self, evento):
        texto_base = ""
        if evento.status == "baixando": texto_base = "Baixando pacote de sons..."
        elif evento.status == "extraindo": texto_base = "Extraindo arquivos do ZIP..."
        elif evento.status == "copiando": texto_base = "Movendo sons para a pasta do personagem..."
        
        texto_completo = f"{texto_base} {evento.porcentagem}%"
        if hasattr(evento, 'detalhe') and evento.detalhe:
            texto_completo += f" ({evento.detalhe})"
            
        self.texto_status.SetLabel(texto_completo)
        self.barra_progresso.SetValue(evento.porcentagem)
        
        if not hasattr(self, 'ultimo_status') or self.ultimo_status != evento.status:
            self.ultimo_status = evento.status
            try:
                wx.GetApp().fale(texto_base)
            except:
                pass

    def ao_cancelar(self, evento):
        self.texto_status.SetLabel("Cancelando... Por favor, aguarde.")
        self.btn_cancelar.Disable()
        self.importer.cancelar = True

    def ao_finalizar(self, evento):
        if evento.cancelado:
            wx.MessageBox("A importação de sons foi cancelada pelo usuário.", "Cancelado", wx.ICON_INFORMATION)
        elif evento.sucesso:
            try:
                wx.GetApp().fale("Pacote de sons importado com sucesso!")
            except:
                pass
            wx.MessageBox("Pacote de sons atualizado com sucesso!", "Sucesso", wx.ICON_INFORMATION)
        else:
            msg = "Não foi possível baixar os sons automaticamente.\n\nSe for um link do Mega ou se houver erro de permissão, faça o download manual do pacote e importe-o utilizando a opção 'Importar arquivo local'."
            wx.MessageBox(msg, "Erro na Importação", wx.ICON_ERROR)
        self.Destroy()

class DialogoPedeURL(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Baixar Pacote de Sons")
        painel = wx.Panel(self)
        
        wx.StaticText(painel, label="Cole o link do pacote de sons (Drive/Dropbox/Link Direto):")
        
        self.campo_url = wx.TextCtrl(painel, style=wx.TE_PROCESS_ENTER)
        
        self.btn_baixar = wx.Button(painel, wx.ID_OK, label="Baixar")
        self.btn_cancelar = wx.Button(painel, wx.ID_CANCEL, label="Cancelar")
        
        self.campo_url.Bind(wx.EVT_TEXT_PASTE, self.ao_colar_url)
        self.campo_url.Bind(wx.EVT_TEXT_ENTER, self.ao_apertar_enter)
        
        self.campo_url.SetFocus()

    def ao_colar_url(self, evento):
        if not wx.TheClipboard.Open():
            return
            
        if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT)):
            data = wx.TextDataObject()
            wx.TheClipboard.GetData(data)
            texto_sujo = data.GetText()
            
            texto_sem_quebras = texto_sujo.replace('\n', '').replace('\r', '').strip()
            
            self.campo_url.WriteText(texto_sem_quebras)
        else:
            evento.Skip()
            
        wx.TheClipboard.Close()

    def ao_apertar_enter(self, evento):
        self.EndModal(wx.ID_OK)