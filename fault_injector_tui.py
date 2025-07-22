# fault_injector_tui.py (Updated for Screen 2)

from textual.app import App, ComposeResult
from textual.widgets import (
    Header,
    Footer,
    Static,
    ListView,
    ListItem,
    Label,
    Button,
    Input,
)
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual.screen import Screen

# --- Data for the fault experiments ---
# Now includes a list of editable fields for each experiment
FAULT_EXPERIMENTS = {
    "Pod Faults": {
        "description": "Simulates Pod-level failures like kills, failures, and container-specific issues.",
        "kind": "PodChaos",
        "editable_fields": {
            "name": "pod-failure-example",
            "namespace": "chaos-mesh",
            "action": "pod-failure",  # This will be a selectable field
            "duration": "30s",
            "labelSelectors": "'app.kubernetes.io/component': 'tikv'",
        },
        "action_options": ["pod-failure", "pod-kill", "container-kill"],
    },
    "Network Faults": {
        "description": "Simulates network issues such as latency, packet loss, or partitions.",
        "kind": "NetworkChaos",
        "editable_fields": {
            "name": "delay-example",
            "namespace": "default",
            "action": "delay",
            "latency": "10ms",
            "labelSelectors": "'app': 'web-show'",
        },
        "action_options": ["delay", "loss", "duplicate", "corrupt"],
    },
    # Add more experiments here in the same format
}


# Helper function to generate YAML from our data structure
def generate_yaml(kind, fields):
    spec_fields = fields.copy()
    name = spec_fields.pop("name")
    namespace = spec_fields.pop("namespace")

    # Simple YAML generation
    yaml_string = f"""```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: {kind}
metadata:
  name: {name}
  namespace: {namespace}
spec:
"""
    for key, value in spec_fields.items():
        if key == "labelSelectors":
            yaml_string += f"  selector:\n    labelSelectors:\n      {value}"
        elif key in ["latency", "correlation", "jitter"]:  # Indent delay fields
            if "delay:" not in yaml_string:
                yaml_string += "  delay:\n"
            yaml_string += f"    {key}: '{value}'\n"
        else:
            yaml_string += f"  {key}: {value}\n"

    return yaml_string + "\n```"


class ExperimentSelectionScreen(Screen):
    """The first screen where the user selects the type of experiment."""

    def compose(self) -> ComposeResult:
        yield Header(name="Fault_Injector - Select Experiment")
        with Horizontal():
            with Vertical(id="options-pane"):
                yield Label("Select Experiment")
                yield ListView(
                    *[ListItem(Label(name)) for name in FAULT_EXPERIMENTS.keys()],
                    id="options-list",
                )
            with Vertical(id="preview-pane"):
                yield Static("Description will appear here.", id="description")
                yield Static(id="code-preview")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(ListView).focus()
        self.query_one(ListView).index = 0

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        fault_name = event.item.query_one(Label).renderable
        experiment_data = FAULT_EXPERIMENTS.get(str(fault_name))

        if experiment_data:
            self.query_one("#description").update(experiment_data["description"])
            # Generate the YAML for the preview
            yaml_preview = generate_yaml(
                experiment_data["kind"], experiment_data["editable_fields"]
            )
            self.query_one("#code-preview").update(yaml_preview)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """When user presses Enter, switch to the modification screen."""
        fault_name = str(event.item.query_one(Label).renderable)
        self.app.push_screen(ModifyConfigScreen(fault_name))


class ModifyConfigScreen(Screen):
    """The second screen for modifying the YAML config of the selected experiment."""

    def __init__(self, fault_name: str) -> None:
        super().__init__()
        self.fault_name = fault_name
        self.experiment_data = FAULT_EXPERIMENTS[fault_name]
        self.current_fields = self.experiment_data["editable_fields"].copy()

    def compose(self) -> ComposeResult:
        yield Header(name=f"Modify YAML Config - {self.experiment_data['kind']}")
        with Horizontal():
            with Vertical(id="options-pane"):
                yield Label("Parameters")
                # Create a ListView of the editable fields
                parameter_items = [
                    ListItem(Label(f"{field_name}: {self.current_fields[field_name]}"))
                    for field_name in self.current_fields.keys()
                ]
                yield ListView(*parameter_items, id="parameters-list")

                yield Button("Inject Chaos", variant="primary", id="inject-button")

            with Vertical(id="preview-pane"):
                yield Static(
                    "Use arrow keys to select a parameter and Enter to edit.",
                    id="description",
                )
                yield Static(id="code-preview")
        yield Footer()

    def on_mount(self) -> None:
        """Update the preview on mount and focus the parameters list."""
        self.update_preview()
        parameters_list = self.query_one("#parameters-list", ListView)
        parameters_list.focus()
        parameters_list.index = 0

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Update description when parameter is highlighted."""
        if event.list_view.id == "parameters-list" and event.item is not None:
            parameter_text = str(event.item.query_one(Label).renderable)
            field_name = parameter_text.split(":")[0]
            description = self.query_one("#description", Static)
            description.update(
                f"Selected: {field_name}. Press Enter to edit this parameter."
            )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle parameter selection for editing."""
        if event.list_view.id == "parameters-list" and event.item is not None:
            parameter_text = str(event.item.query_one(Label).renderable)
            field_name = parameter_text.split(":")[0]
            current_value = self.current_fields[field_name]

            # Push an input screen for editing the parameter
            self.app.push_screen(
                InputScreen(field_name, current_value, self.experiment_data),
                self.handle_parameter_update
            )

    def handle_parameter_update(self, result):
        """Handle the result from the input screen."""
        if result:
            field_name, new_value = result
            self.current_fields[field_name] = new_value
            self.refresh_parameter_list()
            self.update_preview()

    def refresh_parameter_list(self):
        """Refresh the parameter list with updated values."""
        parameters_list = self.query_one("#parameters-list", ListView)
        parameters_list.clear()

        # Add updated parameter items
        for field_name in self.current_fields.keys():
            item = ListItem(
                Label(f"{field_name}: {self.current_fields[field_name]}")
            )
            parameters_list.append(item)

    def update_preview(self):
        """Helper to regenerate and display the YAML preview."""
        yaml_preview = generate_yaml(
            self.experiment_data["kind"], self.current_fields
        )
        code_preview = self.query_one("#code-preview", Static)
        code_preview.update(yaml_preview)


class InputScreen(Screen):
    """Screen for editing a parameter value."""

    def __init__(
        self, field_name: str, current_value: str, experiment_data: dict
    ):
        super().__init__()
        self.field_name = field_name
        self.current_value = current_value
        self.experiment_data = experiment_data

    def compose(self) -> ComposeResult:
        yield Header(name=f"Edit {self.field_name}")
        with Vertical():
            yield Label(f"Editing: {self.field_name}")
            yield Label(f"Current value: {self.current_value}")

            # Check if this field has predefined options
            if (self.field_name == "action" and
                    "action_options" in self.experiment_data):
                yield Label("Available options:")
                action_options = self.experiment_data["action_options"]
                option_items = [
                    ListItem(Label(option)) for option in action_options
                ]
                yield ListView(*option_items, id="options-list")
            else:
                yield Input(value=self.current_value, id="input-field")

            with Horizontal():
                yield Button("Save", variant="primary", id="save-button")
                yield Button("Cancel", id="cancel-button")
        yield Footer()

    def on_mount(self) -> None:
        """Focus the appropriate input field."""
        try:
            self.query_one("#options-list", ListView).focus()
        except Exception:
            try:
                self.query_one("#input-field", Input).focus()
            except Exception:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-button":
            try:
                # Try to get selected option from ListView
                options_list = self.query_one("#options-list", ListView)
                if options_list.highlighted_child:
                    selected_option = str(
                        options_list.highlighted_child.query_one(Label)
                        .renderable
                    )
                    self.dismiss((self.field_name, selected_option))
                else:
                    self.dismiss(None)
            except Exception:
                try:
                    # Get text from Input field
                    input_field = self.query_one("#input-field", Input)
                    new_value = input_field.value
                    self.dismiss((self.field_name, new_value))
                except Exception:
                    self.dismiss(None)
        elif event.button.id == "cancel-button":
            self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle option selection."""
        if event.list_view.id == "options-list" and event.item is not None:
            selected_option = str(event.item.query_one(Label).renderable)
            self.dismiss((self.field_name, selected_option))


class FaultInjectorApp(App):
    """Main App class."""

    CSS_PATH = "fault_injector.tcss"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("b", "app.pop_screen", "Back", show=True),
    ]

    # Start with the experiment selection screen
    SCREENS = {"selection": ExperimentSelectionScreen}

    def on_mount(self) -> None:
        self.push_screen("selection")


if __name__ == "__main__":
    app = FaultInjectorApp()
    app.run()
