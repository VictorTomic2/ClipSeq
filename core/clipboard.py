"""
core/clipboard.py

Operações de clipboard e simulação de colagem.

DESIGN IMPORTANTE:
    As funções aqui são chamadas na thread do listener pynput
    (enquanto a janela de destino ainda está com foco),
    garantindo que o Ctrl+V simulado vai para o app correto.
"""
from __future__ import annotations

import time

import pyperclip
from pynput.keyboard import Controller, Key

_keyboard = Controller()


def copiar_para_clipboard(texto: str) -> None:
    """Copia texto para o clipboard do sistema via pyperclip."""
    pyperclip.copy(texto)


def simular_colar() -> None:
    """
    Simula Ctrl+V no sistema operacional.

    Deve ser chamado enquanto a janela de DESTINO ainda está em foco.
    Um pequeno sleep antes garante que as teclas do atalho (Ctrl+Alt+V)
    já foram liberadas, evitando conflitos.
    """
    time.sleep(0.1)
    # Solta as teclas modificadoras que o usuário pode estar segurando
    _keyboard.release(Key.alt)
    _keyboard.release(Key.alt_l)
    _keyboard.release(Key.alt_r)
    _keyboard.release(Key.shift)
    _keyboard.release(Key.shift_l)
    _keyboard.release(Key.shift_r)
    _keyboard.release(Key.ctrl)
    _keyboard.release(Key.ctrl_l)
    _keyboard.release(Key.ctrl_r)
    time.sleep(0.05)
    
    _keyboard.press(Key.ctrl)
    _keyboard.press('v')
    _keyboard.release('v')
    _keyboard.release(Key.ctrl)


def colar_texto(texto: str, simular: bool = True) -> None:
    """
    Cola texto no clipboard e, se `simular=True`, dispara Ctrl+V virtual.

    Parâmetros:
        texto   : valor a ser colocado no clipboard
        simular : True  → copia + Ctrl+V (fluxo principal via hotkey)
                  False → apenas copia para clipboard (sem Ctrl+V)
    """
    copiar_para_clipboard(texto)
    if simular:
        simular_colar()


def emitir_beep(frequencia: int = 800, duracao_ms: int = 150) -> None:
    """
    Emite beep discreto usando winsound (nativo Windows, sem instalação).

    Parâmetros:
        frequencia : Hz — intervalo válido: 37–32767
        duracao_ms : milissegundos
    """
    try:
        import winsound
        # Garante limites válidos
        frequencia = max(37, min(32767, frequencia))
        duracao_ms = max(50, min(2000, duracao_ms))
        winsound.Beep(frequencia, duracao_ms)
    except Exception:
        pass  # silencia se winsound não estiver disponível (ex: não-Windows)
