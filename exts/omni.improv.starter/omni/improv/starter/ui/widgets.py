"""
Reusable omni.ui widgets and layout helpers for Omniverse Kit extensions.
"""

from typing import Callable, Optional
try:
    import omni.ui as ui
except ImportError:
    ui = None


def create_section_header(title: str, subtitle: Optional[str] = None):
    """Creates a clean styled section header with optional subtitle."""
    if not ui:
        return
    with ui.VStack(height=0, spacing=2):
        ui.Label(title, name="header")
        if subtitle:
            ui.Label(subtitle, name="subtext")
        ui.Spacer(height=4)


def create_action_card(title: str, description: str, button_text: str, on_click: Callable, button_style: str = "primary"):
    """Creates an action card with title, description, and an action button."""
    if not ui:
        return
    with ui.ZStack():
        ui.Rectangle(style={"background_color": 0xFF282B30, "border_radius": 6, "border_color": 0xFF383C44, "border_width": 1})
        with ui.VStack(spacing=6, style={"padding": 10}):
            ui.Label(title, name="accent")
            ui.Label(description, name="subtext", word_wrap=True)
            ui.Spacer(height=2)
            btn = ui.Button(button_text, height=28, name=button_style)
            btn.set_clicked_fn(on_click)


def create_slider_row(label: str, min_val: float, max_val: float, default_val: float, on_changed: Optional[Callable] = None):
    """Creates a labeled horizontal float slider."""
    if not ui:
        return None
    model = ui.SimpleFloatModel(default_val)
    if on_changed:
        model.add_value_changed_fn(lambda m: on_changed(m.as_float))
    
    with ui.HStack(height=24, spacing=8):
        ui.Label(label, width=120)
        slider = ui.FloatSlider(model, min=min_val, max=max_val, step=0.1)
        ui.FloatDrag(model, width=60, step=0.1)
    return model
