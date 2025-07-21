# fault_injector_tui.py

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, ListView, ListItem, Label
from textual.containers import Horizontal, Vertical
from textual.binding import Binding

# --- Data for the fault experiments ---
# This dictionary holds the content for each fault type.
# It's easy to add new faults here without changing the UI code.
FAULT_EXPERIMENTS = {
    "Pod Faults": {
        "description": "Simulates Pod-level failures like kills, failures, and container-specific issues.",
        "yaml": """```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: pod-failure-example
  namespace: chaos-mesh
spec:
  action: pod-failure
  mode: one
  duration: '30s'
  selector:
    labelSelectors:
      'app.kubernetes.io/component': 'tikv'
```""",
    },
    "Network Faults": {
        "description": "Simulates network issues such as latency, packet loss, or partitions.",
        "yaml": """```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: delay-example
spec:
  action: delay
  mode: one
  selector:
    namespaces:
      - default
    labelSelectors:
      'app': 'web-show'
  delay:
    latency: '10ms'
    correlation: '100'
    jitter: '0ms'
```""",
    },
    "Stress Scenarios": {
        "description": "Simulates CPU or Memory stress on selected pods.",
        "yaml": """```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: StressChaos
metadata:
  name: cpu-stress-example
spec:
  mode: one
  selector:
    namespaces:
      - default
    labelSelectors:
      'app': 'cpu-burner'
  stressors:
    cpu:
      workers: 2
      load: 80
```""",
    },
}


class FaultInjectorApp(App):
    """A Textual TUI for injecting chaos engineering faults."""

    CSS_PATH = "fault_injector.tcss"  # Link to the CSS file for styling

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("h", "toggle_help", "Help"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(name="Fault_Injector")

        # Main layout is a horizontal split
        with Horizontal():
            # Left pane: A selectable list of fault types
            with Vertical(id="options-pane"):
                yield Label("Select Experiment")
                yield ListView(
                    *[ListItem(Label(name)) for name in FAULT_EXPERIMENTS.keys()],
                    id="options-list"
                )

            # Right pane: A container for the description and code preview
            with Vertical(id="preview-pane"):
                yield Static("Description will appear here.", id="description")
                # Using Static with renderable Markdown for syntax highlighting
                yield Static(id="code-preview")

        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is first mounted."""
        # Focus the list view and highlight the first item to show initial content
        self.query_one(ListView).focus()
        self.query_one(ListView).index = 0

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Called when a user highlights an item in the ListView."""
        # Get the friendly name from the highlighted list item
        fault_name = event.item.query_one(Label).renderable

        # Retrieve the data for this fault from our dictionary
        experiment_data = FAULT_EXPERIMENTS.get(str(fault_name))

        if experiment_data:
            # Get the description and code preview widgets by their ID
            description_widget = self.query_one("#description", Static)
            code_widget = self.query_one("#code-preview", Static)

            # Update the content of the widgets
            description_widget.update(experiment_data["description"])
            code_widget.update(experiment_data["yaml"])

    def action_toggle_help(self) -> None:
        """An action to show a simple help message (can be expanded later)."""
        # For now, just a basic notification. This can be a modal screen later.
        self.notify("Use arrow keys to navigate. 'q' to quit.")


if __name__ == "__main__":
    app = FaultInjectorApp()
    app.run()