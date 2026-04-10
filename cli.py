"""
cli.py
======
Interfaz de línea de comandos para probar el agente localmente.

Comandos especiales:
  reset   — Limpia historial de conversación y sesión del cliente
  trace   — Muestra la traza de herramientas de la sesión actual
  quit / exit / salir — Termina el programa
"""

import sys
from core.agent import create_agent
from core import session_context


def run_cli() -> None:
    print("=" * 60)
    print("  Agente E-commerce — Strata Analytics Challenge")
    print("  Comandos: 'reset', 'trace', 'quit'")
    print("=" * 60)
    print()

    agent = create_agent(streaming=False)
    print("[OK] Agente inicializado correctamente.\n")

    while True:
        try:
            user_input = input("Tú: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n¡Hasta luego!")
            sys.exit(0)

        if not user_input:
            continue

        # Comandos especiales
        if user_input.lower() in ("quit", "exit", "salir", "q"):
            print("¡Hasta luego!")
            sys.exit(0)

        if user_input.lower() == "reset":
            agent.reset_memory()
            print("[Sistema] Sesión reiniciada.\n")
            continue

        if user_input.lower() == "trace":
            trace = session_context.get_tool_trace()
            if not trace:
                print("[Traza] No se han llamado herramientas en esta sesión.\n")
            else:
                print(f"[Traza] {len(trace)} llamada(s) a herramientas:")
                for i, entry in enumerate(trace):
                    print(f"  [{i}] {entry['tool']}")
                    print(f"      Input:  {entry['input']}")
                    output_preview = str(entry['output'])[:100]
                    print(f"      Output: {output_preview}{'...' if len(str(entry['output'])) > 100 else ''}")
                print()
            continue

        # Invocar el agente
        response = agent(user_input)
        print(f"\nAgente: {str(response)}\n")


if __name__ == "__main__":
    run_cli()
