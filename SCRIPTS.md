# Manual de Scripts — ClientMUD

Scripts permitem automatizar qualquer sequência de ações no MUD com lógica,
variáveis, pausas e reação a respostas do servidor, sem travar a interface
nem bloquear outras triggers.

---

## Índice

1. Como criar um trigger de script
2. Os três modos de escrita
3. Funções disponíveis no script
4. Variáveis globais — setvar e getvar
5. Grupos de captura — grupo()
6. Aguardando respostas do servidor — waitfor
7. Grupos de triggers — ativar_grupo e desativar_grupo
8. Controle de concorrência
9. Tratamento de erros
10. Exemplos práticos completos
11. Scripts em Macros
12. O que funciona muito bem
13. O que não funciona ou tem limitações
14. Limitações de segurança
15. Referência rápida

---

## 1. Como criar um trigger de script

1. Pressione Ctrl+T para abrir o Gerenciador de Triggers.
2. Pressione Ctrl+A para adicionar um novo trigger.
3. Preencha o Nome.
4. Preencha o Grupo se quiser agrupar este trigger com outros para ativar ou desativar em conjunto. Pode deixar vazio.
5. Preencha o Padrão com o texto ou regex que deve ser detectado na saída do MUD.
6. No campo Valor da Ação, escreva o script.
7. Em Ação Principal, selecione Executar Script.
8. Em Concorrência, escolha o comportamento quando o trigger disparar enquanto o script já estiver rodando.
9. Salve com Salvar Trigger.

---

## 2. Os três modos de escrita

O motor detecta automaticamente qual modo você está usando. Não precisa declarar nada.

---

### Modo 1 — Simples (sem Python)

Escreva um comando por linha. Use wait N para pausar N segundos.

```
atacar goblin
wait 2
usar pocao de vida
wait 1
defender
```

Regras do modo simples:
- Cada linha não vazia é enviada como comando ao MUD
- wait N pausa por N segundos (aceita decimais: wait 0.5, wait 2.5)
- Linhas começando com # são comentários e ignoradas
- Ponto e vírgula dentro de uma linha separa vários comandos: norte; leste; sul

---

### Modo 2 — Python direto (sem definir função)

Escreva instruções Python com await diretamente. O motor envolve tudo automaticamente.

```
inimigo = grupo(0)
await send("atacar " + inimigo)
await wait(1.5)
setvar("ultimo_inimigo", inimigo)
```

---

### Modo 3 — Completo (controle total)

Defina explicitamente async def script(): para usar toda a expressividade do Python.

```
async def script():
    for i in range(3):
        await send("atacar")
        await wait(1)
    await send("descansar")
```

Scripts antigos escritos como async def script(ctx): continuam funcionando normalmente. O ctx ainda está disponível.

---

## 3. Funções disponíveis no script

Estas funções estão disponíveis diretamente, sem precisar de ctx ou qualquer prefixo.

---

### send(comando)

Envia um comando ao MUD. Suporta macros, sintaxe de repetição e ponto e vírgula.

```
await send("atacar")
await send("norte; leste; pegar chave")
await send("#5 atacar")
await send("minha_macro")
```

---

### wait(segundos)

Pausa não bloqueante. A interface continua respondendo, outras triggers continuam disparando.

```
await wait(2)
await wait(0.5)
await wait(30)
```

Não há limite prático de tempo de espera. Um script pode esperar horas sem problema.

---

### waitfor(padrao, timeout=30)

Suspende o script até uma linha do MUD combinar com o padrão regex. Retorna um MatchResult.

```
resultado = await waitfor(r"HP:\s*(\d+)/(\d+)", timeout=10)
hp_atual = int(resultado[0])
hp_maximo = int(resultado[1])
```

Atributos do MatchResult:
- resultado.linha — linha completa que fez match
- resultado[0], resultado[1], ... — grupos capturados pelo regex
- len(resultado) — quantidade de grupos

Se o timeout expirar sem match, lança TimeoutError.

---

### setvar(chave, valor)

Salva uma variável global persistente. Fica disponível para todos os scripts enquanto o cliente estiver conectado.

```
setvar("hp", "150")
setvar("modo_combate", "sim")
setvar("kills", str(kills + 1))
```

---

### getvar(chave, padrao=None)

Lê uma variável global. Retorna o valor padrão se a variável não existir.

```
hp = getvar("hp", "0")
modo = getvar("modo_combate", "nao")
kills = int(getvar("kills", "0"))
```

Sempre use getvar com um valor padrão para evitar erros na primeira execução.

---

### grupo(i)

Retorna o grupo de captura i do padrão da trigger que disparou o script. Começa em 0.

```
inimigo = grupo(0)
dano = int(grupo(1))
```

Se o índice não existir, retorna string vazia. Em scripts de macros, sempre retorna string vazia pois não há padrão de captura.

---

### linha()

Retorna a linha completa do MUD que disparou a trigger.

```
texto_completo = linha()
```

Em scripts de macros, retorna string vazia.

---

### cancelar_outros(nome_trigger=None)

Cancela outras instâncias do mesmo script em execução. Útil para garantir que só uma cópia rode por vez.

```
async def script():
    await cancelar_outros()
    await send("iniciar rotina")
```

---

### ativar_grupo(nome)

Ativa todos os triggers que têm o campo Grupo igual ao nome informado.

```
ativar_grupo("combate")
```

---

### desativar_grupo(nome)

Desativa todos os triggers do grupo informado.

```
desativar_grupo("navegacao")
```

---

## 4. Variáveis globais — setvar e getvar

Variáveis globais são compartilhadas entre todos os scripts de todos os triggers e persistem enquanto o cliente estiver conectado. São a forma de comunicação entre scripts diferentes.

Exemplo — trigger A atualiza o HP:
Padrão: HP:\s*(\d+)/(\d+)

```
setvar("hp", grupo(0))
setvar("hp_max", grupo(1))
```

Exemplo — trigger B usa o HP guardado:
Padrão: Você entra em combate

```
async def script():
    hp = int(getvar("hp", "100"))
    hp_max = int(getvar("hp_max", "100"))
    if hp_max > 0 and hp / hp_max < 0.5:
        await send("usar pocao antes de combater")
    await send("postura de ataque")
```

---

## 5. Grupos de captura — grupo()

Dependem do tipo de padrão configurado na trigger.

Com padrão de coringas:
- * captura qualquer texto
- & captura somente dígitos
- @ captura somente letras
- ? captura um único caractere

Exemplo com padrão "* te ataca causando & de dano":
Linha recebida: O troll te ataca causando 73 de dano

```
atacante = grupo(0)   # "O troll"
dano = grupo(1)       # "73"
```

Com padrão regex "(\w+) causou (\d+) de dano":

```
causador = grupo(0)
dano = int(grupo(1))
```

---

## 6. Aguardando respostas do servidor — waitfor

waitfor é o recurso mais poderoso. Permite que o script envie um comando e aguarde pela resposta específica antes de continuar.

Exemplo básico:

```
async def script():
    await send("examinar mochila")
    resultado = await waitfor(r"A mochila contém (\d+) itens", timeout=5)
    qtd = int(resultado[0])
    if qtd > 10:
        await send("say Minha mochila está cheia!")
```

Aguardando uma de várias respostas:

```
async def script():
    await send("abrir porta")
    try:
        res = await waitfor(r"(A porta abre|está trancada|Não há porta)", timeout=5)
        if "trancada" in res.linha:
            await send("usar chave na porta")
    except TimeoutError:
        await send("say A porta não respondeu.")
```

Loop aguardando regeneração:

```
async def script():
    while True:
        await send("status")
        try:
            res = await waitfor(r"HP:\s*(\d+)/(\d+)", timeout=10)
            hp_atual = int(res[0])
            hp_maximo = int(res[1])
            if hp_atual >= hp_maximo:
                break
            await send("descansar")
            await wait(5)
        except TimeoutError:
            await wait(3)
    await send("say HP cheio! Voltando ao combate.")
```

---

## 7. Grupos de triggers — ativar_grupo e desativar_grupo

Cada trigger tem um campo Grupo opcional. Triggers com o mesmo nome de grupo podem ser ativados e desativados em conjunto.

Exemplo de organização:
- Triggers de combate com grupo: combate
- Triggers de navegação com grupo: navegacao
- Triggers de quests com grupo: quests

Dentro de qualquer script:

```
async def script():
    desativar_grupo("navegacao")
    ativar_grupo("combate")
    await send("atacar")
```

Exemplo prático — ativar modo combate ao entrar em batalha:
Padrão: Você entra em combate com *

```
ativar_grupo("combate")
desativar_grupo("passive")
```

Exemplo — desativar combate ao sair:
Padrão: O combate terminou

```
desativar_grupo("combate")
ativar_grupo("passive")
```

---

## 8. Controle de concorrência

Define o que acontece quando o trigger dispara um script que já está rodando.

Nova instância a cada disparo: cria uma cópia nova sempre. As duas rodam em paralelo. Use para ações curtas e independentes.

Ignorar se já estiver rodando: descarta o novo disparo se já houver uma cópia ativa. Use para loops de monitoramento, onde uma instância já está cuidando da situação.

Reiniciar (cancela o anterior): cancela a cópia antiga e começa uma nova com os dados atualizados. Use quando a nova informação invalida o que estava sendo feito, como timers que o servidor atualiza periodicamente.

Exemplo com Reiniciar — script da Quest Elektron:

Cada nova mensagem de timer cancela a espera anterior e recomeça com o tempo correto. Quando o servidor mandar 0 minutos e 0 segundos, a espera é zero e executa imediatamente.

---

## 9. Tratamento de erros

Erros no script são exibidos na janela de saída assim:
[Script 'nome_do_trigger'] ERRO: TipoDoErro: mensagem

Protegendo contra timeout:

```
async def script():
    await send("status")
    try:
        res = await waitfor(r"HP: (\d+)/(\d+)", timeout=8)
        setvar("hp", res[0])
    except TimeoutError:
        pass
```

Protegendo contra grupo inexistente:

```
async def script():
    if not grupo(0):
        return
    inimigo = grupo(0)
    await send("atacar " + inimigo)
```

Protegendo contra conversão:

```
async def script():
    try:
        dano = int(grupo(0))
    except (ValueError, IndexError):
        dano = 0
    if dano > 100:
        await send("usar cura emergencial")
```

---

## 10. Exemplos práticos completos

---

### Quest Elektron — timer automático

Padrão: Faltam (?:(\d+) minutos e )?(\d+) segundos para resetar a área elektron
Tipo de busca: Regex
Concorrência: Reiniciar

```
async def script():
    minutos = int(grupo(0)) if grupo(0) else 0
    segundos = int(grupo(1))
    espera = minutos * 60 + segundos
    if espera > 0:
        await wait(espera)
    await send("levantar")
    await send("rrr")
    await send("questelektron")
    await wait(1)
    await send("tres elektron")
```

Como usar: digite tres elektron uma vez manualmente. O script assume o controle e fica em loop automaticamente enquanto você estiver conectado.

Por que Reiniciar: se o servidor mandar atualizações do timer (Faltam 10 minutos, Faltam 5 minutos), cada mensagem reinicia o contador com o tempo mais preciso. Quando chegar em 0, executa imediatamente.

---

### Auto-cura por HP

Padrão: HP:\s*(\d+)/(\d+)
Tipo: Regex
Concorrência: Ignorar

```
async def script():
    hp_atual = int(grupo(0))
    hp_maximo = int(grupo(1))
    setvar("hp", str(hp_atual))
    setvar("hp_max", str(hp_maximo))

    if hp_maximo == 0:
        return

    pct = hp_atual / hp_maximo
    if pct < 0.25:
        await send("usar pocao de vida grande")
    elif pct < 0.50:
        await send("usar pocao de vida")
    elif pct < 0.70:
        await send("rezar")
```

---

### Rotação de combate

Padrão: Você entra em combate com *
Concorrência: Reiniciar

```
async def script():
    inimigo = grupo(0) if grupo(0) else "inimigo"
    setvar("em_combate", "sim")

    ciclos = 0
    while ciclos < 30:
        await send("atacar " + inimigo)
        await wait(1)

        if ciclos % 3 == 0:
            await send("golpe poderoso")
            await wait(1.5)
        else:
            await wait(1.5)

        hp = int(getvar("hp", "100"))
        hp_max = int(getvar("hp_max", "100"))
        if hp_max > 0 and hp / hp_max < 0.3:
            await send("usar pocao de vida")
            await wait(1)

        ciclos += 1

    setvar("em_combate", "nao")
```

---

### Grinder com parada por comando

Padrão para iniciar: iniciar grind
Concorrência: Ignorar

```
async def script():
    await cancelar_outros()
    setvar("grind_ativo", "sim")
    kills = int(getvar("kills", "0"))

    while getvar("grind_ativo") == "sim":
        await send("procurar monstro")
        try:
            res = await waitfor(r"(Você encontra (\w+)|Nenhum monstro)", timeout=10)
            if "Nenhum monstro" in res.linha:
                await wait(5)
                continue

            inimigo = res[1] if len(res) > 1 else "monstro"
            await send("atacar " + inimigo)
            resultado = await waitfor(r"(morreu|fugiu|Você foi morto)", timeout=30)

            if "morreu" in resultado.linha or "fugiu" in resultado.linha:
                kills += 1
                setvar("kills", str(kills))
            elif "Você foi morto" in resultado.linha:
                setvar("grind_ativo", "nao")
                break

        except TimeoutError:
            await wait(3)

    await send("say Grind encerrado. Kills: " + getvar("kills", "0"))
```

Padrão para parar: parar grind

```
setvar("grind_ativo", "nao")
```

---

### Monitoramento de buff

Padrão: O efeito de * desaparece
Concorrência: Nova instância

```
async def script():
    buff = grupo(0) if grupo(0) else ""
    importantes = ["bencao", "protecao", "velocidade"]

    if any(b in buff.lower() for b in importantes):
        await wait(0.5)
        await send("lancar " + buff)
```

---

### Coleta automática com confirmação

Padrão: Você vê * no chão
Concorrência: Nova instância

```
async def script():
    item = grupo(0) if grupo(0) else "item"
    await send("pegar " + item)
    try:
        res = await waitfor(r"(Você pega|Está muito pesado|não existe)", timeout=5)
        if "pesado" in res.linha:
            await send("say Inventário cheio, não consigo pegar " + item)
    except TimeoutError:
        pass
```

---

### Comunicação entre scripts via variáveis

Trigger A — atualiza HP a cada linha de status:
Padrão: HP:\s*(\d+)/(\d+)

```
setvar("hp", grupo(0))
setvar("hp_max", grupo(1))
```

Trigger B — usa o HP guardado para decidir ação:
Padrão: Você está com fome

```
async def script():
    hp = int(getvar("hp", "100"))
    hp_max = int(getvar("hp_max", "100"))
    if hp_max > 0 and hp / hp_max < 0.5:
        await send("comer pao")
        await wait(1)
        await send("beber agua")
```

---

## 11. Scripts em Macros

Macros podem ter um script associado. Quando preenchido, o script substitui os Comandos e passa a controlar toda a execução da macro. O script tem acesso completo às mesmas funções disponíveis nos triggers: send, wait, waitfor, setvar, getvar, cancelar_outros, ativar_grupo, desativar_grupo e re.

A diferença em relação aos triggers é que grupo(i) e linha() retornam string vazia, pois macros não são disparadas por uma linha do servidor.

---

### Como criar uma macro com script

1. Pressione Ctrl+U para abrir o Gerenciador de Macros.
2. Pressione Ctrl+A para adicionar uma nova macro.
3. Preencha o Nome — é o comando que você digitará no MUD para executar a macro.
4. Deixe o campo Comandos vazio ou preencha-o como fallback (o script tem prioridade).
5. No campo Script, escreva o código. Você pode usar qualquer um dos três modos de escrita.
6. Em Concorrência do Script, escolha o comportamento quando a macro for acionada enquanto já estiver rodando.
7. Confirme com OK.

---

### Os três modos de escrita também se aplicam

Modo simples:

```
preparar
wait 1
atacar goblin
wait 2
curar
```

Modo Python direto:

```
await send("preparar")
await wait(1)
await send("atacar")
```

Modo completo:

```
async def script():
    for i in range(3):
        await send("atacar")
        await wait(1.5)
    await send("descansar")
```

---

### Interligação com triggers via variáveis

Scripts de macros e scripts de triggers compartilham as mesmas variáveis globais via setvar e getvar.

Exemplo — macro "combate" define o modo:

```
async def script():
    setvar("modo", "combate")
    await send("atacar goblin")
    await wait(1)
    await send("golpe especial")
    setvar("modo", "idle")
```

Trigger "morreu" (padrão: Você morreu):

```
if getvar("modo") == "combate":
    await send("ressuscitar")
    setvar("modo", "idle")
```

---

### Exemplo — rotina com resposta do servidor

```
async def script():
    await send("status")
    try:
        res = await waitfor(r"HP:\s*(\d+)/(\d+)", timeout=5)
        hp = int(res[0])
        hp_max = int(res[1])
        if hp_max > 0 and hp / hp_max < 0.5:
            await send("usar pocao de vida")
            await wait(1)
    except TimeoutError:
        pass
    await send("atacar")
```

---

### Chamando macros de dentro de scripts

Qualquer macro existente pode ser chamada a partir de um script de trigger ou de outra macro via send. A macro é expandida normalmente, incluindo os delays configurados nela se não tiver script, ou disparando seu script se tiver.

```
async def script():
    for i in range(5):
        await send("rotacao_basica")
        await wait(2)
```

---

### Diferença entre macro com comandos e macro com script

Macro com comandos: sequência fixa de comandos com delay uniforme, zero Python, simples de criar.

Macro com script: lógica, condicionais, loops, espera por resposta do servidor, lê e escreve variáveis compartilhadas com triggers. Mesma potência dos scripts de triggers, acionada manualmente pelo nome da macro.

---

## 12. O que funciona muito bem

Modo simples (linhas de comandos + wait N): zero conhecimento de Python necessário, funciona imediatamente.

Timers longos com wait: o sistema suporta esperas de até 2 horas sem problema. Um script aguardando 30 minutos não afeta nada do cliente.

Múltiplos scripts simultâneos: até 30 scripts rodando em paralelo. Cada um é independente, sem bloquear os outros.

Comunicação via setvar e getvar: permite que triggers independentes compartilhem estado de forma simples e eficiente.

Integração com macros: send passa automaticamente pelo sistema de macros do cliente.

Captura de dados com waitfor: funciona bem para diálogos simples com o servidor, como verificar HP, inventário, ou aguardar confirmação de ação.

Grupos de triggers: ativar e desativar grupos inteiros programaticamente funciona instantaneamente.

Concorrência Reiniciar para timers: ideal para servidores que mandam atualizações periódicas do mesmo timer.

---

## 13. O que não funciona ou tem limitações

### Scripts com wait maior que 2 horas

O tempo máximo de execução de um script é 2 horas (7200 segundos). Scripts que precisem esperar mais que isso são cancelados. Se o seu jogo tem timers maiores, a solução é encadear: ao final do script, envie o comando que gera a próxima mensagem de timer, reiniciando o ciclo.

### waitfor com padrões muito genéricos

Se o padrão do waitfor for muito abrangente, pode fazer match com uma linha errada antes da linha esperada. Use padrões regex específicos.

### Desconexão durante espera

Se o cliente desconectar enquanto um script estiver no meio de um wait, o script é cancelado. Ao reconectar, é necessário acionar novamente a trigger manualmente ou aguardar a próxima mensagem automática do servidor.

### Scripts não persistem entre sessões

Variáveis guardadas com setvar são perdidas ao fechar o cliente ou desconectar. Não há persistência em disco.

### Sintaxe Python obrigatória para modo 2 e 3

O await e a indentação são obrigatórios porque o motor usa Python internamente. Não há como eliminar isso sem criar uma linguagem própria.

### Sem acesso à interface gráfica

Scripts não conseguem ler o conteúdo da janela de saída diretamente, nem interagir com menus ou diálogos. A única forma de reagir à saída do servidor é via triggers e waitfor.

### waitfor não funciona com linhas ignoradas pelo histórico

Se uma trigger estiver configurada com Não mostrar mensagem no histórico principal e a linha for interceptada antes de chegar ao waitfor, o script pode não receber a linha esperada. Evite essa combinação.

### Sem módulos externos

Não é possível usar import dentro de scripts. Operações de arquivo, rede ou qualquer biblioteca externa não estão disponíveis.

---

## 14. Limitações de segurança

Para proteger o cliente, estes recursos Python não estão disponíveis:

import — impede acesso ao sistema de arquivos e rede
open() — acesso direto a arquivos não é permitido
eval() e exec() — prevenção de execução arbitrária
os, sys, subprocess — acesso ao sistema operacional
Atributos com __ no início e no fim — previne manipulação do interpretador
globals(), locals(), vars() — isolamento do namespace

Tentar usar qualquer um desses resulta em erro exibido na saída.

Limite de concorrência: máximo 30 scripts simultâneos. Novos disparos são ignorados quando o limite é atingido.

Limite de tempo: máximo 2 horas por script.

---

## 15. Referência rápida

```
await send("comando")          envia comando ao MUD (suporta macros e #N)
await wait(segundos)           pausa não bloqueante
await waitfor(regex, timeout)  aguarda linha do MUD, retorna MatchResult
await cancelar_outros()        cancela instâncias paralelas deste script
grupo(0), grupo(1)             capturas do padrão da trigger
linha()                        linha completa que disparou a trigger
setvar("chave", "valor")       guarda variável global persistente
getvar("chave", "padrao")      lê variável global com valor padrão seguro
ativar_grupo("nome")           ativa todos os triggers do grupo
desativar_grupo("nome")        desativa todos os triggers do grupo
re.search(r"...", texto)       expressão regular manual
```

Palavras especiais no modo simples:

```
wait N          pausa de N segundos
# comentário   linha ignorada
cmd1; cmd2      dois comandos em sequência
```
