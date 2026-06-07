"""
core/transforms.py

Catálogo de transforms predefinidos disponíveis na UI.
Cada entrada mapeia 'tipo' (chave interna) para metadados de exibição.
"""
from __future__ import annotations

from typing import Dict, Any

# ──────────────────────────────────────────────
# Catálogo — usado pela UI para montar menus e forms de parâmetros
# ──────────────────────────────────────────────

CATALOGO: Dict[str, Dict[str, Any]] = {
    'strip': {
        'label': 'Remover espaços',
        'descricao': 'Remove espaços e tabs do início e fim',
        'parametros': {},          # sem parâmetros
    },
    'upper': {
        'label': 'MAIÚSCULAS',
        'descricao': 'Converte todo o texto para maiúsculas',
        'parametros': {},
    },
    'lower': {
        'label': 'minúsculas',
        'descricao': 'Converte todo o texto para minúsculas',
        'parametros': {},
    },
    'title': {
        'label': 'Título',
        'descricao': 'Primeira letra de cada palavra em maiúscula',
        'parametros': {},
    },
    'only_numbers': {
        'label': 'Somente números',
        'descricao': 'Remove tudo que não é dígito (0-9)',
        'parametros': {},
    },
    'format_cpf': {
        'label': 'Formatar CPF',
        'descricao': '11 dígitos → XXX.XXX.XXX-XX',
        'parametros': {},
    },
    'format_phone': {
        'label': 'Formatar Telefone',
        'descricao': '10 ou 11 dígitos → (XX) XXXXX-XXXX',
        'parametros': {},
    },
    'remove_newlines': {
        'label': 'Remover quebras de linha',
        'descricao': 'Substitui \\n por espaço simples',
        'parametros': {},
    },
    'regex': {
        'label': 'Regex personalizado',
        'descricao': 'Substituição via expressão regular (re.sub)',
        'parametros': {          # parametros com valores default para o form
            'pattern': '',
            'replacement': '',
        },
    },
    'prefix': {
        'label': 'Adicionar prefixo',
        'descricao': 'Adiciona texto fixo no início do valor',
        'parametros': {'texto': ''},
    },
    'suffix': {
        'label': 'Adicionar sufixo',
        'descricao': 'Adiciona texto fixo no fim do valor',
        'parametros': {'texto': ''},
    },
}


def tipos_sem_parametros() -> list:
    """Retorna lista de tipos que não precisam de parâmetros adicionais."""
    return [t for t, meta in CATALOGO.items() if not meta['parametros']]


def tipos_com_parametros() -> list:
    """Retorna lista de tipos que exigem parâmetros."""
    return [t for t, meta in CATALOGO.items() if meta['parametros']]


def label_para_tipo(tipo: str) -> str:
    """Converte tipo interno → label legível para a UI."""
    return CATALOGO.get(tipo, {}).get('label', tipo)


def tipo_para_label(label: str) -> str:
    """Converte label da UI → tipo interno."""
    for tipo, meta in CATALOGO.items():
        if meta['label'] == label:
            return tipo
    return label
