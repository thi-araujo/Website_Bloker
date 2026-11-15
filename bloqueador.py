"""Lógica do Website Bloker: edição segura do arquivo hosts e regras de horário.

Este módulo não depende da interface gráfica, então pode ser testado e
reaproveitado sozinho. Tudo o que o programa escreve no arquivo hosts fica
entre dois marcadores, e só esse bloco é alterado ou removido: as outras
linhas do arquivo nunca são tocadas.
"""

from __future__ import annotations

import ctypes
import json
import os
import platform
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, time
from pathlib import Path

MARCADOR_INICIO = "# >>> Website_Bloker: inicio (nao edite este bloco)"
MARCADOR_FIM = "# <<< Website_Bloker: fim"
REDIRECIONAMENTO = "127.0.0.1"
ARQUIVO_CONFIG = Path.home() / ".website_bloker.json"
NOMES_DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

_REGEX_DOMINIO = re.compile(
    r"^(?=.{1,253}$)(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$"
)


# --------------------------------------------------------------------------
# Arquivo hosts
# --------------------------------------------------------------------------

def caminho_hosts() -> Path:
    """Caminho do arquivo hosts do sistema.

    A variável de ambiente WEBSITE_BLOKER_HOSTS permite apontar para outro
    arquivo (útil para testar sem mexer no hosts de verdade).
    """
    personalizado = os.environ.get("WEBSITE_BLOKER_HOSTS")
    if personalizado:
        return Path(personalizado)
    if platform.system() == "Windows":
        raiz = os.environ.get("SystemRoot", r"C:\Windows")
        return Path(raiz) / "System32" / "drivers" / "etc" / "hosts"
    return Path("/etc/hosts")


def normalizar_site(texto: str) -> str | None:
    """Converte o que o usuário digitou em um domínio limpo.

    Aceita endereços como "https://www.Instagram.com/explore" e devolve
    "instagram.com". Devolve None se o texto não for um domínio válido.
    """
    site = texto.strip().lower()
    site = re.sub(r"^[a-z][a-z0-9+.-]*://", "", site)  # remove http://, https://
    site = re.split(r"[/?#]", site, maxsplit=1)[0]       # remove caminho
    site = site.split("@")[-1].split(":")[0]             # remove usuário e porta
    site = site.strip(".")
    if site.startswith("www."):
        site = site[4:]
    return site if _REGEX_DOMINIO.match(site) else None


def variantes(site: str) -> list[str]:
    """Domínio sem e com "www.", que são endereços diferentes para o hosts."""
    return [site, f"www.{site}"]


def gerar_bloco(sites: list[str]) -> list[str]:
    linhas = [MARCADOR_INICIO]
    for site in sites:
        for nome in variantes(site):
            linhas.append(f"{REDIRECIONAMENTO} {nome}")
    linhas.append(MARCADOR_FIM)
    return linhas


def remover_bloco(linhas: list[str]) -> list[str]:
    """Remove o bloco do Website Bloker e mantém todas as outras linhas."""
    resultado: list[str] = []
    pendentes: list[str] = []
    dentro = False
    for linha in linhas:
        if linha.strip() == MARCADOR_INICIO:
            dentro = True
            pendentes = []
        elif dentro and linha.strip() == MARCADOR_FIM:
            dentro = False
        elif dentro:
            pendentes.append(linha)
        else:
            resultado.append(linha)
    if dentro:
        # Bloco sem marcador de fim (alguém editou o arquivo à mão): remove só
        # as linhas de redirecionamento e devolve o resto.
        resultado += [l for l in pendentes if not l.startswith(REDIRECIONAMENTO + " ")]
    return resultado


def _ler(caminho: Path) -> list[str]:
    texto = caminho.read_text(encoding="utf-8", errors="surrogateescape")
    return texto.splitlines()


def _escrever(caminho: Path, linhas: list[str]) -> None:
    while linhas and not linhas[-1].strip():
        linhas.pop()
    texto = "\n".join(linhas) + "\n"
    caminho.write_text(texto, encoding="utf-8", errors="surrogateescape")


def _fazer_backup(caminho: Path) -> None:
    """Guarda uma cópia do hosts original na primeira vez que ele é alterado."""
    backup = caminho.with_name(caminho.name + ".website_bloker.bak")
    if not backup.exists():
        shutil.copy2(caminho, backup)


def aplicar_bloqueio(sites: list[str], caminho: Path | None = None) -> None:
    caminho = caminho or caminho_hosts()
    _fazer_backup(caminho)
    linhas = remover_bloco(_ler(caminho))
    if sites:
        while linhas and not linhas[-1].strip():
            linhas.pop()
        linhas += ["", *gerar_bloco(sites)]
    _escrever(caminho, linhas)
    limpar_cache_dns()


def remover_bloqueio(caminho: Path | None = None) -> None:
    caminho = caminho or caminho_hosts()
    linhas = _ler(caminho)
    if MARCADOR_INICIO not in (linha.strip() for linha in linhas):
        return
    _escrever(caminho, remover_bloco(linhas))
    limpar_cache_dns()


def bloqueio_ativo(caminho: Path | None = None) -> bool:
    caminho = caminho or caminho_hosts()
    try:
        return any(linha.strip() == MARCADOR_INICIO for linha in _ler(caminho))
    except OSError:
        return False


def sites_bloqueados(caminho: Path | None = None) -> list[str]:
    """Sites que estão hoje no bloco do arquivo hosts."""
    caminho = caminho or caminho_hosts()
    sites: list[str] = []
    dentro = False
    for linha in _ler(caminho):
        if linha.strip() == MARCADOR_INICIO:
            dentro = True
        elif linha.strip() == MARCADOR_FIM:
            dentro = False
        elif dentro:
            partes = linha.split()
            if len(partes) >= 2 and not partes[1].startswith("www."):
                sites.append(partes[1])
    return sites


# --------------------------------------------------------------------------
# Sistema
# --------------------------------------------------------------------------

def tem_permissao(caminho: Path | None = None) -> bool:
    """Indica se o programa consegue alterar o arquivo hosts."""
    caminho = caminho or caminho_hosts()
    if os.environ.get("WEBSITE_BLOKER_HOSTS"):
        return os.access(caminho, os.W_OK)
    if platform.system() == "Windows":
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except (AttributeError, OSError):
            return False
    return os.access(caminho, os.W_OK)


def reiniciar_como_admin() -> bool:
    """No Windows, abre o programa de novo pedindo permissão de administrador."""
    if platform.system() != "Windows":
        return False
    import sys

    script = os.path.abspath(sys.argv[0])
    parametros = " ".join(f'"{arg}"' for arg in [script, *sys.argv[1:]])
    executavel = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(executavel):
        executavel = sys.executable
    resultado = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", executavel, parametros, None, 1
    )
    return resultado > 32


def limpar_cache_dns() -> None:
    """Pede ao sistema para esquecer endereços já resolvidos (melhor esforço)."""
    if os.environ.get("WEBSITE_BLOKER_HOSTS"):
        return
    sistema = platform.system()
    comandos: list[list[str]] = []
    if sistema == "Windows":
        comandos = [["ipconfig", "/flushdns"]]
    elif sistema == "Darwin":
        comandos = [["dscacheutil", "-flushcache"], ["killall", "-HUP", "mDNSResponder"]]
    elif shutil.which("resolvectl"):
        comandos = [["resolvectl", "flush-caches"]]
    opcoes = {}
    if sistema == "Windows":
        opcoes["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    for comando in comandos:
        try:
            subprocess.run(comando, capture_output=True, timeout=10, check=False, **opcoes)
        except (OSError, subprocess.SubprocessError):
            pass


# --------------------------------------------------------------------------
# Horário e configuração
# --------------------------------------------------------------------------

def dentro_do_horario(agora: datetime, inicio: time, fim: time, dias: set[int]) -> bool:
    """Diz se `agora` está dentro do horário de foco.

    `dias` usa a numeração de datetime.weekday() (0 = segunda, 6 = domingo).
    Se o fim for antes do início (ex.: 22:00 às 06:00), o período atravessa a
    meia-noite e o dia considerado é o dia em que ele começou.
    """
    hora = agora.time()
    dia = agora.weekday()
    if inicio == fim:
        return False
    if inicio < fim:
        return dia in dias and inicio <= hora < fim
    if hora >= inicio:
        return dia in dias
    return hora < fim and (dia - 1) % 7 in dias


def texto_para_hora(texto: str) -> time:
    horas, minutos = texto.split(":")
    return time(int(horas), int(minutos))


@dataclass
class Configuracao:
    sites: list[str] = field(default_factory=lambda: [
        "instagram.com", "facebook.com", "tiktok.com", "x.com", "youtube.com",
    ])
    inicio: str = "09:00"
    fim: str = "18:00"
    dias: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    automatico: bool = False

    def em_horario_de_foco(self, agora: datetime | None = None) -> bool:
        return dentro_do_horario(
            agora or datetime.now(),
            texto_para_hora(self.inicio),
            texto_para_hora(self.fim),
            set(self.dias),
        )

    @classmethod
    def carregar(cls, caminho: Path = ARQUIVO_CONFIG) -> "Configuracao":
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
            padrao = cls()
            config = cls(**{k: dados.get(k, getattr(padrao, k)) for k in asdict(padrao)})
            config.sites = [s for s in (normalizar_site(x) for x in config.sites) if s]
            config.dias = sorted({int(d) for d in config.dias if 0 <= int(d) <= 6})
            texto_para_hora(config.inicio)
            texto_para_hora(config.fim)
            return config
        except (OSError, ValueError, TypeError, AttributeError):
            return cls()

    def salvar(self, caminho: Path = ARQUIVO_CONFIG) -> None:
        caminho.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
