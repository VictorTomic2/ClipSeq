"""
ui/app_window.py

Janela principal do ClipSeq.

Fluxo de colagem (hotkey):
  1. Listener pynput chama _hotkey_callback() na sua própria thread
  2. O callback avança o ponteiro IMEDIATAMENTE (evita double-paste em tecla rápida)
  3. Copia o valor para o clipboard e simula Ctrl+V (enquanto a janela alvo tem foco)
  4. Agenda a atualização da UI via root.after() na thread principal
"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox
from typing import Optional

from core.clipboard import colar_texto, emitir_beep
from core.data_model import BlocoRegistro, ItemBloco, TabelaDados
from core.persistence import (
    carregar_config, carregar_sessao, limpar_sessao,
    salvar_config, salvar_sessao,
)
from hotkeys.listener import HotkeyListener


# ══════════════════════════════════════════════
# AppWindow
# ══════════════════════════════════════════════

class AppWindow:

    # ── Paleta dark ────────────────────────────
    BG       = '#1a1a2e'
    BG2      = '#16213e'
    BG3      = '#0d1b2a'
    CARD     = '#0f3460'
    ACCENT   = '#4fc3f7'
    TEXT     = '#eaeaea'
    TEXT_DIM = '#888888'
    CURR_BG  = '#0e2a42'
    SUCCESS  = '#4caf50'
    DANGER   = '#e94560'

    # ──────────────────────────────────────────
    def __init__(self) -> None:
        self.config = carregar_config()
        self.tabela:      Optional[TabelaDados]   = None
        self.bloco_atual: Optional[BlocoRegistro] = None

        self._listener: Optional[HotkeyListener] = None
        self._banner_job: Optional[str] = None  # after() ID

        self._setup_window()
        self._setup_ui()
        self._restaurar_sessao()
        self._iniciar_listener()

    # ══ Setup ═════════════════════════════════

    def _setup_window(self) -> None:
        self.root = tk.Tk()
        self.root.title('ClipSeq')
        self.root.geometry('390x540')
        self.root.minsize(340, 420)
        self.root.configure(bg=self.BG)
        self.root.resizable(True, True)

        try:
            self.root.attributes('-topmost', self.config.get('sempre_visivel', False))
        except Exception:
            pass

        self.root.protocol('WM_DELETE_WINDOW', self._on_close)

    def _setup_ui(self) -> None:
        # ── HEADER ──────────────────────────────
        header = tk.Frame(self.root, bg=self.BG3)
        header.pack(fill='x')

        tk.Label(header, text='📋  ClipSeq',
                 bg=self.BG3, fg=self.TEXT,
                 font=('Segoe UI', 12, 'bold'),
                 pady=7).pack(side='left', padx=10)

        # Botões do header (direita)
        hbtn = tk.Frame(header, bg=self.BG3)
        hbtn.pack(side='right', padx=8)

        # Botão PIN (sempre no topo)
        self._pin_var = tk.BooleanVar(value=self.config.get('sempre_visivel', False))
        self._btn_pin = tk.Checkbutton(
            hbtn, text='📌', variable=self._pin_var,
            command=self._toggle_pin,
            bg=self.BG3, fg=self.TEXT_DIM,
            selectcolor=self.BG3,
            activebackground=self.BG3,
            activeforeground=self.TEXT,
            font=('Segoe UI', 12),
            indicatoron=False, relief='flat',
            bd=0, cursor='hand2',
        )
        self._btn_pin.pack(side='left', padx=2)

        tk.Button(hbtn, text='⚙',
                  bg=self.BG3, fg=self.TEXT_DIM,
                  activebackground=self.BG3, activeforeground=self.TEXT,
                  bd=0, cursor='hand2',
                  font=('Segoe UI', 12),
                  command=self._abrir_config).pack(side='left', padx=2)

        # ── BANNER ──────────────────────────────
        self._banner_frame = tk.Frame(self.root, bg=self.DANGER, height=0)
        self._banner_frame.pack(fill='x')
        self._banner_frame.pack_propagate(False)
        self._banner_lbl = tk.Label(self._banner_frame, text='',
                                     bg=self.DANGER, fg='white',
                                     font=('Segoe UI', 8, 'bold'))
        self._banner_lbl.pack(pady=2)

        # ── CONTROLE DE LINHA (tabela) ───────────
        self._row_frame = tk.Frame(self.root, bg=self.BG2, pady=3)
        # (empacotado/desempacotado dinamicamente)

        tk.Label(self._row_frame, text='Registro:',
                 bg=self.BG2, fg=self.TEXT_DIM,
                 font=('Segoe UI', 8)).pack(side='left', padx=(10, 2))

        tk.Button(self._row_frame, text='◀',
                  bg=self.BG2, fg=self.TEXT_DIM,
                  bd=0, cursor='hand2', font=('Segoe UI', 9),
                  activebackground=self.BG2,
                  command=self._linha_anterior).pack(side='left')

        self._row_lbl = tk.Label(self._row_frame, text='0 / 0',
                                  bg=self.BG2, fg=self.ACCENT,
                                  font=('Consolas', 8))
        self._row_lbl.pack(side='left', padx=4)

        tk.Button(self._row_frame, text='▶',
                  bg=self.BG2, fg=self.TEXT_DIM,
                  bd=0, cursor='hand2', font=('Segoe UI', 9),
                  activebackground=self.BG2,
                  command=self._proxima_linha).pack(side='left')

        # ── LISTA DE CAMPOS ──────────────────────
        list_wrap = tk.Frame(self.root, bg=self.BG)
        list_wrap.pack(fill='both', expand=True, padx=6, pady=(4, 0))

        self._canvas = tk.Canvas(list_wrap, bg=self.BG, highlightthickness=0)
        sb = tk.Scrollbar(list_wrap, orient='vertical', command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=sb.set)

        self._canvas.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        self._fields_frame = tk.Frame(self._canvas, bg=self.BG)
        self._cw = self._canvas.create_window((0, 0), window=self._fields_frame, anchor='nw')

        self._fields_frame.bind('<Configure>',
                                 lambda e: self._canvas.configure(scrollregion=self._canvas.bbox('all')))
        self._canvas.bind('<Configure>',
                           lambda e: self._canvas.itemconfig(self._cw, width=e.width))
        self._canvas.bind_all('<MouseWheel>',
                               lambda e: self._canvas.yview_scroll(int(-1 * e.delta / 120), 'units'))

        # ── BOTÃO ADICIONAR CAMPO ────────────────
        add_frame = tk.Frame(self.root, bg=self.BG)
        add_frame.pack(fill='x', padx=8, pady=(2, 0))

        tk.Button(add_frame, text='＋ Adicionar campo',
                  bg=self.BG2, fg=self.TEXT_DIM,
                  bd=0, cursor='hand2',
                  font=('Segoe UI', 8),
                  activebackground=self.BG,
                  command=self._adicionar_campo).pack(side='left')

        # ── NAVEGAÇÃO DE CAMPO ───────────────────
        nav = tk.Frame(self.root, bg=self.BG2, pady=5)
        nav.pack(fill='x', padx=6, pady=(4, 0))

        tk.Button(nav, text='◀ Voltar',
                  bg=self.CARD, fg=self.TEXT,
                  bd=0, cursor='hand2', padx=10,
                  font=('Segoe UI', 9),
                  activebackground=self.BG2,
                  command=self._campo_voltar).pack(side='left', padx=(8, 4))

        self._campo_lbl = tk.Label(nav, text='0 / 0',
                                    bg=self.BG2, fg=self.ACCENT,
                                    font=('Consolas', 9))
        self._campo_lbl.pack(side='left', expand=True)

        tk.Button(nav, text='Avançar ▶',
                  bg=self.CARD, fg=self.TEXT,
                  bd=0, cursor='hand2', padx=10,
                  font=('Segoe UI', 9),
                  activebackground=self.BG2,
                  command=self._campo_avancar).pack(side='right', padx=(4, 8))

        # ── AUTO-AVANÇAR TOGGLE ──────────────────
        tog = tk.Frame(self.root, bg=self.BG)
        tog.pack(fill='x', padx=10)

        self._modo_prog_var = tk.BooleanVar(value=self.config.get('modo_progressivo', True))
        tk.Checkbutton(tog,
                       text='⚡ Auto-avançar após colar (Modo Progressivo)',
                       variable=self._modo_prog_var,
                       command=self._toggle_modo_prog,
                       bg=self.BG, fg=self.TEXT_DIM,
                       selectcolor=self.BG,
                       activebackground=self.BG,
                       activeforeground=self.TEXT,
                       font=('Segoe UI', 8), bd=0).pack(anchor='w')

        # ── RODAPÉ ──────────────────────────────
        footer = tk.Frame(self.root, bg=self.BG3, pady=6)
        footer.pack(fill='x', side='bottom')

        tk.Button(footer, text='📥 Importar',
                  bg=self.CARD, fg=self.TEXT,
                  bd=0, cursor='hand2', padx=12, pady=5,
                  font=('Segoe UI', 9),
                  activebackground=self.BG2,
                  command=self._importar).pack(side='left', padx=(10, 4))

        tk.Button(footer, text='📋 Só Copiar',
                  bg=self.BG2, fg=self.TEXT_DIM,
                  bd=0, cursor='hand2', padx=10, pady=5,
                  font=('Segoe UI', 8),
                  activebackground=self.BG,
                  command=self._so_copiar).pack(side='left', padx=2)

        tk.Button(footer, text='🗑 Limpar',
                  bg='#3a1010', fg='#ff6b6b',
                  bd=0, cursor='hand2', padx=10, pady=5,
                  font=('Segoe UI', 8),
                  activebackground='#5a2020',
                  command=self._limpar).pack(side='right', padx=(4, 10))

        self._hotkey_hint = tk.Label(
            footer, text='',
            bg=self.BG3, fg=self.TEXT_DIM,
            font=('Consolas', 7)
        )
        self._hotkey_hint.pack(side='right', padx=4)
        self._atualizar_hint_hotkey()

    # ══ Renderização de campos ════════════════

    def _renderizar_campos(self) -> None:
        for w in self._fields_frame.winfo_children():
            w.destroy()

        if not self.bloco_atual or len(self.bloco_atual) == 0:
            tk.Label(
                self._fields_frame,
                text='Nenhum dado carregado.\nUse  📥 Importar  para começar.',
                bg=self.BG, fg=self.TEXT_DIM,
                font=('Segoe UI', 9), justify='center'
            ).pack(pady=30)
            self._atualizar_contadores()
            return

        for i, item in enumerate(self.bloco_atual.items):
            self._criar_linha(i, item, is_current=(i == self.bloco_atual.indice_atual))

        self._atualizar_contadores()
        self._scroll_para_atual()

    def _criar_linha(self, idx: int, item: ItemBloco, is_current: bool) -> None:
        bg = self.CURR_BG if is_current else self.BG
        fg_lbl = self.ACCENT if is_current else self.TEXT_DIM
        fg_val = self.TEXT if is_current else '#c0c0c0'
        indicador = '➔' if is_current else '  '

        row = tk.Frame(self._fields_frame, bg=bg, pady=4, cursor='hand2')
        row.pack(fill='x', padx=2, pady=1)

        tk.Label(row, text=indicador, bg=bg, fg=self.ACCENT,
                 font=('Consolas', 10), width=2).pack(side='left', padx=(4, 0))

        tk.Label(row, text=item.label,
                 bg=bg, fg=fg_lbl,
                 font=('Segoe UI', 8), width=13, anchor='w').pack(side='left', padx=(4, 0))

        display = item.valor[:38] + '…' if len(item.valor) > 38 else item.valor
        tk.Label(row, text=display,
                 bg=bg, fg=fg_val,
                 font=('Consolas', 8), anchor='w').pack(side='left', fill='x', expand=True, padx=(4, 0))

        tk.Button(row, text='✏',
                  bg=bg, fg=self.TEXT_DIM,
                  bd=0, cursor='hand2',
                  font=('Segoe UI', 8),
                  activebackground=self.BG2,
                  command=lambda i=idx: self._editar_campo(i)).pack(side='right', padx=4)

        # Clique simples → ir para o campo
        for w in (row,):
            w.bind('<Button-1>', lambda e, i=idx: self._ir_para(i))
            w.bind('<Double-Button-1>', lambda e, i=idx: self._editar_campo(i))

        # Hover
        def _on_enter(e, r=row, cur=is_current):
            r.configure(bg=self.BG2 if not cur else self.CURR_BG)
        def _on_leave(e, r=row, cur=is_current, bg_=bg):
            r.configure(bg=bg_)
        row.bind('<Enter>', _on_enter)
        row.bind('<Leave>', _on_leave)

    def _scroll_para_atual(self) -> None:
        if not self.bloco_atual or len(self.bloco_atual) == 0:
            return
        total = len(self.bloco_atual)
        frac = max(0.0, (self.bloco_atual.indice_atual - 1) / max(total, 1))
        self._canvas.yview_moveto(frac)

    def _atualizar_contadores(self) -> None:
        b = self.bloco_atual
        if b and len(b) > 0:
            idx = min(b.indice_atual + 1, len(b))
            self._campo_lbl.config(text=f'{idx} / {len(b)}')
        else:
            self._campo_lbl.config(text='0 / 0')

        if self.tabela:
            self._row_lbl.config(
                text=f'{self.tabela.indice_linha_atual + 1} / {self.tabela.total_linhas}'
            )
            self._row_frame.pack(fill='x', after=self._banner_frame)
        else:
            self._row_frame.pack_forget()

    # ══ Ações principais ══════════════════════

    def _acao_colar(self) -> None:
        """
        Chamado na thread do listener pynput.
        Avança ponteiro ANTES de colar para evitar double-paste rápido.
        """
        bloco = self.bloco_atual
        if bloco is None:
            return

        item = bloco.obter_item_atual()
        if item is None:
            return  # bloco finalizado — aguarda novo registro

        # Snapshot antes de alterar estado
        era_ultimo = bloco.is_no_ultimo()

        # Avança ponteiro imediatamente (thread-safe para leituras seguintes)
        modo_prog = self.config.get('modo_progressivo', True)
        if modo_prog:
            bloco.avancar_item()

        # Cola: copia clipboard + simula Ctrl+V (enquanto janela alvo tem foco)
        try:
            colar_texto(item.valor, simular=self.config.get('simular_ctrl_v', True))
        except Exception as exc:
            print(f'[ClipSeq] Erro ao colar: {exc}')
            return

        # Agenda UI update na thread principal
        def _ui_update():
            if modo_prog and era_ultimo:
                self._on_fim_registro()
            else:
                self._renderizar_campos()
            self._salvar_sessao()

        self.root.after(0, _ui_update)

    def _so_copiar(self) -> None:
        """Copia o item atual para o clipboard sem avançar e sem Ctrl+V."""
        bloco = self.bloco_atual
        if bloco is None:
            return
        item = bloco.obter_item_atual()
        if item is None:
            return
        import pyperclip
        pyperclip.copy(item.valor)
        self._mostrar_banner('📋 Copiado para clipboard', cor=self.ACCENT, dur=1500)

    def _on_fim_registro(self) -> None:
        """Chamado após colar o último campo de um registro."""
        # Som
        if self.config.get('beep_ativado', True):
            freq = self.config.get('beep_frequencia', 800)
            dur  = self.config.get('beep_duracao_ms', 150)
            threading.Thread(target=emitir_beep, args=(freq, dur), daemon=True).start()

        # Banner (pequeno e discreto)
        if self.config.get('banner_ativado', True):
            self._mostrar_banner('✔ Registro completo!', cor=self.SUCCESS, dur=2000)

        # Auto-avança para próxima linha da tabela (sem perguntar)
        if self.tabela and self.config.get('auto_avancar_linha', True):
            if not self.tabela.is_ultima_linha():
                self.tabela.avancar_linha()
                novo = self.tabela.get_bloco_atual()
                if novo:
                    self.bloco_atual = novo
                    self._renderizar_campos()
                    return
            else:
                # Fim da tabela
                self._mostrar_banner('🏁 Tabela completa!', cor=self.DANGER, dur=3000)

        self._renderizar_campos()

    # ══ Banner ═══════════════════════════════

    def _mostrar_banner(self, msg: str, cor: str = None, dur: int = 2000) -> None:
        if not self.config.get('banner_ativado', True):
            return
        cor = cor or self.DANGER
        self._banner_frame.configure(bg=cor, height=22)
        self._banner_lbl.configure(text=msg, bg=cor)
        if self._banner_job:
            self.root.after_cancel(self._banner_job)
        self._banner_job = self.root.after(dur, self._esconder_banner)

    def _esconder_banner(self) -> None:
        self._banner_frame.configure(height=0)
        self._banner_lbl.configure(text='')

    # ══ Navegação ════════════════════════════

    def _campo_voltar(self) -> None:
        if self.bloco_atual:
            self.bloco_atual.voltar_item()
            self._renderizar_campos()
            self._salvar_sessao()

    def _campo_avancar(self) -> None:
        if self.bloco_atual:
            if not self.bloco_atual.avancar_item():
                self._mostrar_banner('Último campo', dur=900)
            self._renderizar_campos()
            self._salvar_sessao()

    def _ir_para(self, idx: int) -> None:
        if self.bloco_atual:
            self.bloco_atual.ir_para(idx)
            self._renderizar_campos()
            self._salvar_sessao()

    def _proxima_linha(self) -> None:
        if self.tabela and self.tabela.avancar_linha():
            self.bloco_atual = self.tabela.get_bloco_atual()
            self._renderizar_campos()
            self._salvar_sessao()

    def _linha_anterior(self) -> None:
        if self.tabela and self.tabela.voltar_linha():
            self.bloco_atual = self.tabela.get_bloco_atual()
            self._renderizar_campos()
            self._salvar_sessao()

    # ══ Toggles ══════════════════════════════

    def _toggle_pin(self) -> None:
        val = self._pin_var.get()
        try:
            self.root.attributes('-topmost', val)
        except Exception:
            self._pin_var.set(False)
            return
        self.config['sempre_visivel'] = val
        salvar_config(self.config)

    def _toggle_modo_prog(self) -> None:
        self.config['modo_progressivo'] = self._modo_prog_var.get()
        salvar_config(self.config)

    def _atualizar_hint_hotkey(self) -> None:
        hk = self.config.get('hotkey', '<ctrl>+<alt>+v')
        # Converte formato interno para legível: <ctrl>+<alt>+v → Ctrl+Alt+V
        legivel = hk.replace('<ctrl>', 'Ctrl').replace('<alt>', 'Alt') \
                    .replace('<shift>', 'Shift').replace('<', '').replace('>', '')
        self._hotkey_hint.config(text=legivel)

    # ══ Diálogos ═════════════════════════════

    def _importar(self) -> None:
        from ui.import_dialog import ImportDialog
        dlg = ImportDialog(self.root, self.config)
        self.root.wait_window(dlg.top)

        if dlg.resultado_tabela:
            self.tabela = dlg.resultado_tabela
            self.bloco_atual = self.tabela.get_bloco_atual()
        elif dlg.resultado_bloco:
            self.tabela = None
            self.bloco_atual = dlg.resultado_bloco

        self._renderizar_campos()
        self._salvar_sessao()

    def _abrir_config(self) -> None:
        from ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self.root, self.config)
        self.root.wait_window(dlg.top)

        if dlg.config_salvo:
            self.config.update(dlg.config_salvo)
            salvar_config(self.config)
            self._atualizar_hint_hotkey()
            # Reinicia listener com novo atalho
            self._iniciar_listener()
            # Sincroniza toggle
            self._pin_var.set(self.config.get('sempre_visivel', False))
            try:
                self.root.attributes('-topmost', self._pin_var.get())
            except Exception:
                pass

    def _editar_campo(self, idx: int) -> None:
        if self.bloco_atual is None:
            return
        from ui.field_editor_dialog import FieldEditorDialog
        item = self.bloco_atual.items[idx]
        dlg = FieldEditorDialog(
            self.root, item,
            is_from_table=(self.tabela is not None)
        )
        self.root.wait_window(dlg.top)

        if dlg.salvo and dlg.item_editado:
            self.bloco_atual.items[idx] = dlg.item_editado

            # Propaga transforms para toda a coluna (se tabela)
            if self.tabela and dlg.aplicar_a_coluna:
                self.tabela.transforms_por_coluna[idx] = list(dlg.item_editado.transforms)

            self._renderizar_campos()
            self._salvar_sessao()

    def _adicionar_campo(self) -> None:
        if self.bloco_atual is None:
            self.bloco_atual = BlocoRegistro([])

        from ui.field_editor_dialog import FieldEditorDialog
        novo = ItemBloco(label='Novo campo', valor_raw='')
        dlg = FieldEditorDialog(self.root, novo, is_new=True)
        self.root.wait_window(dlg.top)

        if dlg.salvo and dlg.item_editado:
            self.bloco_atual.items.append(dlg.item_editado)
            self._renderizar_campos()
            self._salvar_sessao()

    def _limpar(self) -> None:
        if messagebox.askyesno('Limpar tudo', 'Remover todos os dados carregados?', parent=self.root):
            self.tabela = None
            self.bloco_atual = None
            limpar_sessao()
            self._renderizar_campos()

    # ══ Listener ═════════════════════════════

    def _iniciar_listener(self) -> None:
        if self._listener:
            self._listener.parar()
        hotkey = self.config.get('hotkey', '<ctrl>+<alt>+v')
        self._listener = HotkeyListener(hotkey, self._acao_colar)
        self._listener.iniciar()

    # ══ Sessão ═══════════════════════════════

    def _salvar_sessao(self) -> None:
        avulso = self.bloco_atual if self.tabela is None else None
        salvar_sessao(self.tabela, avulso)

    def _restaurar_sessao(self) -> None:
        tabela, bloco = carregar_sessao()
        if tabela:
            self.tabela = tabela
            self.bloco_atual = tabela.get_bloco_atual()
        elif bloco:
            self.bloco_atual = bloco
        self._renderizar_campos()

    # ══ Lifecycle ════════════════════════════

    def _on_close(self) -> None:
        self._salvar_sessao()
        if self._listener:
            self._listener.parar()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
