"""
tests/test_text_parser.py

Testes para core/text_parser.py:
  - detectar_separador
  - parse_texto_tabela (TSV, CSV, simples, com/sem cabeçalho, múltiplas linhas)
  - parse_texto_simples
  - Normalização de colunas faltantes
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from core.text_parser import (
    detectar_separador,
    parse_texto_tabela,
    parse_texto_simples,
    preview_tabela,
)


# ══════════════════════════════════════════════
# detectar_separador
# ══════════════════════════════════════════════

class TestDetectarSeparador:

    def test_tsv_detecta_tab(self):
        texto = 'Nome\tEmail\tTelefone'
        assert detectar_separador(texto) == '\t'

    def test_csv_ponto_virgula(self):
        texto = 'Nome;Email;Telefone'
        assert detectar_separador(texto) == ';'

    def test_csv_virgula(self):
        texto = 'Nome,Email,Telefone'
        assert detectar_separador(texto) == ','

    def test_tab_tem_prioridade_sobre_outros(self):
        texto = 'A\tB\tC,D'   # 2 tabs, 1 vírgula → tab ganha
        assert detectar_separador(texto) == '\t'

    def test_texto_sem_separador_retorna_newline(self):
        texto = 'João Silva'
        assert detectar_separador(texto) == '\n'


# ══════════════════════════════════════════════
# parse_texto_tabela — TSV
# ══════════════════════════════════════════════

class TestParseTextoTabelaTSV:

    def _tsv(self, *rows):
        """Cria TSV juntando linhas com \\n e campos com \\t."""
        return '\n'.join('\t'.join(str(c) for c in row) for row in rows)

    def test_cabecalho_e_uma_linha(self):
        txt = self._tsv(['Nome', 'Email'], ['Alice', 'alice@ex.com'])
        t = parse_texto_tabela(txt, tem_cabecalho=True)
        assert t.headers == ['Nome', 'Email']
        assert t.total_linhas == 1
        assert t.linhas[0] == ['Alice', 'alice@ex.com']

    def test_multiplas_linhas(self):
        txt = self._tsv(
            ['A', 'B'],
            ['1', '2'],
            ['3', '4'],
            ['5', '6'],
        )
        t = parse_texto_tabela(txt)
        assert t.total_linhas == 3
        assert t.linhas[2] == ['5', '6']

    def test_sem_cabecalho_gera_nomes_automaticos(self):
        txt = self._tsv(['Alice', 'alice@ex.com'])
        t = parse_texto_tabela(txt, tem_cabecalho=False)
        assert t.headers == ['Campo 1', 'Campo 2']
        assert t.total_linhas == 1

    def test_colunas_faltantes_preenchidas_com_vazio(self):
        # Linha 2 tem menos colunas que o cabeçalho
        txt = 'A\tB\tC\n1\t2'
        t = parse_texto_tabela(txt)
        assert t.linhas[0] == ['1', '2', '']

    def test_texto_vazio_retorna_tabela_vazia(self):
        t = parse_texto_tabela('')
        assert t.headers == []
        assert t.total_linhas == 0

    def test_apenas_cabecalho_sem_dados(self):
        t = parse_texto_tabela('Nome\tEmail\n')
        assert t.headers == ['Nome', 'Email']
        assert t.total_linhas == 0

    def test_strip_em_cabecalhos(self):
        txt = ' Nome \t Email \n Alice\talice@ex.com'
        t = parse_texto_tabela(txt)
        assert t.headers == ['Nome', 'Email']

    def test_get_bloco_atual_primeira_linha(self):
        txt = self._tsv(['Col1', 'Col2'], ['v1', 'v2'])
        t = parse_texto_tabela(txt)
        b = t.get_bloco_atual()
        assert b.items[0].label == 'Col1'
        assert b.items[0].valor == 'v1'
        assert b.items[1].label == 'Col2'
        assert b.items[1].valor == 'v2'


# ══════════════════════════════════════════════
# parse_texto_tabela — CSV
# ══════════════════════════════════════════════

class TestParseTextoTabelaCSV:

    def test_csv_virgula(self):
        txt = 'Nome,Email\nAlice,alice@ex.com'
        t = parse_texto_tabela(txt, sep=',')
        assert t.headers == ['Nome', 'Email']
        assert t.linhas[0] == ['Alice', 'alice@ex.com']

    def test_csv_ponto_virgula(self):
        txt = 'Nome;Email\nAlice;alice@ex.com'
        t = parse_texto_tabela(txt, sep=';')
        assert t.headers == ['Nome', 'Email']

    def test_csv_com_aspas(self):
        txt = 'Nome,Endereço\nAlice,"Rua A, 123"'
        t = parse_texto_tabela(txt, sep=',')
        assert t.linhas[0][1] == 'Rua A, 123'

    def test_auto_detecta_csv(self):
        txt = 'A,B\n1,2'
        t = parse_texto_tabela(txt)   # sep=None → auto
        assert t.headers == ['A', 'B']

    def test_auto_detecta_ponto_virgula(self):
        txt = 'A;B\n1;2'
        t = parse_texto_tabela(txt)
        assert t.headers == ['A', 'B']


# ══════════════════════════════════════════════
# parse_texto_simples
# ══════════════════════════════════════════════

class TestParseTextoSimples:

    def test_tres_linhas_sem_labels(self):
        txt = 'Alice\nalice@ex.com\n11999990000'
        b = parse_texto_simples(txt)
        assert len(b) == 3
        assert b.items[0].valor == 'Alice'
        assert b.items[0].label == 'Campo 1'
        assert b.items[1].label == 'Campo 2'

    def test_com_labels_fornecidos(self):
        txt = 'Alice\nalice@ex.com'
        b = parse_texto_simples(txt, labels=['Nome', 'Email'])
        assert b.items[0].label == 'Nome'
        assert b.items[1].label == 'Email'

    def test_labels_insuficientes_completados_automaticamente(self):
        txt = 'Alice\nalice@ex.com\n11999'
        b = parse_texto_simples(txt, labels=['Nome'])
        assert b.items[0].label == 'Nome'
        assert b.items[1].label == 'Campo 2'
        assert b.items[2].label == 'Campo 3'

    def test_linhas_vazias_ignoradas(self):
        txt = 'Alice\n\nalice@ex.com\n'
        b = parse_texto_simples(txt)
        assert len(b) == 2

    def test_strip_em_valores(self):
        txt = '  Alice  \n  alice@ex.com  '
        b = parse_texto_simples(txt)
        assert b.items[0].valor == 'Alice'


# ══════════════════════════════════════════════
# preview_tabela
# ══════════════════════════════════════════════

class TestPreviewTabela:

    def test_preview_com_dados(self):
        txt = 'Nome\tEmail\nAlice\talice@ex.com\nBob\tbob@ex.com'
        t = parse_texto_tabela(txt)
        preview = preview_tabela(t)
        assert 'Nome' in preview
        assert 'Alice' in preview

    def test_preview_tabela_vazia(self):
        from core.data_model import TabelaDados
        t = TabelaDados([], [])
        assert 'nenhuma' in preview_tabela(t).lower()

    def test_preview_respeita_max_linhas(self):
        txt = 'A\n1\n2\n3\n4\n5'
        t = parse_texto_tabela(txt, tem_cabecalho=True)
        preview = preview_tabela(t, max_linhas=2)
        assert '5 linha(s)' in preview
        assert 'mostrando 2' in preview
