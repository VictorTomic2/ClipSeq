"""
tests/test_data_model.py

Testes para core/data_model.py:
  - Transform.aplicar()
  - ItemBloco.valor (pipeline de transforms)
  - BlocoRegistro: navegação de ponteiro
  - TabelaDados: acesso e navegação de linhas
  - Serialização round-trip (to_dict / from_dict)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from core.data_model import BlocoRegistro, ItemBloco, TabelaDados, Transform


# ══════════════════════════════════════════════
# Transform.aplicar
# ══════════════════════════════════════════════

class TestTransformAplicar:

    def test_strip_remove_espacos(self):
        t = Transform('strip')
        assert t.aplicar('  olá  ') == 'olá'

    def test_strip_preserva_interior(self):
        t = Transform('strip')
        assert t.aplicar('  João Silva  ') == 'João Silva'

    def test_upper(self):
        assert Transform('upper').aplicar('hello') == 'HELLO'

    def test_lower(self):
        assert Transform('lower').aplicar('HELLO') == 'hello'

    def test_title(self):
        assert Transform('title').aplicar('joão silva') == 'João Silva'

    def test_only_numbers_remove_letras(self):
        assert Transform('only_numbers').aplicar('abc123def456') == '123456'

    def test_only_numbers_cpf_sujo(self):
        assert Transform('only_numbers').aplicar('123.456.789-00') == '12345678900'

    def test_format_cpf_valido(self):
        t = Transform('format_cpf')
        assert t.aplicar('12345678900') == '123.456.789-00'

    def test_format_cpf_invalido_retorna_original(self):
        t = Transform('format_cpf')
        assert t.aplicar('123') == '123'

    def test_format_phone_celular(self):
        t = Transform('format_phone')
        assert t.aplicar('11999990000') == '(11) 99999-0000'

    def test_format_phone_fixo(self):
        t = Transform('format_phone')
        assert t.aplicar('1133334444') == '(11) 3333-4444'

    def test_format_phone_invalido_retorna_original(self):
        t = Transform('format_phone')
        assert t.aplicar('123') == '123'

    def test_remove_newlines(self):
        t = Transform('remove_newlines')
        assert t.aplicar('linha1\nlinha2') == 'linha1 linha2'
        assert t.aplicar('linha1\r\nlinha2') == 'linha1 linha2'

    def test_regex_substituicao_simples(self):
        t = Transform('regex', {'pattern': r'\d+', 'replacement': 'NUM'})
        assert t.aplicar('abc 123 def 456') == 'abc NUM def NUM'

    def test_regex_pattern_vazio_retorna_original(self):
        t = Transform('regex', {'pattern': '', 'replacement': 'x'})
        assert t.aplicar('hello') == 'hello'

    def test_regex_invalida_retorna_original(self):
        t = Transform('regex', {'pattern': '[invalid', 'replacement': 'x'})
        assert t.aplicar('hello') == 'hello'

    def test_prefix(self):
        t = Transform('prefix', {'texto': 'Dr. '})
        assert t.aplicar('João') == 'Dr. João'

    def test_suffix(self):
        t = Transform('suffix', {'texto': ' Jr.'})
        assert t.aplicar('João') == 'João Jr.'

    def test_tipo_desconhecido_retorna_original(self):
        t = Transform('nao_existe')
        assert t.aplicar('hello') == 'hello'


# ══════════════════════════════════════════════
# Transform serialização
# ══════════════════════════════════════════════

class TestTransformSerializacao:

    def test_to_dict(self):
        t = Transform('regex', {'pattern': r'\d+', 'replacement': 'X'})
        d = t.to_dict()
        assert d['tipo'] == 'regex'
        assert d['parametros']['pattern'] == r'\d+'

    def test_from_dict_round_trip(self):
        original = Transform('prefix', {'texto': 'Olá '})
        restored = Transform.from_dict(original.to_dict())
        assert restored.tipo == 'prefix'
        assert restored.parametros['texto'] == 'Olá '
        assert restored.aplicar('mundo') == original.aplicar('mundo')


# ══════════════════════════════════════════════
# ItemBloco
# ══════════════════════════════════════════════

class TestItemBloco:

    def test_valor_basico_strip_automatico(self):
        item = ItemBloco('Nome', '  João  ')
        assert item.valor == 'João'

    def test_valor_remove_newline_automatico(self):
        item = ItemBloco('Campo', 'linha1\nlinha2')
        assert item.valor == 'linha1 linha2'

    def test_valor_com_transform_upper(self):
        item = ItemBloco('Nome', 'joão', [Transform('upper')])
        assert item.valor == 'JOÃO'

    def test_valor_pipeline_multiplos_transforms(self):
        # strip → upper → prefix
        item = ItemBloco('Nome', '  silva  ', [
            Transform('strip'),
            Transform('upper'),
            Transform('prefix', {'texto': 'Sr. '}),
        ])
        assert item.valor == 'Sr. SILVA'

    def test_valor_raw_nao_alterado(self):
        item = ItemBloco('CPF', '  12345678900  ', [Transform('format_cpf')])
        assert item.valor_raw == '  12345678900  '
        assert item.valor == '123.456.789-00'

    def test_serialization_round_trip(self):
        original = ItemBloco('Telefone', '11999990000', [Transform('format_phone')])
        restored = ItemBloco.from_dict(original.to_dict())
        assert restored.label == 'Telefone'
        assert restored.valor == original.valor


# ══════════════════════════════════════════════
# BlocoRegistro — navegação
# ══════════════════════════════════════════════

def _make_bloco(n: int = 3) -> BlocoRegistro:
    items = [ItemBloco(f'Campo{i}', f'valor{i}') for i in range(n)]
    return BlocoRegistro(items)


class TestBlocoRegistroNavegacao:

    def test_obter_item_inicial(self):
        b = _make_bloco(3)
        assert b.obter_item_atual().label == 'Campo0'

    def test_avancar_retorna_true_ate_ultimo(self):
        b = _make_bloco(3)
        assert b.avancar_item() is True   # 0→1
        assert b.avancar_item() is True   # 1→2
        assert b.avancar_item() is True   # 2→3 (finalizado)

    def test_avancar_alem_do_limite_retorna_false(self):
        b = _make_bloco(1)
        b.avancar_item()   # 0→1 (finalizado)
        assert b.avancar_item() is False  # já além do limite

    def test_obter_item_quando_finalizado(self):
        b = _make_bloco(1)
        b.avancar_item()   # finalizado
        assert b.obter_item_atual() is None

    def test_voltar_retorna_false_no_inicio(self):
        b = _make_bloco(3)
        assert b.voltar_item() is False

    def test_voltar_retorna_true_quando_possivel(self):
        b = _make_bloco(3)
        b.avancar_item()
        assert b.voltar_item() is True
        assert b.indice_atual == 0

    def test_ir_para_valido(self):
        b = _make_bloco(3)
        assert b.ir_para(2) is True
        assert b.indice_atual == 2

    def test_ir_para_invalido(self):
        b = _make_bloco(3)
        assert b.ir_para(5) is False
        assert b.indice_atual == 0

    def test_is_no_ultimo_true(self):
        b = _make_bloco(3)
        b.ir_para(2)
        assert b.is_no_ultimo() is True

    def test_is_no_ultimo_false(self):
        b = _make_bloco(3)
        assert b.is_no_ultimo() is False  # está no índice 0, não no último (2)

    def test_is_finalizado_false_inicialmente(self):
        b = _make_bloco(3)
        assert b.is_finalizado() is False

    def test_is_finalizado_true_apos_ultimo(self):
        b = _make_bloco(2)
        b.avancar_item()  # 0→1
        b.avancar_item()  # 1→2 (finalizado)
        assert b.is_finalizado() is True

    def test_resetar(self):
        b = _make_bloco(3)
        b.ir_para(2)
        b.resetar()
        assert b.indice_atual == 0

    def test_len(self):
        b = _make_bloco(5)
        assert len(b) == 5

    def test_serialization_round_trip(self):
        b = _make_bloco(3)
        b.avancar_item()
        b2 = BlocoRegistro.from_dict(b.to_dict())
        assert b2.indice_atual == 1
        assert len(b2) == 3
        assert b2.obter_item_atual().label == 'Campo1'


# ══════════════════════════════════════════════
# TabelaDados
# ══════════════════════════════════════════════

class TestTabelaDados:

    def _make_tabela(self) -> TabelaDados:
        return TabelaDados(
            headers=['Nome', 'Email', 'Tel'],
            linhas=[
                ['Alice', 'alice@ex.com', '11111'],
                ['Bob',   'bob@ex.com',   '22222'],
                ['Carol', 'carol@ex.com', '33333'],
            ]
        )

    def test_get_bloco_atual_retorna_correto(self):
        t = self._make_tabela()
        b = t.get_bloco_atual()
        assert b is not None
        assert b.items[0].valor == 'Alice'
        assert b.items[1].valor == 'alice@ex.com'

    def test_avancar_linha(self):
        t = self._make_tabela()
        assert t.avancar_linha() is True
        b = t.get_bloco_atual()
        assert b.items[0].valor == 'Bob'

    def test_voltar_linha_na_primeira(self):
        t = self._make_tabela()
        assert t.voltar_linha() is False

    def test_ir_para_linha_valida(self):
        t = self._make_tabela()
        assert t.ir_para_linha(2) is True
        b = t.get_bloco_atual()
        assert b.items[0].valor == 'Carol'

    def test_is_ultima_linha(self):
        t = self._make_tabela()
        t.ir_para_linha(2)
        assert t.is_ultima_linha() is True

    def test_total_linhas(self):
        t = self._make_tabela()
        assert t.total_linhas == 3

    def test_get_bloco_aplica_transforms_coluna(self):
        from core.data_model import Transform
        t = self._make_tabela()
        t.transforms_por_coluna[0] = [Transform('upper')]
        b = t.get_bloco_atual()
        assert b.items[0].valor == 'ALICE'

    def test_serialization_round_trip(self):
        t = self._make_tabela()
        t.avancar_linha()
        t2 = TabelaDados.from_dict(t.to_dict())
        assert t2.indice_linha_atual == 1
        assert t2.headers == ['Nome', 'Email', 'Tel']
        assert t2.total_linhas == 3
        b = t2.get_bloco_atual()
        assert b.items[0].valor == 'Bob'
