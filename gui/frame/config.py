import wx
from pathlib import Path

from gui.theme import aplica_tema

class ConfigMixin:
    """Carregamento e persistência das configurações do personagem/conexão
    (variáveis de sessão, triggers, timers, keys e macros)."""

    def _defineVariaveis(self):
        self.pasta_geral = str(Path(self.app.config.config['gerais']['diretorio-de-dados']) / "clientmud")
        self.nome_mud = None
        self._chave_personagem = None
        self.ignorar_urls_msp = self.app.config.config['gerais'].get('ignorar-urls-msp', False)
        if self.json_personagem:
            self.nome = self.json_personagem['nome']
            self.senha = self.json_personagem.get('senha')
            self.reproduzirSons = self.json_personagem.get('reproduzir_sons_fora_janela', True)
            self.lerMensagens = self.json_personagem.get('ler_fora_janela', False)
            self.login = self.json_personagem.get('login_automático', False)
            self.usar_volume_padrao = self.json_personagem.get('usar_volume_padrao', False)
            self.volume_padrao = self.json_personagem.get('volume_padrao', 100)
            if self.json_personagem.get('ignorar_urls_msp', False):
                self.ignorar_urls_msp = True
            self.app.msp.defineIgnorarUrls(self.ignorar_urls_msp)
            self.modo_escuro = self.json_personagem.get('modo_escuro', True)
            self.app.modo_escuro = self.modo_escuro

            chave = self.json_personagem.get('_chave')
            pastas = self.app.config.config['gerais']['pastas-dos-muds']
            if not chave or chave not in pastas:
                mud_hint = self.json_personagem.get('mud', '')
                if mud_hint:
                    candidata = f"{self.nome}@{mud_hint}"
                    if candidata in pastas:
                        chave = candidata
                if not chave or chave not in pastas:
                    for k in pastas:
                        if (k.split('@')[0] if '@' in k else k) == self.nome:
                            chave = k
                            break
                if chave:
                    self.json_personagem['_chave'] = chave
            self._chave_personagem = chave

            if not chave or chave not in pastas:
                self.pasta_logs = Path(self.pasta_geral) / 'logs'
                self.pasta_scripts = Path(self.pasta_geral) / 'scripts'
                self.pasta_sons = Path(self.pasta_geral) / 'sons'
                self.carregaTriggers()
                self.carregaTimers()
                self.carregaKeys()
                self.carregaMacros()
                return

            pasta_base_personagem = Path(pastas[chave])
            self.nome_mud = pasta_base_personagem.parent.name
            self.pasta_personagem = pasta_base_personagem
            self.pasta_logs = pasta_base_personagem / 'logs'
            self.pasta_scripts = pasta_base_personagem / 'scripts'
            self.pasta_sons = pasta_base_personagem.parent / 'sons'
        else:
            self.pasta_logs = Path(self.pasta_geral) / 'logs'
            self.pasta_scripts = Path(self.pasta_geral) / 'scripts'
            self.pasta_sons = Path(self.pasta_geral) / 'sons'
            self.reproduzirSons = self.app.config.config['gerais'].get('toca-sons-fora-da-janela', True)
            self.lerMensagens = self.app.config.config['gerais'].get('ler fora da janela', True)
            self.login = False
            self.usar_volume_padrao = False
            self.volume_padrao = 100
            self.app.msp.defineIgnorarUrls(self.ignorar_urls_msp)
            ultima_conexao = self.app.config.config['gerais'].get('ultima-conexao') or []
            self.modo_escuro = bool(ultima_conexao[3]) if len(ultima_conexao) > 3 else True
            self.app.modo_escuro = self.modo_escuro

        self.carregaTriggers()
        self.carregaTimers()
        self.carregaKeys()
        self.carregaMacros()

    def aplicaConfiguracoesSessao(self):
        """Reaplica na sessão conectada as configurações com efeito imediato,
        relendo-as do personagem (ou das configurações gerais em conexões
        manuais/rápidas). Deve ser chamado após alterar as configurações para
        que passem a valer sem precisar reconectar."""
        gerais = self.app.config.config['gerais']
        self.ignorar_urls_msp = gerais.get('ignorar-urls-msp', False)
        if self.json_personagem:
            self.reproduzirSons = self.json_personagem.get('reproduzir_sons_fora_janela', True)
            self.lerMensagens = self.json_personagem.get('ler_fora_janela', False)
            self.login = self.json_personagem.get('login_automático', False)
            self.usar_volume_padrao = self.json_personagem.get('usar_volume_padrao', False)
            self.volume_padrao = self.json_personagem.get('volume_padrao', 100)
            if self.json_personagem.get('ignorar_urls_msp', False):
                self.ignorar_urls_msp = True
            self.modo_escuro = self.json_personagem.get('modo_escuro', True)
        else:
            self.reproduzirSons = gerais.get('toca-sons-fora-da-janela', True)
            self.lerMensagens = gerais.get('ler fora da janela', True)

        self.app.msp.defineIgnorarUrls(self.ignorar_urls_msp)
        self.app.modo_escuro = self.modo_escuro
        aplica_tema(self)

    def renomeiaPersonagemConectado(self, chave_antigo, nome_novo):
        """Renomeia o personagem enquanto a sessão está conectada, sem perder o
        log em uso nem mensagens que cheguem durante a operação.

        Fecha o log atual (acumulando as mensagens que chegarem), renomeia as
        pastas do personagem, reabre o mesmo log já no novo caminho, grava as
        mensagens pendentes e atualiza todas as referências (pastas de logs,
        scripts e sons, título da janela e chave do personagem). Retorna True
        em caso de sucesso."""
        from models.config import chave_personagem, mud_de_chave

        client = self.app.client
        log_aberto = bool(getattr(client, 'arquivoLog', None)) and not client.arquivoLog.closed
        nome_arquivo_log = client.log.name if (log_aberto and getattr(client, 'log', None)) else None

        if log_aberto:
            client.pausaLog()

        sucesso = self.app.personagem.renomeiaPersonagem(chave_antigo, nome_novo)

        if not sucesso:
            # Reabre o log no caminho original para não descartar as pendentes.
            if log_aberto:
                caminho_original = str(self.pasta_logs / nome_arquivo_log) if nome_arquivo_log else None
                client.retomaLog(caminho_original)
            return False

        mud = mud_de_chave(chave_antigo)
        chave_nova = chave_personagem(nome_novo, mud) if mud else nome_novo
        pasta_base = Path(self.app.config.config['gerais']['pastas-dos-muds'][chave_nova])

        self.pasta_personagem = pasta_base
        self.pasta_logs = pasta_base / 'logs'
        self.pasta_scripts = pasta_base / 'scripts'
        self.pasta_sons = pasta_base.parent / 'sons'
        self.nome = nome_novo
        self._chave_personagem = chave_nova
        if self.json_personagem is not None:
            self.json_personagem['nome'] = nome_novo
            self.json_personagem['_chave'] = chave_nova

        # Reabre o mesmo log (mesmo arquivo) agora no novo caminho e escreve as
        # mensagens que ficaram pendentes durante a renomeação.
        if log_aberto and nome_arquivo_log:
            client.retomaLog(str(self.pasta_logs / nome_arquivo_log))
        client.definePastaLog(str(self.pasta_logs), nome_novo)
        self.app.msp.definePastaSons(self.pasta_sons)

        self.SetTitle(f"{nome_novo} Cliente mud.")
        return True

    def aplicaEdicaoPersonagem(self, chave_nova, novo_dic):
        """Após editar o personagem conectado pelo diálogo padrão, mescla os
        dados salvos no personagem em memória e reaplica na sessão as
        configurações com efeito imediato. As demais (nome, endereço, porta,
        login automático, etc.) valerão na próxima conexão/login."""
        if not novo_dic:
            return
        campos = (
            'nome', 'mud', 'senha', 'endereço', 'porta', 'conexao_segura',
            'login_automático', 'reproduzir_sons_fora_janela', 'ler_fora_janela',
            'usar_volume_padrao', 'volume_padrao', 'ignorar_urls_msp', 'modo_escuro',
        )
        for campo in campos:
            if campo in novo_dic:
                self.json_personagem[campo] = novo_dic[campo]
        if chave_nova:
            self.json_personagem['_chave'] = chave_nova
            self._chave_personagem = chave_nova
        self.aplicaConfiguracoesSessao()

    def carregaTriggers(self):
        from models.trigger import Trigger
        triggers_globais = [Trigger(cfg) for cfg in self.app.config.carregaGlobalConfig().get('triggers', [])]
        triggers_mud = [Trigger(cfg) for cfg in self.app.config.carregaMudConfig(self.nome_mud).get('triggers', [])] if self.nome_mud else []
        if self.json_personagem:
            triggers_locais = [Trigger(cfg) for cfg in self.json_personagem.get('triggers', [])]
        else:
            cfg_manual = self.app.config.config.get('configuracoes-conexoes-manuais', {}) if self.app.config.config else {}
            triggers_locais = [Trigger(cfg) for cfg in cfg_manual.get('triggers', [])]
        self.triggers = triggers_globais + triggers_mud + triggers_locais

    def carregaTimers(self):
        from models.timer import Timer
        timers_globais = [Timer(cfg) for cfg in self.app.config.carregaGlobalConfig().get('timers', [])]
        timers_mud = [Timer(cfg) for cfg in self.app.config.carregaMudConfig(self.nome_mud).get('timers', [])] if self.nome_mud else []
        if self.json_personagem:
            timers_locais = [Timer(cfg) for cfg in self.json_personagem.get('timers', [])]
        else:
            cfg_manual = self.app.config.config.get('configuracoes-conexoes-manuais', {}) if self.app.config.config else {}
            timers_locais = [Timer(cfg) for cfg in cfg_manual.get('timers', [])]
        self.timers = timers_globais + timers_mud + timers_locais

    def carregaKeys(self):
        from models.key import Key
        keys_globais = [Key(cfg) for cfg in self.app.config.carregaGlobalConfig().get('keys', [])]
        keys_mud = [Key(cfg) for cfg in self.app.config.carregaMudConfig(self.nome_mud).get('keys', [])] if self.nome_mud else []
        if self.json_personagem:
            keys_locais = [Key(cfg) for cfg in self.json_personagem.get('keys', [])]
        else:
            cfg_manual = self.app.config.config.get('configuracoes-conexoes-manuais', {}) if self.app.config.config else {}
            keys_locais = [Key(cfg) for cfg in cfg_manual.get('keys', [])]
        self.keys = keys_globais + keys_mud + keys_locais

    def carregaMacros(self):
        from models.macro import Macro
        macros_globais = [Macro(cfg) for cfg in self.app.config.carregaGlobalConfig().get('macros', [])]
        macros_mud = [Macro(cfg) for cfg in self.app.config.carregaMudConfig(self.nome_mud).get('macros', [])] if self.nome_mud else []
        if self.json_personagem:
            macros_locais = [Macro(cfg) for cfg in self.json_personagem.get('macros', [])]
        else:
            cfg_manual = self.app.config.config.get('configuracoes-conexoes-manuais', {}) if self.app.config.config else {}
            macros_locais = [Macro(cfg) for cfg in cfg_manual.get('macros', [])]
        self.macros = macros_globais + macros_mud + macros_locais

    def salvaConfiguracoesPersonagem(self):
        triggers_local, triggers_mud, triggers_global = [], [], []
        for t in self.triggers:
            if t.escopo == 2: triggers_global.append(t.to_dict())
            elif t.escopo == 1: triggers_mud.append(t.to_dict())
            else: triggers_local.append(t.to_dict())

        timers_local, timers_mud, timers_global = [], [], []
        for t in self.timers:
            if t.escopo == 2: timers_global.append(t.to_dict())
            elif t.escopo == 1: timers_mud.append(t.to_dict())
            else: timers_local.append(t.to_dict())

        keys_local, keys_mud, keys_global = [], [], []
        for k in self.keys:
            if k.escopo == 2: keys_global.append(k.to_dict())
            elif k.escopo == 1: keys_mud.append(k.to_dict())
            else: keys_local.append(k.to_dict())

        macros_local, macros_mud, macros_global = [], [], []
        for m in self.macros:
            if m.escopo == 2: macros_global.append(m.to_dict())
            elif m.escopo == 1: macros_mud.append(m.to_dict())
            else: macros_local.append(m.to_dict())

        self.app.config.salvaGlobalConfig(triggers_global, timers_global, keys_global, macros_global)

        if self.nome_mud:
            self.app.config.salvaMudConfig(self.nome_mud, triggers_mud, timers_mud, keys_mud, macros_mud)
        else:
            for item in triggers_mud:
                item['escopo'] = 0
                triggers_local.append(item)
            for item in timers_mud:
                item['escopo'] = 0
                timers_local.append(item)
            for item in keys_mud:
                item['escopo'] = 0
                keys_local.append(item)
            for item in macros_mud:
                item['escopo'] = 0
                macros_local.append(item)

        if not self.json_personagem:
            self.app.config.atualizaConfigsConexaoManual(triggers_local, timers_local, keys_local, macros_local)
            return

        self.json_personagem['triggers'] = triggers_local
        self.json_personagem['timers'] = timers_local
        self.json_personagem['keys'] = keys_local
        self.json_personagem['macros'] = macros_local

        chave = self._chave_personagem or self.nome
        if not self.app.personagem.atualizaPersonagem(chave, self.json_personagem):
            wx.MessageBox("Falha ao salvar as configurações do personagem.", "Erro", wx.ICON_ERROR)
