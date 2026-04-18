# ClientMUD

Cliente de MUD de código aberto para Windows, desenvolvido pensando em acessibilidade para pessoas cegas e com baixa visão. Utiliza leitor de tela via accessible_output2 e foi projetado para ser totalmente operável pelo teclado.

---

## Download e Instalação

Acesse a página de releases e baixe o instalador mais recente:
https://github.com/augusto-marques-anacleto/clientmud/releases/

Execute o instalador e siga as instruções. O cliente será instalado e um atalho será criado na área de trabalho.

---

## Primeiros Passos

### Adicionando um personagem

1. Abra o ClientMUD. A janela de conexões será exibida.
2. Pressione o botão "Adicionar personagem" ou use Ctrl+A.
3. Preencha os campos: nome do MUD, nome do personagem, senha (opcional), endereço e porta do servidor.
4. Marque "Logar automaticamente" se quiser que o cliente envie usuário e senha ao conectar.
5. Salve. O personagem aparecerá na lista.

### Conectando

1. Selecione o personagem na lista e pressione Enter ou clique em "Conectar".
2. Aguarde a conexão. Se falhar, uma mensagem de erro será exibida.
3. Para fechar a janela do MUD e voltar à lista de personagens, pressione Escape.

### Conexão manual (sem personagem cadastrado)

Use o botão "Conexão manual" ou Ctrl+M na tela inicial. Informe endereço e porta.

---

## Navegação e Atalhos

### Na janela do MUD

| Tecla | Ação |
|---|---|
| Enter | Envia o comando digitado |
| Shift+Enter | Envia sem limpar o campo de entrada |
| Seta para cima | Comando anterior no histórico |
| Seta para baixo | Próximo comando no histórico |
| Escape | Fecha a janela e volta à lista de personagens |
| Ctrl+H | Abre histórico customizado |
| Ctrl+M | Interrompe a música em reprodução |
| Ctrl+T | Gerenciar triggers |
| Ctrl+I | Gerenciar timers |
| Ctrl+K | Gerenciar atalhos de teclado |
| Ctrl+U | Gerenciar macros e rotas |
| Ctrl+O | Escrever por voz (ditado) |
| Ctrl+G | Abrir pasta geral de dados |
| Ctrl+L | Abrir pasta de logs |
| Ctrl+R | Abrir pasta de scripts |
| Ctrl+S | Abrir pasta de sons |
| Ctrl+B | Baixar pacote de sons via link |
| Ctrl+Shift+E | Exportar backup |
| Ctrl+Shift+I | Importar backup |
| F1 | Abrir ajuda |

### Repetição de comandos

Para enviar um mesmo comando várias vezes, use o formato `#N comando`. Exemplo: `#5 norte` envia "norte" cinco vezes (máximo 100 repetições).

---

## Funcionalidades

### Triggers

Padrões de texto que executam comandos automaticamente quando o servidor envia uma mensagem correspondente.

- Suporte a coringas: `*` (qualquer texto), `?` (qualquer caractere), `&` (uma palavra), `@` (número)
- Comparação sem diferenciar maiúsculas de minúsculas
- Escopo: apenas este personagem, todo o MUD ou global (todos os MUDs)

Acesse por: menu Ferramentas > Gerenciar Triggers ou Ctrl+T.

### Timers

Comandos executados automaticamente em intervalos de tempo definidos.

- Configuração de intervalo em segundos
- Ativação e desativação individual
- Escopo: personagem, MUD ou global

Acesse por: menu Ferramentas > Gerenciar Timers ou Ctrl+I.

### Macros e Rotas

Sequências de comandos executadas de uma vez ao digitar o nome da macro.

- Comandos separados por ponto e vírgula (`;`)
- Intervalo configurável entre cada comando
- Gravação de rota: use o menu Ferramentas > Macros e Rotas > Iniciar Gravação, jogue normalmente e interrompa para salvar os comandos como macro
- Escopo: personagem, MUD ou global

Acesse por: menu Ferramentas > Macros e Rotas > Gerenciar Macros ou Ctrl+U.

### Atalhos de Teclado (Keys)

Teclas ou combinações de teclas que enviam comandos ao servidor.

- Suporte a F1–F12, Numpad 0–9, letras e números com Ctrl ou Alt
- Escopo: personagem, MUD ou global

Acesse por: menu Ferramentas > Gerenciar Atalhos ou Ctrl+K.

### Histórico Customizado

Triggers podem direcionar linhas para históricos separados, organizando mensagens por categoria (combate, chat, etc.). Abra com Ctrl+H. Quando há mais de um histórico, uma lista de escolha será exibida.

### Ditado por Voz

Fale um comando em vez de digitá-lo. O cliente usa o microfone, reconhece a fala e envia o comando. Pontuação pode ser ditada por extenso ("ponto de interrogação", "ponto e vírgula", etc.).

Acesse por: menu Ferramentas > Escrever por Voz ou Ctrl+O.

### Sons (MSP)

O cliente suporta reprodução de sons e música. Os arquivos de som do personagem ficam na pasta `sons` dentro da pasta do personagem.

- Ctrl+PgUp / Ctrl+PgDn: ajusta volume da música
- Ctrl+Shift+PgUp / Ctrl+Shift+PgDn: ajusta volume dos efeitos sonoros
- Ctrl+M: interrompe a música atual

Baixe ou importe pacotes de sons pelo menu Ferramentas > Gerenciar Sons.

### Logs

Todas as sessões são salvas automaticamente em arquivos de texto na pasta de logs do personagem. O nome do arquivo inclui a hora e a data da conexão.

Acesse a pasta de logs pelo menu Pastas > Abrir Pasta de Logs ou Ctrl+L.

### Backup

Exporte todas as configurações e personagens em um arquivo `.mudbak` para guardar ou transferir para outro computador. Importe pelo mesmo menu para restaurar tudo.

Acesse por: menu Ferramentas > Backup.

---

## Atualizações

O cliente verifica atualizações automaticamente ao iniciar (se habilitado nas configurações). Para verificar manualmente, use: menu Ajuda > Checar Atualizações.

---

## Desenvolvimento

### Requisitos

- Python 3.13
- Dependências: veja `requirements.txt`

### Instalando dependências

```
pip install -r requirements.txt
```

### Executando

```
python main.pyw
```

### Compilando

O projeto usa Nuitka para gerar o executável e InnoSetup para o instalador. O processo completo é automatizado pelo GitHub Actions ao criar uma tag `v*`.

---

## Créditos

Desenvolvido por **José Augusto**

Contribuições, revisões e suporte: **Gustavo Barrios**
https://github.com/gustavo-barrios2006

Repositório e releases:
https://github.com/augusto-marques-anacleto/clientmud/releases/

---

## Licença

Este projeto é de código aberto. Consulte o repositório para detalhes da licença.
