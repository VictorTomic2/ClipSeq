"""
core/persistence.py

Salva e restaura:
  - config.json  : preferências do usuário (hotkey, beep, etc.)
  - session.json : estado da sessão atual (tabela/bloco + ponteiro)

Tudo salvo na pasta  <raiz do projeto>/data/
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from core.data_model import BlocoRegistro, TabelaDados


# ──────────────────────────────────────────────
# Diretório de dados
# ──────────────────────────────────────────────

def _data_dir() -> Path:
    """
    Retorna (e cria se necessário) a pasta /data relativa ao executável/script.
    """
    base = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    d = base / 'data'
    d.mkdir(parents=True, exist_ok=True)
    return d


# ──────────────────────────────────────────────
# Configurações
# ──────────────────────────────────────────────

_DEFAULTS: Dict[str, Any] = {
    'hotkey': '<ctrl>+<alt>+v',
    'sempre_visivel': False,
    'modo_progressivo': True,
    'simular_ctrl_v': True,
    'auto_avancar_linha': True,
    'beep_ativado': True,
    'beep_frequencia': 800,
    'beep_duracao_ms': 150,
    'banner_ativado': True,
}


def carregar_config() -> Dict[str, Any]:
    """
    Lê config.json. Valores ausentes são preenchidos com os defaults.
    Nunca lança exceção.
    """
    config = dict(_DEFAULTS)
    path = _data_dir() / 'config.json'
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                salvo = json.load(f)
            config.update(salvo)
        except Exception:
            pass
    return config


def salvar_config(config: Dict[str, Any]) -> None:
    path = _data_dir() / 'config.json'
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────
# Sessão
# ──────────────────────────────────────────────

def salvar_sessao(
    tabela: Optional[TabelaDados],
    bloco_avulso: Optional[BlocoRegistro],
) -> None:
    """
    Salva o estado atual da sessão.

    Se `tabela` existir, salva a tabela (inclui o índice da linha atual).
    Caso contrário, salva o bloco avulso (se existir).
    """
    data: Dict[str, Any] = {
        'tabela': tabela.to_dict() if tabela else None,
        'bloco_avulso': bloco_avulso.to_dict() if bloco_avulso else None,
    }
    path = _data_dir() / 'session.json'
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def carregar_sessao() -> Tuple[Optional[TabelaDados], Optional[BlocoRegistro]]:
    """
    Retorna (tabela, bloco_avulso) ou (None, None) se não há sessão salva.
    """
    path = _data_dir() / 'session.json'
    if not path.exists():
        return None, None

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        tabela = (
            TabelaDados.from_dict(data['tabela'])
            if data.get('tabela')
            else None
        )
        bloco = (
            BlocoRegistro.from_dict(data['bloco_avulso'])
            if data.get('bloco_avulso')
            else None
        )
        return tabela, bloco

    except Exception:
        return None, None


def limpar_sessao() -> None:
    path = _data_dir() / 'session.json'
    if path.exists():
        path.unlink()
