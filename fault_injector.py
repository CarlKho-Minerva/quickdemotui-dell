import os
import yaml
import tempfile  # To save modified YAML
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.prompt import Prompt
from rich.console import Group
from pynput import keyboard

# --- Configuration & Data ---

# A dictionary to hold the menu options and their associated YAML templates/descriptions.
EXPERIMENTS = {
    "Pod Faults": {
        "description": "Simulates pod-level failures like kills, failures, and container-specific issues.",
        "yaml_file": "templates/pod_chaos_template.yaml",
        "editable_fields": [
            "metadata.name",
            "metadata.namespace",
            "spec.action",
            "spec.mode",
            "spec.duration",
            "spec.selector.labelSelectors.'app.kubernetes.io/component'",
        ],
    },
    "Network Faults": {
        "description": "Simulates network issues like latency, packet loss, and corruption.",
        "yaml_file": "templates/network_chaos_template.yaml",
        "editable_fields": [
            "metadata.name",
            "spec.selector.namespaces",
            "spec.delay.latency",
        ],
    },
    "Stress Scenarios": {
        "description": "Injects CPU or memory stress on targeted pods.",
        "yaml_file": "templates/stress_chaos_template.yaml",
        "editable_fields": [
            "metadata.name",
            "spec.stressors.cpu.workers",
            "spec.stressors.cpu.load",
        ],
    },
    "help": {
        "description": "Displays help information about the Fault Injector tool and its commands.",
        "yaml_file": None,
    },
}

MENU_ITEMS = list(EXPERIMENTS.keys())

# --- Utility Functions ---


def get_nested_value(d, keys):
    """Access a nested dictionary value using a list of keys."""
    for key in keys:
        d = d[key]
    return d


def set_nested_value(d, keys, value):
    """Set a nested dictionary value using a list of keys."""
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    # Attempt to convert value to correct type
    try:
        current_val = get_nested_value(d, keys)
        value = type(current_val)(value)
    except (ValueError, TypeError):
        pass  # Keep as string if conversion fails
    d[keys[-1]] = value


# --- UI Class for Screen 2 ---


class ModifyYamlScreen:
    def __init__(self, console, experiment_name):
        self.console = console
        self.experiment_name = experiment_name
        self.experiment_info = EXPERIMENTS[experiment_name]

        with open(self.experiment_info["yaml_file"], "r") as f:
            self.yaml_data = yaml.safe_load(f)

        self.editable_fields = self.experiment_info["editable_fields"]
        self.menu_items = self.editable_fields + ["Inject Chaos"]
        self.selected_index = 0
        self.running = True
        self.last_drawn_state = None  # Track state to prevent unnecessary redraws

        self.layout = self._create_layout()

    def _create_layout(self):
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(ratio=1, name="main"),
            Layout(size=3, name="footer"),
        )
        layout["main"].split_row(Layout(name="left"), Layout(name="right", ratio=2))
        return layout

    def _get_menu_text(self):
        menu_text = Text()
        for i, item in enumerate(self.menu_items):
            value_str = ""
            if item != "Inject Chaos":
                try:
                    value = get_nested_value(self.yaml_data, item.split("."))
                    value_str = f": {value}"
                except KeyError:
                    value_str = ": <not set>"

            if i == self.selected_index:
                menu_text.append(f"> {item}{value_str}\n", style="bold green")
            else:
                menu_text.append(f"  {item}{value_str}\n")
        return menu_text

    def _get_highlighted_yaml(self):
        """Returns the YAML content with the selected line highlighted."""
        yaml_str = yaml.dump(self.yaml_data, sort_keys=False)

        # Simple highlighting logic for this prototype
        # A more robust solution might parse YAML line info
        highlight_term = None
        if self.selected_index < len(self.editable_fields):
            highlight_term = self.editable_fields[self.selected_index].split(".")[-1]

        if highlight_term:
            # Highlight specific lines containing the term
            lines = yaml_str.split("\n")
            highlighted_yaml = ""
            for line in lines:
                if highlight_term in line:
                    highlighted_yaml += f">>> {line}\n"
                else:
                    highlighted_yaml += f"{line}\n"
            return Syntax(highlighted_yaml, "yaml", theme="dracula", line_numbers=True)
        else:
            return Syntax(yaml_str, "yaml", theme="dracula", line_numbers=True)

    def draw(self):
        # Create a state signature to check if redraw is needed
        current_state = (self.selected_index, str(self.yaml_data))
        if current_state == self.last_drawn_state:
            return  # Skip redraw if nothing changed

        self.layout["header"].update(
            Panel(
                Text(
                    f"2/ Modify YAML Config - {self.yaml_data.get('kind', '')}",
                    justify="center",
                    style="bold blue",
                )
            )
        )
        self.layout["left"].update(
            Panel(self._get_menu_text(), title="Parameters", border_style="magenta")
        )
        self.layout["right"].update(
            Panel(
                self._get_highlighted_yaml(), title="YAML Preview", border_style="cyan"
            )
        )
        self.layout["footer"].update(
            Panel(
                Text(
                    "(↑/↓) Navigate  (Enter) Edit  (q) Quit  (b) Back", justify="center"
                )
            )
        )
        self.console.clear()
        self.console.print(self.layout)
        self.last_drawn_state = current_state

    def edit_field(self):
        field_path = self.editable_fields[self.selected_index]
        keys = field_path.split(".")
        current_value = get_nested_value(self.yaml_data, keys)

        # Temporarily exit rich rendering to use Prompt
        self.console.clear()
        new_value = Prompt.ask(
            f"Enter new value for [bold cyan]{field_path}[/bold cyan]",
            default=str(current_value),
        )

        set_nested_value(self.yaml_data, keys, new_value)
        self.draw()

    def on_press(self, key):
        try:
            if key == keyboard.Key.up:
                self.selected_index = (self.selected_index - 1) % len(self.menu_items)
            elif key == keyboard.Key.down:
                self.selected_index = (self.selected_index + 1) % len(self.menu_items)
            elif key == keyboard.Key.enter:
                if self.selected_index == len(
                    self.editable_fields
                ):  # "Inject Chaos" is selected
                    self.console.print("\n[bold green]Injecting Chaos...[/bold green]")
                    # Save the modified YAML to a temp file and run kubectl
                    with tempfile.NamedTemporaryFile(
                        mode="w", delete=False, suffix=".yaml"
                    ) as tmp:
                        yaml.dump(self.yaml_data, tmp)
                        tmp_path = tmp.name

                    self.console.print(f"Applying modified config from {tmp_path}")
                    # In a real tool, you would now call a function to start Screen 3
                    # os.system(f"kubectl apply -f {tmp_path}")
                    self.running = False
                    return False
                else:
                    self.edit_field()
            elif key.char == "q":
                self.running = False
                return False
            elif key.char == "b":
                # Go back to the previous screen
                main()
                self.running = False
                return False

        except AttributeError:
            pass  # Ignore other keys

        if self.running:
            self.draw()

    def run(self):
        self.draw()
        with keyboard.Listener(on_press=self.on_press) as listener:
            listener.join()


# --- UI Class for Screen 1 (Slightly modified to call Screen 2) ---


class SelectExperimentScreen:
    def __init__(self, console):
        self.console = console
        self.layout = self._create_layout()
        self.selected_index = 0
        self.running = True

    # ... (_create_layout, _get_menu_text, _get_preview_content, draw methods are the same as before) ...
    def _create_layout(self):
        """Creates the two-pane layout for the screen."""
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(ratio=1, name="main"),
            Layout(size=3, name="footer"),
        )
        layout["main"].split_row(Layout(name="left"), Layout(name="right", ratio=2))
        return layout

    def _get_menu_text(self):
        """Generates the menu text with the current selection highlighted."""
        menu_text = Text()
        for i, item in enumerate(MENU_ITEMS):
            if i == self.selected_index:
                menu_text.append(f"> {item}\n", style="bold green")
            else:
                menu_text.append(f"  {item}\n")
        return menu_text

    def _get_preview_content(self):
        """Generates the content for the right preview pane based on the selection."""
        selected_item = MENU_ITEMS[self.selected_index]
        experiment_info = EXPERIMENTS[selected_item]

        description = Text(experiment_info["description"], style="bold yellow")

        if experiment_info["yaml_file"] and os.path.exists(
            experiment_info["yaml_file"]
        ):
            with open(experiment_info["yaml_file"], "r") as f:
                yaml_content = f.read()
            syntax = Syntax(yaml_content, "yaml", theme="dracula", line_numbers=True)
            # Use Group to properly combine Text and Syntax objects
            content = Group(description, syntax)
            return Panel(
                content, title="Preview", border_style="cyan"
            )
        elif selected_item == "help":
            return Panel(
                f"{description}\n\n"
                "This tool helps you inject faults into your Kubernetes cluster.\n"
                "Use ↑ and ↓ arrow keys to navigate.\n"
                "Press Enter to select an option.\n"
                "Press 'q' to quit at any time.",
                title="Help",
                border_style="cyan",
            )
        else:
            return Panel(description, title="Preview", border_style="cyan")

    def draw(self):
        """Renders the entire screen."""
        self.layout["header"].update(
            Panel(Text("1/ Select Experiment", justify="center", style="bold blue"))
        )
        self.layout["left"].update(
            Panel(self._get_menu_text(), title="Fault_Injector", border_style="magenta")
        )
        self.layout["right"].update(self._get_preview_content())
        self.layout["footer"].update(
            Panel(Text("(↑/↓) Navigate  (Enter) Select  (q) Quit", justify="center"))
        )
        self.console.clear()
        self.console.print(self.layout)

    def on_press(self, key):
        try:
            if key == keyboard.Key.up:
                self.selected_index = (self.selected_index - 1) % len(MENU_ITEMS)
            elif key == keyboard.Key.down:
                self.selected_index = (self.selected_index + 1) % len(MENU_ITEMS)
            elif key == keyboard.Key.enter:
                selected_option = MENU_ITEMS[self.selected_index]
                if EXPERIMENTS[selected_option].get("yaml_file"):
                    # Transition to the ModifyYamlScreen
                    next_screen = ModifyYamlScreen(self.console, selected_option)
                    next_screen.run()
                    self.running = False
                elif selected_option == "help":
                    # Just redraw to show the help content clearly
                    self.draw()
                else:
                    self.console.print(
                        f"\n[bold yellow]'{selected_option}' is not yet implemented.[/bold yellow]"
                    )

                # Stop the listener for the current screen
                return False
            elif key.char == "q":
                self.running = False
                return False
        except AttributeError:
            pass

        if self.running:
            self.draw()

    def run(self):
        self.draw()
        with keyboard.Listener(on_press=self.on_press) as listener:
            listener.join()


# --- Main Application Logic ---


def main():
    """Main entry point for the application."""
    console = Console()
    screen1 = SelectExperimentScreen(console)
    screen1.run()


# ... (setup_template_files function is the same as before) ...
def setup_template_files():
    """Creates dummy YAML template files for the demo to work."""
    if not os.path.exists("templates"):
        os.makedirs("templates")

    pod_chaos_yaml = """apiVersion: chaos-mesh.org/v1alpha1
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
"""

    network_chaos_yaml = """apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: delay
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
"""

    stress_chaos_yaml = """apiVersion: chaos-mesh.org/v1alpha1
kind: StressChaos
metadata:
  name: cpu-stress
spec:
  mode: one
  selector:
    namespaces:
      - default
  stressors:
    cpu:
      workers: 1
      load: 50
"""
    with open("templates/pod_chaos_template.yaml", "w") as f:
        f.write(pod_chaos_yaml)
    with open("templates/network_chaos_template.yaml", "w") as f:
        f.write(network_chaos_yaml)
    with open("templates/stress_chaos_template.yaml", "w") as f:
        f.write(stress_chaos_yaml)


if __name__ == "__main__":
    setup_template_files()
    main()
    print("\nExiting Fault Injector.")
