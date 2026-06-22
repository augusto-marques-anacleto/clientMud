import subprocess
import wx
from pathlib import Path

from core.external_scripts import GerenciadorScriptsExternos


class DialogoScriptsExternos(wx.Dialog):

    def __init__(self, parent, pasta_scripts):
        super().__init__(parent, title="Scripts Externos")
        self._pasta = pasta_scripts
        self._habilitados = set(GerenciadorScriptsExternos.carregar_habilitados(pasta_scripts))
        painel = wx.Panel(self)

        self.lista = wx.ListCtrl(painel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.lista.InsertColumn(0, "Ativo")
        self.lista.InsertColumn(1, "Script")
        self.lista.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._toggle)
        self.lista.Bind(wx.EVT_LIST_ITEM_SELECTED, self._ao_selecionar)
        self.lista.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._ao_selecionar)
        self.lista.Bind(wx.EVT_KEY_DOWN, self._tecla_lista)

        self.btn_toggle = wx.Button(painel, label="Ativar/Desativar\tCtrl+D")
        self.btn_toggle.Bind(wx.EVT_BUTTON, self._toggle)
        self.btn_toggle.Enable(False)

        btn_pasta = wx.Button(painel, label="Abrir Pasta de Scripts")
        btn_pasta.Bind(wx.EVT_BUTTON, self._abre_pasta)

        btn_fechar = wx.Button(painel, wx.ID_OK, label="Fechar")
        btn_fechar.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_OK))

        id_toggle = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, self._toggle, id=id_toggle)
        self.SetAcceleratorTable(wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('D'), id_toggle),
        ]))

        self._preenche_lista()
        btn_fechar.SetFocus()

    def _preenche_lista(self):
        self.lista.DeleteAllItems()
        scripts = GerenciadorScriptsExternos.listar_scripts(self._pasta)
        for i, nome in enumerate(scripts):
            estado = "Ativado" if nome in self._habilitados else "Desativado"
            self.lista.InsertItem(i, estado)
            self.lista.SetItem(i, 1, nome)

        total = self.lista.GetItemCount()
        if total > 0:
            self.lista.Select(0)
            self.lista.Focus(0)
        else:
            self.btn_toggle.Enable(False)

    def _ao_selecionar(self, evt):
        self.btn_toggle.Enable(self.lista.GetFirstSelected() != -1)
        evt.Skip()

    def _toggle(self, evt):
        idx = self.lista.GetFirstSelected()
        if idx == -1:
            return
        nome = self.lista.GetItemText(idx, 1)
        if nome in self._habilitados:
            self._habilitados.discard(nome)
            self.lista.SetItem(idx, 0, "Desativado")
            wx.GetApp().fale(f"Script {nome} desativado.")
        else:
            self._habilitados.add(nome)
            self.lista.SetItem(idx, 0, "Ativado")
            wx.GetApp().fale(f"Script {nome} ativado.")
        GerenciadorScriptsExternos.salvar_habilitados(self._pasta, list(self._habilitados))

    def _tecla_lista(self, evt):
        if evt.GetKeyCode() == wx.WXK_SPACE:
            self._toggle(None)
        else:
            evt.Skip()

    def _abre_pasta(self, evt):
        pasta = Path(self._pasta)
        pasta.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer", str(pasta)])
