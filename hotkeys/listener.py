"""
hotkeys/listener.py

Wrapper em torno de pynput.keyboard.GlobalHotKeys.

Funciona sem privilégios de administrador no Windows
(não usa SetWindowsHookEx de baixo nível; usa a API de mensagens WM_INPUT).
"""
from __future__ import annotations

from typing import Callable, Optional

from pynput import keyboard


class HotkeyListener:
    """
    Escuta um único atalho global e chama `callback` quando acionado.

    Exemplo de hotkey válido: '<ctrl>+<alt>+v'

    O callback é executado na thread interna do pynput.
    Use `root.after(0, fn)` para transferir para a thread do tkinter.
    """

    def __init__(self, hotkey: str, callback: Callable[[], None]):
        self._hotkey = hotkey
        self._callback = callback
        self._listener: Optional[keyboard.GlobalHotKeys] = None

    # ── Ciclo de vida ─────────────────────────

    def iniciar(self) -> None:
        """Inicia (ou reinicia) o listener."""
        self._parar()
        try:
            self._listener = keyboard.GlobalHotKeys(
                {self._hotkey: self._on_activate}
            )
            self._listener.daemon = True
            self._listener.start()
        except Exception as exc:
            print(f'[HotkeyListener] Não foi possível iniciar: {exc}')

    def parar(self) -> None:
        """Para o listener e libera recursos."""
        self._parar()

    def atualizar_hotkey(self, nova_hotkey: str) -> None:
        """Troca o atalho em runtime e reinicia o listener."""
        self._hotkey = nova_hotkey
        self.iniciar()

    # ── Interno ───────────────────────────────

    def _parar(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def _on_activate(self) -> None:
        try:
            self._callback()
        except Exception as exc:
            print(f'[HotkeyListener] Erro no callback: {exc}')
