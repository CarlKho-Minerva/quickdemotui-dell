from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Static

class MyTUI(App):
    """A simple TUI app."""

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Static("Welcome to your TUI!")
        yield Button("Press me", id="my_button")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        if event.button.id == "my_button":
            self.query_one(Static).update("You pressed the button!")

if __name__ == "__main__":
    app = MyTUI()
    app.run()