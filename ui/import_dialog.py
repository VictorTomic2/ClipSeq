"""
ui/import_dialog.py

Diálogo de importação de dados.

Permite ao usuário:
  1. Colar texto bruto de planilha (TSV/CSV) ou texto simples
  2. Configurar se a primeira linha é cabeçalho
  3. Escolher separador (auto ou manual)
  4. Visualizar preview das colunas detectadas
  5. Confirmar para carregar na AppWindow
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from core.data_model import BlocoRegistro, TabelaDados
from core.text_parser import detectar_separador, parse_texto_tabela, parse_texto_simples, preview_tabela


class ImportDialog:
    # Paleta de cores (dark)
    BG = '#1a1a2e'
    BG2 = '#16213e'
    BG3 = '#0d1b2a'
    ACCENT = '#4fc3f7'
    TEXT = '#eaeaea'
    TEXT_DIM = '#888888'
    SUCCESS = '#4caf50'
    DANGER = '#e94560'

    def __init__(self, parent: tk.Tk, config: dict):
        self.parent = parent
        self.config = config

        # Resultados possíveis (apenas um será preenchido)
        self.resultado_tabela: Optional[TabelaDados] = None
        self.resultado_bloco: Optional[BlocoRegistro] = None

        self._build()

    def _build(self) -> None:
        self.top = tk.Toplevel(self.parent)
        self.top.title('Importar Dados')
        self.top.geometry('560x560')
        self.top.configure(bg=self.BG)
        self.top.resizable(True, True)
        self.top.grab_set()  # modal
        self.top.transient(self.parent)

        # ── Título ──────────────────────────────
        tk.Label(
            self.top, text='📥  Importar Dados',
            bg=self.BG3, fg=self.TEXT,
            font=('Segoe UI', 12, 'bold'), pady=8
        ).pack(fill='x')

        # ── Opções ──────────────────────────────
        opts_frame = tk.Frame(self.top, bg=self.BG2, pady=6)
        opts_frame.pack(fill='x', padx=8, pady=(6, 0))

        # Checkbox cabeçalho
        self._cabecalho_var = tk.BooleanVar(value=True)
        cb = tk.Checkbutton(
            opts_frame,
            text='Primeira linha é cabeçalho (nomes das colunas)',
            variable=self._cabecalho_var,
            command=self._atualizar_preview,
            bg=self.BG2, fg=self.TEXT,
            selectcolor=self.BG2,
            activebackground=self.BG2,
            activeforeground=self.TEXT,
            font=('Segoe UI', 9), bd=0
        )
        cb.pack(anchor='w', padx=10)

        # Separador
        sep_frame = tk.Frame(opts_frame, bg=self.BG2)
        sep_frame.pack(anchor='w', padx=10, pady=(4, 0))

        tk.Label(sep_frame, text='Separador:', bg=self.BG2, fg=self.TEXT_DIM,
                 font=('Segoe UI', 8)).pack(side='left')

        self._sep_var = tk.StringVar(value='auto')
        for val, txt in [('auto', 'Auto'), ('\t', 'Tab'), (';', 'Ponto e vírgula'), (',', 'Vírgula')]:
            rb = tk.Radiobutton(
                sep_frame, text=txt, variable=self._sep_var, value=val,
                command=self._atualizar_preview,
                bg=self.BG2, fg=self.TEXT_DIM,
                selectcolor=self.BG2,
                activebackground=self.BG2,
                font=('Segoe UI', 8), bd=0
            )
            rb.pack(side='left', padx=(6, 0))

        # ── Área de colagem ──────────────────────
        tk.Label(
            self.top, text='Cole seus dados aqui (Ctrl+V):',
            bg=self.BG, fg=self.TEXT_DIM, font=('Segoe UI', 8), anchor='w'
        ).pack(fill='x', padx=10, pady=(8, 2))

        paste_frame = tk.Frame(self.top, bg=self.BG)
        paste_frame.pack(fill='both', expand=True, padx=8)

        self._text_input = tk.Text(
            paste_frame,
            bg=self.BG2, fg=self.TEXT,
            insertbackground=self.TEXT,
            font=('Consolas', 9),
            relief='flat', bd=0,
            wrap='none',
            height=9,
            selectbackground='#1e4a7a',
        )
        scroll_y = tk.Scrollbar(paste_frame, orient='vertical', command=self._text_input.yview)
        scroll_x = tk.Scrollbar(paste_frame, orient='horizontal', command=self._text_input.xview)
        self._text_input.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self._text_input.grid(row=0, column=0, sticky='nsew')
        scroll_y.grid(row=0, column=1, sticky='ns')
        scroll_x.grid(row=1, column=0, sticky='ew')
        paste_frame.rowconfigure(0, weight=1)
        paste_frame.columnconfigure(0, weight=1)

        # Bind: atualiza preview ao digitar/colar
        self._text_input.bind('<KeyRelease>', lambda e: self._atualizar_preview())
        self._text_input.bind('<<Paste>>', lambda e: self.top.after(50, self._atualizar_preview))

        # ── Preview ──────────────────────────────
        tk.Label(
            self.top, text='Preview:',
            bg=self.BG, fg=self.TEXT_DIM, font=('Segoe UI', 8), anchor='w'
        ).pack(fill='x', padx=10, pady=(6, 2))

        self._preview_lbl = tk.Label(
            self.top,
            text='(aguardando dados…)',
            bg=self.BG2, fg=self.ACCENT,
            font=('Consolas', 8),
            justify='left', anchor='w',
            wraplength=520,
            pady=6, padx=8,
        )
        self._preview_lbl.pack(fill='x', padx=8)

        # ── Botões ───────────────────────────────
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
            btn_frame, text='✔  Confirmar',
            bg=self.SUCCESS, fg='white',
            bd=0, cursor='hand2', padx=14, pady=5,
            activebackground='#388e3c',
            font=('Segoe UI', 9, 'bold'),
            command=self._confirmar
        ).pack(side='right', padx=4)

        # Foco inicial na área de texto
        self._text_input.focus_set()

    # ── Lógica ────────────────────────────────

    def _get_texto(self) -> str:
        return self._text_input.get('1.0', 'end-1c')

    def _get_sep(self) -> Optional[str]:
        v = self._sep_var.get()
        return None if v == 'auto' else v

    def _atualizar_preview(self) -> None:
        texto = self._get_texto()
        if not texto.strip():
            self._preview_lbl.config(text='(aguardando dados…)', fg=self.ACCENT)
            return

        try:
            sep = self._get_sep()
            tem_cab = self._cabecalho_var.get()
            tabela = parse_texto_tabela(texto, tem_cabecalho=tem_cab, sep=sep)

            if tabela.total_linhas == 0 and not tabela.headers:
                # Texto simples (sem separador)
                linhas = [l for l in texto.strip().split('\n') if l.strip()]
                self._preview_lbl.config(
                    text=f'Texto simples: {len(linhas)} campo(s) detectado(s)',
                    fg=self.TEXT_DIM
                )
                return

            preview = preview_tabela(tabela)
            self._preview_lbl.config(text=preview, fg=self.ACCENT)

        except Exception as exc:
            self._preview_lbl.config(text=f'Erro ao parsear: {exc}', fg=self.DANGER)

    def _confirmar(self) -> None:
        texto = self._get_texto().strip()
        if not texto:
            return

        sep = self._get_sep()
        tem_cab = self._cabecalho_var.get()

        # Tenta como tabela primeiro
        tabela = parse_texto_tabela(texto, tem_cabecalho=tem_cab, sep=sep)

        if tabela.total_linhas >= 1 and tabela.headers:
            self.resultado_tabela = tabela
        else:
            # Fallback: texto simples, um campo por linha
            self.resultado_bloco = parse_texto_simples(texto)

        self.top.destroy()
