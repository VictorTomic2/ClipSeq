"""
ClipSeq — Gerenciador de Clipboard Sequencial
Versão 1.0.0

Execução:
    python main.py

Build:
    build.bat
"""
import sys
import os

# Garante que imports e paths de dados funcionem tanto em dev quanto em .exe
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def main() -> None:
    from ui.app_window import AppWindow
    app = AppWindow()
    app.run()


if __name__ == '__main__':
    main()
