"""Remocao de apps UWP pre-instalados (bloatware), so para o usuario atual.

Nao mexe em pacotes provisionados (outros usuarios do PC continuam com o app
padrao). Reversivel: da pra reinstalar pela Microsoft Store depois."""

import subprocess

# risk: "safe" (dificilmente alguem usa) ou "cuidado" (algumas pessoas usam bastante)
CURATED_BLOATWARE = [
    dict(id="Microsoft.549981C3F5F10", display="App da Cortana", risk="safe",
          desc="App standalone da Cortana (recurso legado)."),
    dict(id="Microsoft.BingNews", display="Noticias (MSN)", risk="safe",
          desc="App de noticias da Microsoft."),
    dict(id="Microsoft.BingWeather", display="Clima (MSN)", risk="safe",
          desc="App de previsao do tempo da Microsoft."),
    dict(id="Microsoft.MixedReality.Portal", display="Mixed Reality Portal", risk="safe",
          desc="Realidade mista/VR — inutil sem headset compativel."),
    dict(id="Microsoft.Microsoft3DViewer", display="Visualizador 3D", risk="safe",
          desc="Visualizador de modelos 3D, pouco usado."),
    dict(id="Microsoft.SkypeApp", display="Skype", risk="cuidado",
          desc="Cliente Skype pre-instalado. Desative so se nao usa Skype."),
    dict(id="Microsoft.MicrosoftSolitaireCollection", display="Solitaire Collection", risk="safe",
          desc="Colecao de jogos de cartas pre-instalada."),
    dict(id="Microsoft.ZuneMusic", display="Player de Musica (Groove/Media Player app)", risk="cuidado",
          desc="App de musica da Microsoft. Desative se usa outro player."),
    dict(id="Microsoft.ZuneVideo", display="Filmes e TV", risk="cuidado",
          desc="App de video da Microsoft. Desative se usa outro player."),
    dict(id="MicrosoftTeams", display="Teams (consumidor/chat pessoal)", risk="cuidado",
          desc="Versao de chat pessoal do Teams (nao a versao corporativa instalada separadamente)."),
    dict(id="Microsoft.GamingApp", display="App Xbox", risk="cuidado",
          desc="App Xbox para PC (Game Pass, biblioteca Xbox). Desative so se nao joga via Xbox/Game Pass."),
    dict(id="Microsoft.YourPhone", display="Vincular ao Celular (Phone Link)", risk="cuidado",
          desc="Integracao com celular Android/iPhone. Desative se nao usa esse recurso."),
    dict(id="Microsoft.3DBuilder", display="3D Builder", risk="safe",
          desc="App de modelagem/impressao 3D, pouco usado."),
    dict(id="Microsoft.BingFinance", display="Financas (MSN Money)", risk="safe",
          desc="App de cotacoes e financas da Microsoft."),
    dict(id="Microsoft.BingSports", display="Esportes (MSN)", risk="safe",
          desc="App de esportes da Microsoft."),
    dict(id="Microsoft.BingTranslator", display="Tradutor Microsoft", risk="cuidado",
          desc="App de traducao. Desative se usa outro tradutor (ex: navegador)."),
    dict(id="Microsoft.BingFoodAndDrink", display="Comidas e Bebidas (MSN)", risk="safe",
          desc="App de receitas da Microsoft."),
    dict(id="Microsoft.BingHealthAndFitness", display="Saude e Fitness (MSN)", risk="safe",
          desc="App de saude e exercicios da Microsoft."),
    dict(id="Microsoft.BingTravel", display="Viagens (MSN)", risk="safe",
          desc="App de viagens da Microsoft."),
    dict(id="Microsoft.XboxApp", display="Xbox Console Companion (legado)", risk="cuidado",
          desc="Versao antiga do app Xbox. Desative se nao usa Xbox/Game Pass."),
    dict(id="Microsoft.Xbox.TCUI", display="Xbox TCUI (interface social)", risk="cuidado",
          desc="Componentes de interface social do Xbox (convites, chat). Ligado ao app Xbox."),
    dict(id="Microsoft.XboxGamingOverlay", display="Xbox Game Bar", risk="cuidado",
          desc="Overlay de jogos (Win+G). Desative se nao usa gravacao/widgets do Game Bar."),
    dict(id="Microsoft.XboxSpeechToTextOverlay", display="Xbox Speech To Text Overlay", risk="safe",
          desc="Legendas por voz do Game Bar. Raramente usado."),
    dict(id="Microsoft.XboxIdentityProvider", display="Xbox Identity Provider", risk="cuidado",
          desc="Login de conta Xbox usado por jogos e pelo app Xbox."),
    dict(id="Microsoft.WindowsAlarms", display="Alarmes e Relogio", risk="safe",
          desc="App de alarmes, cronometro e relogio mundial."),
    dict(id="Microsoft.WindowsCamera", display="Camera", risk="cuidado",
          desc="App de camera do Windows. Desative so se nao usa a webcam via este app."),
    dict(id="Microsoft.WindowsCommunicationsApps", display="Email e Calendario (Mail/Calendar)", risk="cuidado",
          desc="Apps de email e calendario da Microsoft. Desative se usa Outlook/Gmail web."),
    dict(id="Microsoft.WindowsFeedbackHub", display="Central de Feedback", risk="safe",
          desc="App pra enviar feedback sobre o Windows pra Microsoft."),
    dict(id="Microsoft.WindowsMaps", display="Mapas", risk="safe",
          desc="App de mapas offline/online da Microsoft."),
    dict(id="Microsoft.WindowsSoundRecorder", display="Gravador de Som", risk="safe",
          desc="App simples de gravacao de audio."),
    dict(id="Microsoft.MicrosoftStickyNotes", display="Notas Adesivas (Sticky Notes)", risk="cuidado",
          desc="Post-its digitais. Desative so se nao usa pra anotacoes rapidas."),
    dict(id="Microsoft.MicrosoftOfficeHub", display="Aplicativo do Office (atalho/promocional)", risk="safe",
          desc="Tela promocional do Office, nao e o Office em si (Word/Excel continuam intactos)."),
    dict(id="Microsoft.Office.OneNote", display="OneNote (versao UWP)", risk="cuidado",
          desc="Versao loja do OneNote. Desative so se usa a versao desktop/Office ou nao usa OneNote."),
    dict(id="Microsoft.NetworkSpeedTest", display="Teste de Velocidade de Rede", risk="safe",
          desc="App simples de teste de velocidade de internet."),
    dict(id="Microsoft.PowerBIForWindows", display="Power BI", risk="safe",
          desc="App de dashboards Power BI. So relevante pra quem usa Power BI."),
    dict(id="Microsoft.OneConnect", display="Servicos de Operadora (Paid Wifi & Cellular)", risk="safe",
          desc="Gerencia planos de dados/wifi pago de operadoras. Raramente usado em desktop."),
    dict(id="Microsoft.People", display="Pessoas (Contatos)", risk="safe",
          desc="App de contatos integrado ao Windows."),
    dict(id="Microsoft.Print3D", display="Print 3D", risk="safe",
          desc="App de preparacao de impressao 3D."),
    dict(id="Microsoft.Wallet", display="Carteira (Wallet)", risk="safe",
          desc="App de carteira digital/pagamentos, pouco usado no Brasil."),
    dict(id="Microsoft.Todos", display="Microsoft To Do", risk="cuidado",
          desc="App de lista de tarefas. Desative so se nao usa pra organizar tarefas."),
    dict(id="Microsoft.WhiteboardUpdate", display="Microsoft Whiteboard", risk="safe",
          desc="Quadro branco colaborativo, pouco usado fora de reunioes corporativas."),
    dict(id="Microsoft.PowerAutomateDesktop", display="Power Automate Desktop", risk="cuidado",
          desc="Ferramenta de automacao de tarefas. Desative se nao usa automacoes RPA."),
    dict(id="Microsoft.Getstarted", display="Dicas (Get Started/Tips)", risk="safe",
          desc="App de dicas de uso do Windows para novos usuarios."),
    dict(id="Microsoft.GetHelp", display="Obter Ajuda", risk="safe",
          desc="App de suporte tecnico da Microsoft."),
    dict(id="Microsoft.WindowsReadingList", display="Lista de Leitura", risk="safe",
          desc="App pra salvar paginas/artigos pra ler depois."),
    dict(id="Clipchamp.Clipchamp", display="Clipchamp (editor de video)", risk="cuidado",
          desc="Editor de video simples da Microsoft. Desative se usa outro editor."),
    dict(id="MicrosoftWindows.Client.CoPilot", display="App do Copilot", risk="safe",
          desc="Aplicativo dedicado do Copilot (alem do toggle em Privacidade & IA)."),
]


def _run_ps(script, timeout=30):
    return subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True, text=True, timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW,
    )


def list_installed_appx_names():
    """Uma unica chamada de PowerShell que lista TODOS os pacotes AppX instalados de uma vez
    — usada pelo scan em lote (ver is_installed com installed_names). Abrir um powershell.exe
    novo pra cada um dos ~47 itens curados (isolado, sem essa lista) custa varias centenas de
    ms cada um; em sequencia isso deixava a aba Bloatware parecendo travada por dezenas de
    segundos toda vez que abria."""
    try:
        result = _run_ps("(Get-AppxPackage).Name -join '|'")
        raw = result.stdout.strip()
        return raw.split("|") if raw else []
    except Exception:
        return []


def is_installed(package_id, installed_names=None):
    """Se installed_names for passado (lista ja obtida via list_installed_appx_names), checa
    localmente sem abrir PowerShell nenhum — MUITO mais rapido pra checar varios de uma vez.
    Sem isso, faz uma chamada isolada (ok pra checar so 1 item, ex: depois de um toggle)."""
    if installed_names is not None:
        return any(name.startswith(package_id) for name in installed_names)
    try:
        result = _run_ps(f"(Get-AppxPackage -Name '{package_id}*' | Select-Object -First 1).Name")
        return bool(result.stdout.strip())
    except Exception:
        return False


def remove_package(package_id, log_callback=None):
    try:
        result = _run_ps(
            f"Get-AppxPackage -Name '{package_id}*' | Remove-AppxPackage -ErrorAction Stop",
            timeout=60,
        )
        if result.returncode == 0:
            return True
        if log_callback:
            log_callback(f"  erro ao remover: {result.stderr.strip()[:200]}")
        return False
    except Exception as exc:
        if log_callback:
            log_callback(f"  erro ao remover: {exc}")
        return False


def reinstall_package(package_id, log_callback=None):
    """Tenta trazer o app de volta registrando o pacote da Store para o usuario atual."""
    try:
        result = _run_ps(
            "Get-AppxPackage -AllUsers -Name '{0}*' | "
            "Foreach-Object {{ Add-AppxPackage -DisableDevelopmentMode "
            "-Register \"$($_.InstallLocation)\\AppXManifest.xml\" -ErrorAction Stop }}".format(package_id),
            timeout=60,
        )
        if result.returncode == 0:
            return True
        if log_callback:
            log_callback("  nao foi possivel reinstalar automaticamente — "
                           "reinstale pela Microsoft Store se quiser o app de volta.")
        return False
    except Exception as exc:
        if log_callback:
            log_callback(f"  erro ao tentar reinstalar: {exc}")
        return False
