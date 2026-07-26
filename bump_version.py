"""Incrementa o numero de BUILD em version.py — chamado pelo build.bat antes de cada
compilacao, pra cada .exe gerado carregar um numero de versao diferente e identificavel."""

import re

with open("version.py", "r", encoding="utf-8") as f:
    content = f.read()

match = re.search(r"BUILD = (\d+)", content)
current = int(match.group(1)) if match else 0
new_build = current + 1
content = re.sub(r"BUILD = \d+", f"BUILD = {new_build}", content)

with open("version.py", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Numero da build atualizado para {new_build}")
