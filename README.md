# ClientMUD

**ClientMUD** é um cliente avançado para jogos *Multi-User Dungeon* (MUD), desenvolvido em **Python**, com foco em automação, personalização e acessibilidade.  
O projeto oferece recursos como triggers, timers, atalhos de teclado, suporte a som (MSP), salvamento automático de logs e escrita por voz.

---

## Visão Geral

O **ClientMUD** permite conectar-se a servidores MUD via Telnet, automatizar comandos, reagir a eventos do jogo com ações personalizadas e organizar configurações específicas por personagem.  
Foi criado para oferecer uma experiência fluida e configurável, com suporte nativo a leitura e escrita acessíveis.

---

## Funcionalidades Principais

### **Timers**
- Permitem enviar **comandos repetidos** automaticamente a cada *X* segundos.
- Cada timer é totalmente configurável (intervalo e comando a enviar).

### **Triggers**
- Disparam ações automáticas quando uma mensagem específica é recebida do MUD.
- Tipos de ação:
  - **Comando:** envia um comando de resposta ao MUD.
  - **Som:** toca um som local quando o gatilho ocorre.
  - **Histórico:** registra apenas as mensagens correspondentes ao gatilho em um histórico personalizado.

### **Keys (Atalhos de Teclado)**
- Permitem mapear qualquer tecla ou combinação de teclas para **enviar comandos personalizados** ao MUD.
- Exemplo: `F1` para "ver", `Ctrl+A` para "ajuda", etc.

### 🗂️ **Configurações e Perfis**
- Todas as configurações são salvas automaticamente em **arquivos JSON**, incluindo triggers, timers e keys.
- Estrutura de salvamento:
```

pasta_de_dados/
└── muds/
└── nome_do_mud/
└── nome_do_personagem/
└── nome_do_personagem.json

````
- O arquivo `config.json` guarda as configurações principais e as usadas em conexões manuais (sem personagens favoritos).

### **Escrita por Voz**
- Função de reconhecimento de voz integrada.
- Pode ser ativada via:
- Menu **Ferramentas → Escrita por Voz**, ou  
- Atalho **Ctrl + O**.
- Permite ditar comandos para o MUD sem precisar digitar.

### **Logs Automáticos**
- O cliente salva automaticamente os logs de cada sessão dentro da pasta do personagem.
- Mantém histórico de todas as interações, incluindo mensagens enviadas e recebidas.

### **Suporte a MSP (Mud Sound Protocol)**
- Reproduz efeitos sonoros e músicas enviados pelo servidor MUD via MSP.

---

## Estrutura do Projeto

| Arquivo / Pasta | Descrição |
|-----------------|------------|
| `cliente.py` | Núcleo principal do cliente (enviar de comandos para o MUD). |
| `janelamud.pyw` | Interface gráfica principal. |
| `configuracoes.py` | Manipula as preferências gerais e conexões. |
| `trigger.py` | Classe de uma trigger |
| `timer.py` | classe dos timers |
| `key.py` | Classe das keys |
| `msp.py` | Implementa o suporte ao Mud Sound Protocol. |
| `log.py` | Salvamento de log de erros ocorridos no programa no arquivo erros.log |
| `atualizador.pyw` | Atualizador automático do cliente. |
| `telnetlib.py` | Comunicação via Telnet. |
| `ambiente_compilacao/` | Ambiente venv pronto para compilação do projeto com Nuitka. |

---

## Como Usar

### 1. Instalação

```bash
git clone https://github.com/augusto-marques-anacleto/clientmud.git
cd clientmud
```

Certifique-se de ter o **Python 3.x** instalado e os módulos accessible_output2, sound-lib, pyaudio, speech_recognition e wxpython .
Em seguida, execute:

```bash
python janelamud.pyw
```

---

### 2. Conexão a um MUD

1. Abra o programa e realize as configurações iniciais.
2. No menu principal, escolha **Adicionar Personagem**.
3. Informe o nome do MUD, servidor, porta, o nome do personagem e opcionalmente a senha e se deseja logar automaticamente.
4. O cliente criará automaticamente a estrutura de pastas e o arquivo JSON correspondente.
5. Clique em **Conectar** no menu principal com o personagem selecionado na lista para iniciar a sessão.

---

### 3. Configurações

* Todas as opções de triggers, timers e teclas podem ser configuradas dentro da interface.
* As alterações são salvas automaticamente ao sair das janelas de gerenciador.

---

### 4. Escrita por Voz

Ative via menu **Ferramentas → Escrita por Voz** ou pressione **Ctrl + O** estando dentro do MUD.
Diga o comando que deseja enviar após a mensagem comece a falar — ele será automaticamente transcrito e enviado ao MUD.

## Acessibilidade

* Compatível com leitores de tela (ex.: NVDA).
* Escrita por voz integrada.
* Interface otimizada para navegação por teclado.

---

## Contribuindo

1. Faça um fork do repositório.
2. Crie uma branch para sua modificação:

   ```bash
   git checkout -b minha-modificacao
   ```
3. Envie suas mudanças e abra um *pull request*.

---

## Contato

Para sugestões ou relatórios de bugs, abra uma *Issue* em:
[github.com/augusto-marques-anacleto/clientmud/issues](https://github.com/augusto-marques-anacleto/clientmud/issues)