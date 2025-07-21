import os
import yaml
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.console import Group
from pynput import keyboard

# --- Configuration & Data ---

# A dictionary to hold the menu options and their associated YAML templates/descriptions.
# In a real app, you might load these from separate files.
EXPERIMENTS = {
    "Pod Faults": {
        "description": "Simulates pod-level failures like kills, failures, and container-specific issues.",
        "yaml_file": "templates/pod_chaos_template.yaml",
    },
    "Network Faults": {
        "description": "Simulates network issues like latency, packet loss, and corruption.",
        "yaml_file": "templates/network_chaos_template.yaml",
    },
    "Stress Scenarios": {
        "description": "Injects CPU or memory stress on targeted pods.",
        "yaml_file": "templates/stress_chaos_template.yaml",
    },
    "...": {
        "description": "More chaos types to be added...",
        "yaml_file": None,
    },
    "Schedule": {
        "description": "Future: Schedule chaos experiments to run at a specific time.",
        "yaml_file": None,
    },
    "Workflows": {
        "description": "Future: Chain multiple experiments together in a sequence.",
        "yaml_file": None,
    },
    "help": {
        "description": "Displays help information about the Fault Injector tool and its commands.",
        "yaml_file": None,
    },
}

MENU_ITEMS = list(EXPERIMENTS.keys())

# --- Main Application State Machine ---

class FaultInjectorApp:
    def __init__(self):
        self.console = Console()
        self.current_screen = "select_experiment"
        self.running = True
        self.selected_experiment = None
        self.yaml_content = None
        self.screen_stack = ["select_experiment"]  # For navigation history

        # Initialize screens
        self.screens = {
            "select_experiment": SelectExperimentScreen(self),
            "modify_yaml": ModifyYAMLScreen(self),
            "execute": ExecuteScreen(self),
        }

    def transition_to(self, screen_name, **kwargs):
        """Navigate to a different screen within the same app instance"""
        self.current_screen = screen_name
        self.screen_stack.append(screen_name)

        # Pass any data between screens
        if "experiment" in kwargs:
            self.selected_experiment = kwargs["experiment"]
        if "yaml_content" in kwargs:
            self.yaml_content = kwargs["yaml_content"]

    def go_back(self):
        """Return to previous screen like 'cd ..' in terminal"""
        if len(self.screen_stack) > 1:
            self.screen_stack.pop()
            self.current_screen = self.screen_stack[-1]
            return True
        return False

    def quit_app(self):
        """Exit the entire application"""
        self.running = False

    def run(self):
        """Main event loop - stays running until quit"""
        while self.running:
            current_screen_obj = self.screens[self.current_screen]
            current_screen_obj.draw()

            # Use a flag to control when to break the listener
            current_screen_obj.continue_listening = True

            def on_press_wrapper(key):
                current_screen_obj.on_press(key)
                if not current_screen_obj.continue_listening:
                    return False  # This stops the listener

            with keyboard.Listener(on_press=on_press_wrapper) as listener:
                listener.join()

        self.console.print("\n[bold green]Goodbye![/bold green]")

# --- UI Classes for Different Screens ---


class SelectExperimentScreen:
    def __init__(self, app):
        self.app = app
        self.console = app.console
        self.layout = self._create_layout()
        self.selected_index = 0
        self.continue_listening = True

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
            content = Group(description, Text("\n"), syntax)
            return Panel(
                content, title="Preview", border_style="cyan"
            )
        elif selected_item == "help":
            return Panel(
                f"{description}\n\n"
                "This tool helps you inject faults into your Kubernetes cluster.\n\n"
                "Use ↑ and ↓ arrow keys to navigate.\n\n"
                "Press Enter to select an option.\n\n"
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
        """Handles keyboard input."""
        try:
            if key == keyboard.Key.up:
                self.selected_index = (self.selected_index - 1) % len(MENU_ITEMS)
            elif key == keyboard.Key.down:
                self.selected_index = (self.selected_index + 1) % len(MENU_ITEMS)
            elif key == keyboard.Key.enter:
                selected_option = MENU_ITEMS[self.selected_index]

                # Handle different menu selections
                if selected_option in ["Pod Faults", "Network Faults",
                                     "Stress Scenarios"]:
                    # Transition to YAML modification screen
                    self.app.transition_to("modify_yaml",
                                          experiment=selected_option)
                    self.continue_listening = False
                elif selected_option == "help":
                    # Just redraw to show help, don't transition
                    pass
                else:
                    self.console.print(
                        f"\n[yellow]'{selected_option}' not implemented yet[/yellow]"
                    )

            elif key.char == "q":
                self.app.quit_app()
                self.continue_listening = False
        except AttributeError:
            pass  # Ignore non-character keys like shift, etc.

        # Redraw the screen after every key press
        self.draw()


class ModifyYAMLScreen:
    def __init__(self, app):
        self.app = app
        self.console = app.console
        self.layout = self._create_layout()
        self.continue_listening = True

    def _create_layout(self):
        """Creates the layout for YAML modification screen."""
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(ratio=1, name="main"),
            Layout(size=3, name="footer"),
        )
        return layout

    def draw(self):
        """Renders the YAML modification screen."""
        experiment = self.app.selected_experiment
        self.layout["header"].update(
            Panel(Text(f"2/ Modify YAML Config - {experiment}",
                      justify="center", style="bold blue"))
        )

        # Load and display YAML content
        experiment_info = EXPERIMENTS[experiment]
        if experiment_info["yaml_file"] and os.path.exists(experiment_info["yaml_file"]):
            with open(experiment_info["yaml_file"], "r") as f:
                yaml_content = f.read()
            syntax = Syntax(yaml_content, "yaml", theme="dracula", line_numbers=True)
            self.layout["main"].update(
                Panel(syntax, title="YAML Configuration", border_style="cyan")
            )
        else:
            self.layout["main"].update(
                Panel("No YAML template available", title="YAML Configuration")
            )

        self.layout["footer"].update(
            Panel(Text("(Enter) Execute  (b) Back  (q) Quit", justify="center"))
        )
        self.console.clear()
        self.console.print(self.layout)

    def on_press(self, key):
        """Handles keyboard input for YAML screen."""
        try:
            if key == keyboard.Key.enter:
                self.app.transition_to("execute")
                self.continue_listening = False
            elif key.char == "b":
                self.app.go_back()
                self.continue_listening = False
            elif key.char == "q":
                self.app.quit_app()
                self.continue_listening = False
        except AttributeError:
            pass

        self.draw()


class ExecuteScreen:
    def __init__(self, app):
        self.app = app
        self.console = app.console
        self.layout = self._create_layout()
        self.continue_listening = True

    def _create_layout(self):
        """Creates the layout for execution screen."""
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(ratio=1, name="main"),
            Layout(size=3, name="footer"),
        )
        return layout

    def draw(self):
        """Renders the execution screen."""
        experiment = self.app.selected_experiment
        self.layout["header"].update(
            Panel(Text(f"3/ Execute - {experiment}",
                      justify="center", style="bold blue"))
        )

        self.layout["main"].update(
            Panel(
                f"Ready to execute {experiment} chaos experiment!\n\n"
                "This would typically:\n"
                "• Validate the YAML configuration\n"
                "• Apply to Kubernetes cluster\n"
                "• Monitor the experiment\n"
                "• Provide real-time feedback\n\n"
                "[bold green]Simulation mode - no actual execution[/bold green]",
                title="Execution Status",
                border_style="green"
            )
        )

        self.layout["footer"].update(
            Panel(Text("(r) Run  (b) Back  (q) Quit", justify="center"))
        )
        self.console.clear()
        self.console.print(self.layout)

    def on_press(self, key):
        """Handles keyboard input for execute screen."""
        try:
            if key.char == "r":
                self.console.print(
                    "\n[bold green]Executing experiment... (simulated)[/bold green]"
                )
                # Here you would actually execute the chaos experiment
                self.continue_listening = False
            elif key.char == "b":
                self.app.go_back()
                self.continue_listening = False
            elif key.char == "q":
                self.app.quit_app()
                self.continue_listening = False
        except AttributeError:
            pass

        self.draw()


# --- Template Files (for setup) ---


def setup_template_files():
    """Creates dummy YAML template files for the demo to work."""
    if not os.path.exists("templates"):
        os.makedirs("templates")

    pod_chaos_yaml = """
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
"""

    network_chaos_yaml = """
apiVersion: chaos-mesh.org/v1alpha1
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

    stress_chaos_yaml = """
apiVersion: chaos-mesh.org/v1alpha1
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
    app = FaultInjectorApp()
    app.run()
