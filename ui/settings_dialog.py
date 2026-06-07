"""
ui/settings_dialog.py

Diálogo de configurações do ClipSeq.

Seções:
  - Atalho de teclado
  - Comportamento (auto-avançar, simular Ctrl+V, auto-avançar linha)
  - Notificações (beep: on/off, frequência, duração — banner: on/off)
  - Janela (sempre no topo)
"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox
from typing import Any, Dict, Optional

from core.clipboard import emitir_beep


class SettingsDialog:

    BG = '#1a1a2e'
    BG2 = '#16213e'
    BG3 = '#0d1b2a'
    ACCENT = '#4fc3f7'
    SUCCESS = '#4caf50'
    DANGER = '#e94560'
    TEXT = '#eaeaea'
    TEXT_DIM = '#888888'
    CARD = '#0f3460'

    def __init__(self, parent: tk.Tk, config: Dict[str, Any]):
        self.parent = parent
        self._config = dict(config)   # cópia de trabalho

        self.config_salvo: Optional[Dict[str, Any]] = None

        self._build()
        self._carregar_valores()

    def _build(self) -> None:
        self.top = tk.Toplevel(self.parent)
        self.top.title('Configurações — ClipSeq')
        self.top.geometry('440x560')
        self.top.configure(bg=self.BG)
        self.top.resizable(False, True)
        self.top.grab_set()
        self.top.transient(self.parent)
        self.top.protocol('WM_DELETE_WINDOW', self._salvar)

        # Título
        tk.Label(
            self.top, text='⚙  Configurações',
            bg=self.BG3, fg=self.TEXT,
            font=('Segoe UI', 11, 'bold'), pady=8
        ).pack(fill='x')

        # Scroll container
        canvas = tk.Canvas(self.top, bg=self.BG, highlightthickness=0)
        sb = tk.Scrollbar(self.top, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        body = tk.Frame(canvas, bg=self.BG)
        win_id = canvas.create_window((0, 0), window=body, anchor='nw')

        def _resize(e):
            canvas.configure(scrollregion=canvas.bbox('all'))
            canvas.itemconfig(win_id, width=e.width)

        body.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', _resize)
        canvas.bind_all('<MouseWheel>', lambda e: canvas.yview_scroll(int(-1 * e.delta / 120), 'units'))

        pad = {'padx': 16, 'pady': 3}

        # ══ SEÇÃO: Atalho ══════════════════════
        self._secao(body, '⌨  Atalho de Teclado')

        hotkey_info = tk.Frame(body, bg=self.BG2, pady=4)
        hotkey_info.pack(fill='x', **{'padx': 16, 'pady': 2})

        tk.Label(
            hotkey_info,
            text='Formato: <ctrl>+<alt>+v  ou  <ctrl>+<shift>+c',
            bg=self.BG2, fg=self.TEXT_DIM, font=('Consolas', 7), anchor='w'
        ).pack(fill='x', padx=6)

        self._hotkey_entry = tk.Entry(
            hotkey_info, bg=self.BG, fg=self.ACCENT,
            insertbackground=self.TEXT,
            font=('Consolas', 10), relief='flat',
        )
        self._hotkey_entry.pack(fill='x', padx=6, pady=4)

        # ══ SEÇÃO: Comportamento ══════════════
        self._secao(body, '⚡  Comportamento')

        self._modo_prog_var = tk.BooleanVar()
        self._simular_var = tk.BooleanVar()
        self._auto_linha_var = tk.BooleanVar()

        self._checkbox(body, 'Auto-avançar campo após colar', self._modo_prog_var, **pad)
        self._checkbox(body, 'Simular Ctrl+V automaticamente', self._simular_var, **pad)
        self._checkbox(
            body,
            'Avançar para próxima linha ao finalizar registro (tabela)',
            self._auto_linha_var, **pad
        )

        # ══ SEÇÃO: Som ═══════════════════════
        self._secao(body, '🔔  Som ao Finalizar Registro')

        self._beep_var = tk.BooleanVar()
        self._checkbox(body, 'Emitir som ao completar um registro', self._beep_var, **pad)

        # Frequência
        freq_frame = tk.Frame(body, bg=self.BG)
        freq_frame.pack(fill='x', **{'padx': 16, 'pady': 2})

        tk.Label(freq_frame, text='Frequência (Hz):', bg=self.BG, fg=self.TEXT_DIM,
                 font=('Segoe UI', 8), width=17, anchor='w').pack(side='left')

        self._freq_var = tk.IntVar(value=800)
        freq_lbl = tk.Label(freq_frame, text='800', bg=self.BG, fg=self.ACCENT,
                             font=('Consolas', 8), width=5)
        freq_lbl.pack(side='right')

        self._freq_scale = tk.Scale(
            freq_frame, from_=200, to=2000, orient='horizontal',
            variable=self._freq_var, resolution=50,
            bg=self.BG, fg=self.TEXT_DIM, troughcolor=self.CARD,
            highlightthickness=0, showvalue=False, length=160,
            command=lambda v: freq_lbl.config(text=str(int(float(v))))
        )
        self._freq_scale.pack(side='left', fill='x', expand=True)

        # Duração
        dur_frame = tk.Frame(body, bg=self.BG)
        dur_frame.pack(fill='x', **{'padx': 16, 'pady': 2})

        tk.Label(dur_frame, text='Duração (ms):', bg=self.BG, fg=self.TEXT_DIM,
                 font=('Segoe UI', 8), width=17, anchor='w').pack(side='left')

        self._dur_var = tk.IntVar(value=150)
        dur_lbl = tk.Label(dur_frame, text='150', bg=self.BG, fg=self.ACCENT,
                            font=('Consolas', 8), width=5)
        dur_lbl.pack(side='right')

        self._dur_scale = tk.Scale(
            dur_frame, from_=50, to=500, orient='horizontal',
            variable=self._dur_var, resolution=25,
            bg=self.BG, fg=self.TEXT_DIM, troughcolor=self.CARD,
            highlightthickness=0, showvalue=False, length=160,
            command=lambda v: dur_lbl.config(text=str(int(float(v))))
        )
        self._dur_scale.pack(side='left', fill='x', expand=True)

        # Botão testar
        tk.Button(
            body, text='▶  Testar som',
            bg=self.CARD, fg=self.TEXT,
            bd=0, cursor='hand2', padx=10, pady=3,
            font=('Segoe UI', 8),
            activebackground=self.BG2,
            command=self._testar_beep
        ).pack(anchor='w', **{'padx': 16, 'pady': 4})

        # ══ SEÇÃO: Banner ═══════════════════
        self._secao(body, '💬  Banner Visual')

        self._banner_var = tk.BooleanVar()
        self._checkbox(
            body,
            'Mostrar banner pequeno ao completar registro',
            self._banner_var, **pad
        )

        # ══ SEÇÃO: Janela ═══════════════════
        self._secao(body, '🪟  Janela')

        self._pin_var = tk.BooleanVar()
        self._checkbox(
            body,
            'Sempre visível (janela no topo)',
            self._pin_var, **pad
        )

        # ── Rodapé (Aviso de Auto-Save) ──────
        btn_frame = tk.Frame(self.top, bg=self.BG3, pady=8)
        btn_frame.pack(fill='x', side='bottom')

        tk.Label(
            btn_frame, text='As alterações são salvas automaticamente ao fechar esta janela.',
            bg=self.BG3, fg=self.TEXT_DIM,
            font=('Segoe UI', 8)
        ).pack(pady=4)

    # ── Helpers ───────────────────────────────

    def _secao(self, parent: tk.Frame, titulo: str) -> None:
        tk.Label(
            parent, text=titulo,
            bg=self.BG, fg=self.ACCENT,
            font=('Segoe UI', 9, 'bold'), anchor='w', pady=4
        ).pack(fill='x', padx=16, pady=(10, 0))
        tk.Frame(parent, bg=self.CARD, height=1).pack(fill='x', padx=16)

    def _checkbox(self, parent: tk.Frame, texto: str, var: tk.BooleanVar, **kwargs) -> None:
        tk.Checkbutton(
            parent, text=texto, variable=var,
            bg=self.BG, fg=self.TEXT,
            selectcolor=self.BG,
            activebackground=self.BG,
            activeforeground=self.TEXT,
            font=('Segoe UI', 9), bd=0
        ).pack(anchor='w', **kwargs)

    # ── Valores iniciais ──────────────────────

    def _carregar_valores(self) -> None:
        c = self._config
        self._hotkey_entry.insert(0, c.get('hotkey', '<ctrl>+<alt>+v'))
        self._modo_prog_var.set(c.get('modo_progressivo', True))
        self._simular_var.set(c.get('simular_ctrl_v', True))
        self._auto_linha_var.set(c.get('auto_avancar_linha', True))
        self._beep_var.set(c.get('beep_ativado', True))
        self._freq_var.set(c.get('beep_frequencia', 800))
        self._dur_var.set(c.get('beep_duracao_ms', 150))
        self._banner_var.set(c.get('banner_ativado', True))
        self._pin_var.set(c.get('sempre_visivel', False))

    # ── Ações ─────────────────────────────────

    def _testar_beep(self) -> None:
        threading.Thread(
            target=emitir_beep,
            args=(self._freq_var.get(), self._dur_var.get()),
            daemon=True
        ).start()

    def _salvar(self) -> None:
        hotkey = self._hotkey_entry.get().strip()
        if not hotkey:
            messagebox.showwarning('Campo obrigatório', 'O atalho não pode estar vazio.', parent=self.top)
            return

        self.config_salvo = {
            'hotkey': hotkey,
            'modo_progressivo': self._modo_prog_var.get(),
            'simular_ctrl_v': self._simular_var.get(),
            'auto_avancar_linha': self._auto_linha_var.get(),
            'beep_ativado': self._beep_var.get(),
            'beep_frequencia': self._freq_var.get(),
            'beep_duracao_ms': self._dur_var.get(),
            'banner_ativado': self._banner_var.get(),
            'sempre_visivel': self._pin_var.get(),
        }
        self.top.destroy()
