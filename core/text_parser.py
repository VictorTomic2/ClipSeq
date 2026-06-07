"""
core/text_parser.py

Parseia texto bruto copiado de planilhas (Excel, Google Sheets, CSV)
em TabelaDados ou BlocoRegistro, detectando separadores automaticamente.

Suporta:
    - TSV (Tab Separated Values) — formato padrão do Excel ao copiar células
    - CSV com vírgula ou ponto-e-vírgula
    - Texto simples (uma linha por campo)
    - Tabelas completas (cabeçalho + N linhas de dados)
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from core.data_model import BlocoRegistro, ItemBloco, TabelaDados


# ──────────────────────────────────────────────
# Detecção de separador
# ──────────────────────────────────────────────

def detectar_separador(texto: str) -> str:
    """
    Analisa a primeira linha do texto e retorna o separador mais provável.
    Prioridade: Tab > ';' > ','
    """
    primeira_linha = texto.split('\n')[0] if '\n' in texto else texto
    tabs = primeira_linha.count('\t')
    semicolons = primeira_linha.count(';')
    commas = primeira_linha.count(',')

    if tabs > 0 and tabs >= max(semicolons, commas):
        return '\t'
    if semicolons > 0 and semicolons >= commas:
        return ';'
    if commas > 0:
        return ','
    # Fallback: sem separador detectado → texto simples (uma linha por campo)
    return '\n'


# ──────────────────────────────────────────────
# Parser de linha individual
# ──────────────────────────────────────────────

def _parse_linha_tsv(linha: str) -> List[str]:
    """Split por tab, remove \\r residual do Windows."""
    return [c.rstrip('\r') for c in linha.split('\t')]


def _parse_linha_csv(linha: str, sep: str) -> List[str]:
    """
    Split respeitando aspas duplas (RFC 4180 simplificado).
    Ex: 'João,"Rua A, 123",SP' → ['João', 'Rua A, 123', 'SP']
    """
    campos: List[str] = []
    atual: List[str] = []
    dentro_aspas = False

    for ch in linha.rstrip('\r'):
        if ch == '"':
            dentro_aspas = not dentro_aspas
        elif ch == sep and not dentro_aspas:
            campos.append(''.join(atual))
            atual = []
        else:
            atual.append(ch)

    campos.append(''.join(atual))
    return campos


def _parse_linha(linha: str, sep: str) -> List[str]:
    if sep == '\t':
        return _parse_linha_tsv(linha)
    return _parse_linha_csv(linha, sep)


# ──────────────────────────────────────────────
# Parser principal: tabela
# ──────────────────────────────────────────────

def parse_texto_tabela(
    texto: str,
    tem_cabecalho: bool = True,
    sep: Optional[str] = None,
) -> TabelaDados:
    """
    Converte texto bruto (colado de planilha) em TabelaDados.

    Parâmetros:
        texto         : texto colado diretamente do Excel / Sheets
        tem_cabecalho : se True, primeira linha vira nomes das colunas
        sep           : separador ('\\t', ';', ',') — None = auto-detecção

    Retorna:
        TabelaDados com headers e linhas normalizadas
    """
    texto = texto.strip()
    if not texto:
        return TabelaDados(headers=[], linhas=[])

    sep = sep or detectar_separador(texto)
    linhas_raw = texto.split('\n')

    # Remove linhas completamente vazias
    linhas_raw = [l for l in linhas_raw if l.strip()]
    if not linhas_raw:
        return TabelaDados(headers=[], linhas=[])

    # Se o separador for '\n' (texto simples de uma coluna), trata diferente
    if sep == '\n':
        headers = ['Campo 1'] if not tem_cabecalho else [linhas_raw[0].strip()]
        dados = linhas_raw[1:] if tem_cabecalho else linhas_raw
        linhas = [[v.strip()] for v in dados]
        return TabelaDados(headers=headers, linhas=linhas)

    # Parse de todas as linhas
    linhas_parsed = [_parse_linha(l, sep) for l in linhas_raw]

    # Determina headers
    if tem_cabecalho and linhas_parsed:
        headers = [h.strip() for h in linhas_parsed[0]]
        linhas_dados = linhas_parsed[1:]
    else:
        max_cols = max((len(l) for l in linhas_parsed), default=0)
        headers = [f'Campo {i + 1}' for i in range(max_cols)]
        linhas_dados = linhas_parsed

    if not headers:
        return TabelaDados(headers=[], linhas=[])

    num_cols = len(headers)

    # Normaliza: garante que todas as linhas têm exatamente num_cols colunas
    linhas_normalizadas: List[List[str]] = []
    for linha in linhas_dados:
        # Preenche colunas faltantes com string vazia
        padded = (linha + [''] * num_cols)[:num_cols]
        linhas_normalizadas.append(padded)

    return TabelaDados(headers=headers, linhas=linhas_normalizadas)


# ──────────────────────────────────────────────
# Parser de texto simples (sem separadores)
# ──────────────────────────────────────────────

def parse_texto_simples(
    texto: str,
    labels: Optional[List[str]] = None,
) -> BlocoRegistro:
    """
    Converte texto simples (uma linha por campo) em BlocoRegistro.

    Útil quando o usuário cola dados sem usar a função de importação de tabela.

    Parâmetros:
        texto  : texto com um valor por linha
        labels : nomes dos campos; se None → 'Campo 1', 'Campo 2'…
    """
    linhas = [l for l in texto.strip().split('\n') if l.strip()]
    items: List[ItemBloco] = []

    for i, linha in enumerate(linhas):
        label = labels[i] if labels and i < len(labels) else f'Campo {i + 1}'
        items.append(ItemBloco(label=label, valor_raw=linha.strip()))

    return BlocoRegistro(items)


# ──────────────────────────────────────────────
# Utilidades de pré-visualização
# ──────────────────────────────────────────────

def preview_tabela(tabela: TabelaDados, max_linhas: int = 3) -> str:
    """
    Gera uma string de preview da tabela detectada.
    Útil para exibir no ImportDialog antes de confirmar.
    """
    if not tabela.headers:
        return '(nenhuma coluna detectada)'

    header_str = ' | '.join(tabela.headers)
    linhas_preview = tabela.linhas[:max_linhas]
    rows = [' | '.join(row) for row in linhas_preview]

    total = tabela.total_linhas
    resumo = f'{total} linha(s) de dados'
    if total > max_linhas:
        resumo += f' (mostrando {max_linhas})'

    return '\n'.join([header_str, '-' * len(header_str)] + rows + [resumo])
