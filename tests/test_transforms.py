"""
tests/test_transforms.py

Testes focados nos transforms do catálogo (core/transforms.py)
e na integração com ItemBloco.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from core.data_model import ItemBloco, Transform
from core import transforms as cat


# ══════════════════════════════════════════════
# Catálogo
# ══════════════════════════════════════════════

class TestCatalogo:

    def test_todos_os_tipos_tem_label(self):
        for tipo, meta in cat.CATALOGO.items():
            assert 'label' in meta, f'Tipo {tipo!r} sem label'
            assert meta['label'], f'Tipo {tipo!r} com label vazio'

    def test_todos_os_tipos_tem_descricao(self):
        for tipo, meta in cat.CATALOGO.items():
            assert 'descricao' in meta

    def test_tipos_sem_parametros(self):
        sem_params = cat.tipos_sem_parametros()
        assert 'strip' in sem_params
        assert 'upper' in sem_params
        assert 'regex' not in sem_params

    def test_tipos_com_parametros(self):
        com_params = cat.tipos_com_parametros()
        assert 'regex' in com_params
        assert 'prefix' in com_params
        assert 'suffix' in com_params
        assert 'strip' not in com_params

    def test_label_para_tipo(self):
        assert cat.label_para_tipo('strip') == 'Remover espaços'
        assert cat.label_para_tipo('format_cpf') == 'Formatar CPF'

    def test_label_para_tipo_desconhecido(self):
        assert cat.label_para_tipo('xxx') == 'xxx'  # retorna o próprio tipo

    def test_tipo_para_label_round_trip(self):
        for tipo in cat.CATALOGO:
            label = cat.label_para_tipo(tipo)
            assert cat.tipo_para_label(label) == tipo


# ══════════════════════════════════════════════
# Integração Transform + ItemBloco
# ══════════════════════════════════════════════

class TestTransformIntegracao:

    def test_format_cpf_em_item(self):
        item = ItemBloco('CPF', '12345678900', [Transform('format_cpf')])
        assert item.valor == '123.456.789-00'

    def test_format_phone_celular_em_item(self):
        item = ItemBloco('Tel', '11999990000', [Transform('format_phone')])
        assert item.valor == '(11) 99999-0000'

    def test_pipeline_only_numbers_then_format_cpf(self):
        # CPF digitado com pontos/traços → limpa → formata
        item = ItemBloco('CPF', '123.456.789-00', [
            Transform('only_numbers'),
            Transform('format_cpf'),
        ])
        assert item.valor == '123.456.789-00'

    def test_pipeline_strip_then_title(self):
        item = ItemBloco('Nome', '  JOÃO DA SILVA  ', [
            Transform('strip'),
            Transform('lower'),
            Transform('title'),
        ])
        assert item.valor == 'João Da Silva'

    def test_regex_remove_caracteres_especiais(self):
        item = ItemBloco('RG', '12.345.678-9', [
            Transform('regex', {'pattern': r'[.\-]', 'replacement': ''})
        ])
        assert item.valor == '123456789'

    def test_prefix_ddd_fixo(self):
        item = ItemBloco('Tel', '999990000', [
            Transform('prefix', {'texto': '(11) '})
        ])
        assert item.valor == '(11) 999990000'

    def test_suffix_dominio_email(self):
        item = ItemBloco('Login', 'joao.silva', [
            Transform('suffix', {'texto': '@empresa.com'})
        ])
        assert item.valor == 'joao.silva@empresa.com'

    def test_transforms_nao_alteram_valor_raw(self):
        item = ItemBloco('Nome', 'maria', [Transform('upper')])
        assert item.valor == 'MARIA'
        assert item.valor_raw == 'maria'  # valor_raw nunca muda

    def test_sem_transforms_retorna_valor_limpo(self):
        item = ItemBloco('Campo', '\r\n  texto  \r\n')
        # Strip básico + normaliza newlines são SEMPRE aplicados
        assert item.valor == 'texto'

    def test_lista_transforms_vazia(self):
        item = ItemBloco('Campo', 'valor', [])
        assert item.valor == 'valor'

    def test_serialize_item_com_transforms(self):
        item = ItemBloco('Email', 'ALICE@EX.COM', [Transform('lower')])
        d = item.to_dict()
        assert len(d['transforms']) == 1
        assert d['transforms'][0]['tipo'] == 'lower'

        restored = ItemBloco.from_dict(d)
        assert restored.valor == 'alice@ex.com'


# ══════════════════════════════════════════════
# Casos de borda
# ══════════════════════════════════════════════

class TestCasosDeborda:

    def test_transform_em_string_vazia(self):
        for tipo in ['strip', 'upper', 'lower', 'title', 'only_numbers',
                     'remove_newlines', 'format_cpf', 'format_phone']:
            t = Transform(tipo)
            result = t.aplicar('')
            assert isinstance(result, str), f'Transform {tipo!r} devolveu não-str'

    def test_transform_em_string_com_unicode(self):
        t = Transform('upper')
        assert t.aplicar('são paulo') == 'SÃO PAULO'

    def test_prefix_vazio_nao_altera(self):
        t = Transform('prefix', {'texto': ''})
        assert t.aplicar('valor') == 'valor'

    def test_suffix_vazio_nao_altera(self):
        t = Transform('suffix', {'texto': ''})
        assert t.aplicar('valor') == 'valor'

    def test_regex_sem_match_retorna_original(self):
        t = Transform('regex', {'pattern': r'\d+', 'replacement': 'X'})
        assert t.aplicar('sem números') == 'sem números'

    def test_format_cpf_com_pontuacao_ja_existente(self):
        # Se vier com pontuação, only_numbers primeiro é necessário
        t = Transform('format_cpf')
        # Sem limpeza prévia: não tem 11 dígitos → retorna original
        assert t.aplicar('123.456.789-00') == '123.456.789-00'
