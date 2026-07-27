# Guaxinim Optimizer

Limpador e otimizador de PC para Windows 10/11, com interface gráfica moderna (estilo
Fluent/WinUI3), em português, inglês e espanhol.

## Recursos

- **Dashboard em tempo real** — CPU, RAM, GPU (temperatura, uso, clock, consumo via
  NVIDIA) e espaço livre em disco, atualizando ao vivo.
- **Limpeza de disco** — cache, temporários, prefetch, lixeira, cache de atualizações do
  Windows, componentes do WinSxS, pontos de restauração e mais, com análise de espaço
  antes e depois de limpar.
- **Privacidade e IA** — desativa Copilot, Cortana, telemetria e outros recursos ligados
  a coleta de dados, sem mexer em nada que comprometa a segurança do sistema (Defender,
  UAC e SmartScreen nunca são desativados).
- **Modo Gamer** — tweaks de performance (plano de energia, prioridade de processos,
  MMCSS, precisão do mouse, Nagle, HPET, entre outros), com estado real lido direto do
  Windows e opção de reverter tudo.
- **Inicialização e serviços** — ativa/desativa itens de inicialização e serviços do
  Windows com segurança.
- **Remoção de bloatware** — lista curada de aplicativos pré-instalados dispensáveis.
- **Ferramentas de rede** — flush de DNS, troca de servidor DNS (Cloudflare/Google/Quad9)
  e teste de ping.
- **Buscador de duplicados** — encontra arquivos duplicados por conteúdo (hash), com
  otimização para não travar em pastas grandes.
- **Desinstalador** — remove programas instalados e limpa pastas residuais deixadas
  para trás.
- **Limpeza automática agendada** — roda silenciosamente em segundo plano no Agendador
  de Tarefas do Windows, sem precisar abrir o programa.

## Instalação

Baixe o executável mais recente e rode `GuaxinimOptimizer.exe`. Não requer instalação.
O programa pede elevação de administrador automaticamente, necessária para aplicar a
maioria dos ajustes com segurança.

## Rodando a partir do código-fonte

```bash
pip install psutil pillow
python main.py
```

## Gerando o executável

```bash
build.bat
```

Gera `dist/GuaxinimOptimizer.exe` via PyInstaller (arquivo único, sem console).

## Aviso

Este programa faz alterações reais no sistema (registro do Windows, serviços, arquivos).
Todas as mudanças de configuração podem ser revertidas pela própria interface. Use por
sua conta e risco; recomendamos revisar o que cada opção faz antes de aplicar.
