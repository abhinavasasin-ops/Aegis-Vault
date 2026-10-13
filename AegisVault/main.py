"""AegisVault entry point."""
from aegisvault.ui.app import AegisApp


def main() -> None:
    app = AegisApp()
    app.mainloop()


if __name__ == "__main__":
    main()
