"""
core/data_model.py

Modelos de dados do ClipSeq:
  - Transform       : uma transformação aplicada a um valor de campo
  - ItemBloco       : um campo individual (label + valor_raw + lista de transforms)
  - BlocoRegistro   : um registro completo (vários campos) com ponteiro de posição
  - TabelaDados     : vários registros vindos de uma planilha colada
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ──────────────────────────────────────────────
# Transform
# ──────────────────────────────────────────────

class Transform:
    """
    Uma transformação aplicável a um valor de texto.

    Tipos sem parâmetros:
        strip, upper, lower, title, only_numbers,
        format_cpf, format_phone, remove_newlines

    Tipos com parâmetros (passados em `parametros`):
        regex   → {'pattern': str, 'replacement': str}
        prefix  → {'texto': str}
        suffix  → {'texto': str}
    """

    def __init__(self, tipo: str, parametros: Optional[Dict[str, str]] = None):
        self.tipo = tipo
        self.parametros: Dict[str, str] = parametros or {}

    # ── Aplicação ─────────────────────────────

    def aplicar(self, valor: str) -> str:
        t = self.tipo
        p = self.parametros

        if t == 'strip':
            return valor.strip()

        elif t == 'upper':
            return valor.upper()

        elif t == 'lower':
            return valor.lower()

        elif t == 'title':
            return valor.title()

        elif t == 'only_numbers':
            return re.sub(r'\D', '', valor)

        elif t == 'format_cpf':
            nums = re.sub(r'\D', '', valor)
            if len(nums) == 11:
                return f'{nums[:3]}.{nums[3:6]}.{nums[6:9]}-{nums[9:]}'
            return valor  # retorna original se não tiver 11 dígitos

        elif t == 'format_phone':
            nums = re.sub(r'\D', '', valor)
            if len(nums) == 11:          # celular: (XX) XXXXX-XXXX
                return f'({nums[:2]}) {nums[2:7]}-{nums[7:]}'
            elif len(nums) == 10:        # fixo:    (XX) XXXX-XXXX
                return f'({nums[:2]}) {nums[2:6]}-{nums[6:]}'
            return valor

        elif t == 'remove_newlines':
            return valor.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')

        elif t == 'regex':
            pattern = p.get('pattern', '')
            replacement = p.get('replacement', '')
            if pattern:
                try:
                    return re.sub(pattern, replacement, valor)
                except re.error:
                    return valor  # regex inválida: retorna sem alterar
            return valor

        elif t == 'prefix':
            return p.get('texto', '') + valor

        elif t == 'suffix':
            return valor + p.get('texto', '')

        return valor

    # ── Serialização ──────────────────────────

    def to_dict(self) -> dict:
        return {'tipo': self.tipo, 'parametros': self.parametros}

    @classmethod
    def from_dict(cls, d: dict) -> 'Transform':
        return cls(tipo=d['tipo'], parametros=d.get('parametros', {}))

    def __repr__(self) -> str:
        if self.parametros:
            params = ', '.join(f'{k}={v!r}' for k, v in self.parametros.items())
            return f'Transform({self.tipo}, {params})'
        return f'Transform({self.tipo})'


# ──────────────────────────────────────────────
# ItemBloco
# ──────────────────────────────────────────────

class ItemBloco:
    """
    Um campo individual dentro de um BlocoRegistro.

    Exemplos: Nome, E-mail, CPF, RG, Localização…

    O valor exposto (.valor) é sempre o valor_raw após:
      1. limpeza automática (strip + normaliza quebras de linha)
      2. pipeline de transforms definido pelo usuário
    """

    def __init__(
        self,
        label: str,
        valor_raw: str,
        transforms: Optional[List[Transform]] = None,
    ):
        self.label = label
        self.valor_raw = valor_raw
        self.transforms: List[Transform] = transforms or []

    @property
    def valor(self) -> str:
        """Valor processado (strip básico + todas as transforms)."""
        v = self.valor_raw
        # Limpeza básica sempre aplicada
        v = v.strip()
        v = v.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
        # Pipeline de transforms do usuário
        for t in self.transforms:
            v = t.aplicar(v)
        return v

    # ── Serialização ──────────────────────────

    def to_dict(self) -> dict:
        return {
            'label': self.label,
            'valor_raw': self.valor_raw,
            'transforms': [t.to_dict() for t in self.transforms],
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'ItemBloco':
        return cls(
            label=d['label'],
            valor_raw=d['valor_raw'],
            transforms=[Transform.from_dict(t) for t in d.get('transforms', [])],
        )

    def __repr__(self) -> str:
        return f'ItemBloco(label={self.label!r}, valor={self.valor!r})'


# ──────────────────────────────────────────────
# BlocoRegistro
# ──────────────────────────────────────────────

class BlocoRegistro:
    """
    Um registro completo: lista ordenada de ItemBloco com um ponteiro
    (indice_atual) que indica qual campo será colado no próximo paste.

    Ciclo de vida do ponteiro:
        0  →  1  →  …  →  len-1  →  len   (finalizado)
                                      ↑
                              is_finalizado() == True
                              obter_item_atual() == None
    """

    def __init__(self, items: List[ItemBloco]):
        self.items = list(items)
        self.indice_atual: int = 0

    # ── Acesso ────────────────────────────────

    def obter_item_atual(self) -> Optional[ItemBloco]:
        if 0 <= self.indice_atual < len(self.items):
            return self.items[self.indice_atual]
        return None

    # ── Navegação ─────────────────────────────

    def avancar_item(self) -> bool:
        """
        Avança ponteiro em 1. Retorna True se avançou.
        Pode ir até len(items) para indicar 'finalizado'.
        """
        if self.indice_atual <= len(self.items) - 1:
            self.indice_atual += 1
            return True
        return False

    def voltar_item(self) -> bool:
        """Volta ponteiro em 1. Retorna True se voltou."""
        if self.indice_atual > 0:
            self.indice_atual -= 1
            return True
        return False

    def ir_para(self, indice: int) -> bool:
        """Vai para um índice específico. Retorna True se válido."""
        if 0 <= indice < len(self.items):
            self.indice_atual = indice
            return True
        return False

    def resetar(self) -> None:
        self.indice_atual = 0

    # ── Estado ────────────────────────────────

    def is_no_ultimo(self) -> bool:
        """Ponteiro está exatamente no último item (ainda não foi colado)."""
        return len(self.items) > 0 and self.indice_atual == len(self.items) - 1

    def is_finalizado(self) -> bool:
        """Todos os itens já foram colados (ponteiro passou do último)."""
        return self.indice_atual >= len(self.items)

    def __len__(self) -> int:
        return len(self.items)

    # ── Serialização ──────────────────────────

    def to_dict(self) -> dict:
        return {
            'items': [i.to_dict() for i in self.items],
            'indice_atual': self.indice_atual,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'BlocoRegistro':
        bloco = cls([ItemBloco.from_dict(i) for i in d.get('items', [])])
        bloco.indice_atual = d.get('indice_atual', 0)
        return bloco


# ──────────────────────────────────────────────
# TabelaDados
# ──────────────────────────────────────────────

class TabelaDados:
    """
    Representa uma planilha completa colada pelo usuário.

    - headers             : nomes das colunas (detectados da 1ª linha ou gerados)
    - linhas              : lista de listas de strings (dados brutos)
    - indice_linha_atual  : qual linha está sendo usada no momento
    - transforms_por_coluna : transforms que se aplicam a todos os registros
                              de uma determinada coluna (índice → lista de Transform)
    """

    def __init__(self, headers: List[str], linhas: List[List[str]]):
        self.headers: List[str] = headers
        self.linhas: List[List[str]] = linhas
        self.indice_linha_atual: int = 0
        self.transforms_por_coluna: Dict[int, List[Transform]] = {}

    # ── Acesso ────────────────────────────────

    @property
    def total_linhas(self) -> int:
        return len(self.linhas)

    def get_bloco_atual(self) -> Optional[BlocoRegistro]:
        """Constrói um BlocoRegistro para a linha atual."""
        if not (0 <= self.indice_linha_atual < len(self.linhas)):
            return None

        linha = self.linhas[self.indice_linha_atual]
        items: List[ItemBloco] = []
        for col_idx, header in enumerate(self.headers):
            valor = linha[col_idx] if col_idx < len(linha) else ''
            transforms = list(self.transforms_por_coluna.get(col_idx, []))
            items.append(ItemBloco(label=header, valor_raw=valor, transforms=transforms))
        return BlocoRegistro(items)

    # ── Navegação de linhas ───────────────────

    def avancar_linha(self) -> bool:
        if self.indice_linha_atual < len(self.linhas) - 1:
            self.indice_linha_atual += 1
            return True
        return False

    def voltar_linha(self) -> bool:
        if self.indice_linha_atual > 0:
            self.indice_linha_atual -= 1
            return True
        return False

    def ir_para_linha(self, idx: int) -> bool:
        if 0 <= idx < len(self.linhas):
            self.indice_linha_atual = idx
            return True
        return False

    def is_ultima_linha(self) -> bool:
        return self.indice_linha_atual >= len(self.linhas) - 1

    # ── Serialização ──────────────────────────

    def to_dict(self) -> dict:
        return {
            'headers': self.headers,
            'linhas': self.linhas,
            'indice_linha_atual': self.indice_linha_atual,
            'transforms_por_coluna': {
                str(k): [t.to_dict() for t in v]
                for k, v in self.transforms_por_coluna.items()
            },
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'TabelaDados':
        tabela = cls(headers=d.get('headers', []), linhas=d.get('linhas', []))
        tabela.indice_linha_atual = d.get('indice_linha_atual', 0)
        tabela.transforms_por_coluna = {
            int(k): [Transform.from_dict(t) for t in v]
            for k, v in d.get('transforms_por_coluna', {}).items()
        }
        return tabela
