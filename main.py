from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static

class MyTUI(App):
    """A simple TUI app."""

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Static("Welcome to your TUI!")
        yield Footer()

if __name__ == "__main__":
    app = MyTUI()
    app.run()