"""
ui/field_editor_dialog.py

Editor de campo individual: permite ao usuário alterar:
  - O nome (label) do campo
  - O valor bruto
  - O pipeline de transforms (adicionar / remover)
  - Opcionalmente: propagar os transforms para toda a coluna da tabela
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Optional

from core.data_model import ItemBloco, Transform
from core import transforms as tr_catalog


class FieldEditorDialog:

    BG = '#1a1a2e'
    BG2 = '#16213e'
    BG3 = '#0d1b2a'
    ACCENT = '#4fc3f7'
    SUCCESS = '#4caf50'
    DANGER = '#e94560'
    TEXT = '#eaeaea'
    TEXT_DIM = '#888888'
    CARD = '#0f3460'

    def __init__(
        self,
        parent: tk.Tk,
        item: ItemBloco,
        is_new: bool = False,
        is_from_table: bool = False,
    ):
        self.parent = parent
        # Trabalha numa cópia para não alterar o original caso cancele
        self._label = item.label
        self._valor_raw = item.valor_raw
        self._transforms = list(item.transforms)
        self.is_new = is_new
        self.is_from_table = is_from_table

        # Resultados
        self.salvo: bool = False
        self.item_editado: Optional[ItemBloco] = None
        self.aplicar_a_coluna: bool = False

        self._build()
        self._atualizar_preview()

    def _build(self) -> None:
        self.top = tk.Toplevel(self.parent)
        self.top.title('Novo campo' if self.is_new else f'Editar: {self._label}')
        self.top.geometry('480x580')
        self.top.configure(bg=self.BG)
        self.top.resizable(True, True)
        self.top.grab_set()
        self.top.transient(self.parent)

        tk.Label(
            self.top,
            text='✏  Editar Campo',
            bg=self.BG3, fg=self.TEXT,
            font=('Segoe UI', 11, 'bold'), pady=7
        ).pack(fill='x')

        body = tk.Frame(self.top, bg=self.BG)
        body.pack(fill='both', expand=True, padx=10, pady=6)

        # ── Nome do campo ────────────────────────
        self._section(body, 'Nome do campo')
        self._label_entry = self._entry(body, self._label)

        # ── Valor bruto ──────────────────────────
        self._section(body, 'Valor bruto (como veio da planilha)')

        raw_frame = tk.Frame(body, bg=self.BG2)
        raw_frame.pack(fill='x')

        self._raw_text = tk.Text(
            raw_frame,
            bg=self.BG2, fg=self.TEXT,
            insertbackground=self.TEXT,
            font=('Consolas', 9),
            relief='flat', height=3,
            wrap='word',
            selectbackground='#1e4a7a',
        )
        self._raw_text.insert('1.0', self._valor_raw)
        self._raw_text.pack(fill='x', padx=4, pady=4)
        self._raw_text.bind('<KeyRelease>', lambda e: self._atualizar_preview())

        # ── Preview processado ────────────────────
        self._section(body, 'Preview (valor que será colado)')

        self._preview_lbl = tk.Label(
            body, text='',
            bg=self.CARD, fg=self.ACCENT,
            font=('Consolas', 9),
            anchor='w', justify='left',
            pady=5, padx=8,
            wraplength=420,
        )
        self._preview_lbl.pack(fill='x')

        # ── Transforms ativos ─────────────────────
        self._section(body, 'Transforms ativos')

        self._tr_list_frame = tk.Frame(body, bg=self.BG2)
        self._tr_list_frame.pack(fill='x')
        self._renderizar_lista_transforms()

        # ── Adicionar transform ───────────────────
        add_frame = tk.Frame(body, bg=self.BG, pady=4)
        add_frame.pack(fill='x')

        tk.Label(add_frame, text='Adicionar:', bg=self.BG, fg=self.TEXT_DIM,
                 font=('Segoe UI', 8)).pack(side='left')

        labels = [tr_catalog.CATALOGO[t]['label'] for t in tr_catalog.CATALOGO]
        self._tr_tipo_var = tk.StringVar(value=labels[0])
        om = tk.OptionMenu(add_frame, self._tr_tipo_var, *labels)
        om.config(bg=self.BG2, fg=self.TEXT, activebackground=self.CARD,
                  highlightthickness=0, font=('Segoe UI', 8), bd=0)
        om['menu'].config(bg=self.BG2, fg=self.TEXT, font=('Segoe UI', 8))
        om.pack(side='left', padx=(4, 0))

        tk.Button(
            add_frame, text='＋',
            bg=self.CARD, fg=self.ACCENT,
            bd=0, cursor='hand2', padx=6,
            font=('Segoe UI', 9),
            activebackground=self.BG2,
            command=self._adicionar_transform
        ).pack(side='left', padx=(4, 0))

        # ── Aplicar a toda a coluna ───────────────
        if self.is_from_table:
            self._col_var = tk.BooleanVar(value=False)
            tk.Checkbutton(
                body,
                text='Aplicar transforms a toda a coluna (todos os registros)',
                variable=self._col_var,
                bg=self.BG, fg=self.TEXT_DIM,
                selectcolor=self.BG,
                activebackground=self.BG,
                font=('Segoe UI', 8), bd=0
            ).pack(anchor='w', pady=(8, 0))

        # ── Botões ────────────────────────────────
        btn_frame = tk.Frame(self.top, bg=self.BG3, pady=8)
        btn_frame.pack(fill='x', side='bottom')

        tk.Button(
            btn_frame, text='Cancelar',
            bg=self.BG2, fg=self.TEXT_DIM,
            bd=0, cursor='hand2', padx=14, pady=5,
            activebackground=self.BG,
            font=('Segoe UI', 9),
            command=self.top.destroy
        ).pack(side='right', padx=(4, 10))

        tk.Button(
            btn_frame, text='✔  Salvar',
            bg=self.SUCCESS, fg='white',
            bd=0, cursor='hand2', padx=14, pady=5,
            activebackground='#388e3c',
            font=('Segoe UI', 9, 'bold'),
            command=self._salvar
        ).pack(side='right', padx=4)

    # ── Helpers de UI ─────────────────────────

    def _section(self, parent: tk.Frame, texto: str) -> None:
        tk.Label(parent, text=texto, bg=self.BG, fg=self.TEXT_DIM,
                 font=('Segoe UI', 7), anchor='w').pack(fill='x', pady=(6, 1))

    def _entry(self, parent: tk.Frame, valor: str) -> tk.Entry:
        e = tk.Entry(
            parent,
            bg=self.BG2, fg=self.TEXT,
            insertbackground=self.TEXT,
            font=('Segoe UI', 9),
            relief='flat',
            selectbackground='#1e4a7a',
        )
        e.insert(0, valor)
        e.pack(fill='x')
        e.bind('<KeyRelease>', lambda ev: self._atualizar_preview())
        return e

    # ── Transforms ────────────────────────────

    def _renderizar_lista_transforms(self) -> None:
        for w in self._tr_list_frame.winfo_children():
            w.destroy()

        if not self._transforms:
            tk.Label(
                self._tr_list_frame,
                text='Nenhum transform adicionado',
                bg=self.BG2, fg=self.TEXT_DIM,
                font=('Segoe UI', 8), pady=4
            ).pack()
            return

        for i, t in enumerate(self._transforms):
            row = tk.Frame(self._tr_list_frame, bg=self.BG2, pady=2)
            row.pack(fill='x', padx=4)

            label = tr_catalog.label_para_tipo(t.tipo)
            params_str = ''
            if t.parametros:
                params_str = '  ' + '  '.join(f'{k}={v!r}' for k, v in t.parametros.items())

            tk.Label(row, text=f'  {i+1}. {label}{params_str}',
                     bg=self.BG2, fg=self.TEXT,
                     font=('Consolas', 8), anchor='w').pack(side='left', fill='x', expand=True)

            tk.Button(
                row, text='🗑',
                bg=self.BG2, fg=self.DANGER,
                bd=0, cursor='hand2',
                font=('Segoe UI', 8),
                activebackground=self.BG,
                command=lambda i=i: self._remover_transform(i)
            ).pack(side='right', padx=2)

    def _adicionar_transform(self) -> None:
        label = self._tr_tipo_var.get()
        tipo = tr_catalog.tipo_para_label(label)
        meta = tr_catalog.CATALOGO.get(tipo, {})
        params_def = meta.get('parametros', {})

        # Se tem parâmetros, abre um mini-diálogo
        if params_def:
            params = self._pedir_parametros(tipo, params_def)
            if params is None:
                return  # usuário cancelou
        else:
            params = {}

        self._transforms.append(Transform(tipo=tipo, parametros=params))
        self._renderizar_lista_transforms()
        self._atualizar_preview()

    def _pedir_parametros(self, tipo: str, defaults: dict) -> Optional[dict]:
        """Mini-diálogo para coletar parâmetros de um transform."""
        dlg = tk.Toplevel(self.top)
        dlg.title(f'Parâmetros — {tr_catalog.label_para_tipo(tipo)}')
        dlg.configure(bg=self.BG)
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.transient(self.top)

        resultado: dict = {}
        entries: dict = {}

        tk.Label(dlg, text='Configure os parâmetros:', bg=self.BG, fg=self.TEXT_DIM,
                 font=('Segoe UI', 8), pady=6, padx=10).pack(anchor='w')

        for key, default in defaults.items():
            frm = tk.Frame(dlg, bg=self.BG)
            frm.pack(fill='x', padx=10, pady=2)

            key_label = key.replace('_', ' ').capitalize()
            tk.Label(frm, text=key_label + ':', bg=self.BG, fg=self.TEXT,
                     font=('Segoe UI', 8), width=12, anchor='w').pack(side='left')

            e = tk.Entry(frm, bg=self.BG2, fg=self.TEXT, insertbackground=self.TEXT,
                         font=('Consolas', 9), relief='flat', width=28)
            e.insert(0, default)
            e.pack(side='left', padx=(4, 0))
            entries[key] = e

        def on_ok():
            for k, widget in entries.items():
                resultado[k] = widget.get()
            dlg.destroy()

        def on_cancel():
            resultado['__cancelled__'] = True
            dlg.destroy()

        btn_row = tk.Frame(dlg, bg=self.BG, pady=8)
        btn_row.pack()
        tk.Button(btn_row, text='OK', bg=self.SUCCESS, fg='white', bd=0, padx=12, pady=4,
                  cursor='hand2', command=on_ok, font=('Segoe UI', 8, 'bold')).pack(side='left', padx=4)
        tk.Button(btn_row, text='Cancelar', bg=self.BG2, fg=self.TEXT_DIM, bd=0, padx=12, pady=4,
                  cursor='hand2', command=on_cancel, font=('Segoe UI', 8)).pack(side='left')

        dlg.wait_window()
        if resultado.get('__cancelled__'):
            return None
        return resultado

    def _remover_transform(self, idx: int) -> None:
        if 0 <= idx < len(self._transforms):
            self._transforms.pop(idx)
            self._renderizar_lista_transforms()
            self._atualizar_preview()

    # ── Preview ───────────────────────────────

    def _atualizar_preview(self) -> None:
        valor_raw = self._raw_text.get('1.0', 'end-1c')
        # Aplica mesmo processamento do ItemBloco.valor
        temp = ItemBloco(
            label=self._label_entry.get(),
            valor_raw=valor_raw,
            transforms=list(self._transforms),
        )
        self._preview_lbl.config(text=temp.valor or '(vazio)')

    # ── Salvar ────────────────────────────────

    def _salvar(self) -> None:
        label = self._label_entry.get().strip()
        if not label:
            messagebox.showwarning('Campo obrigatório', 'O nome do campo não pode estar vazio.', parent=self.top)
            return

        self.item_editado = ItemBloco(
            label=label,
            valor_raw=self._raw_text.get('1.0', 'end-1c'),
            transforms=list(self._transforms),
        )
        self.aplicar_a_coluna = (
            self._col_var.get() if self.is_from_table and hasattr(self, '_col_var') else False
        )
        self.salvo = True
        self.top.destroy()
