"""
Main dockable omni.ui Window for Omniverse Improv Starter.
Provides an interactive control panel for scene setup, procedural generation, and physics tweaking.
"""

import random
from typing import Optional
from pxr import Gf, Sdf, Usd, UsdPhysics

from ..style import STYLE
from ..core.stage_builder import StageBuilder
from ..core.physics_helper import PhysicsHelper
from .widgets import create_section_header, create_action_card, create_slider_row

try:
    import omni.ui as ui
    import omni.usd
    HAS_OMNI = True
except ImportError:
    ui = None
    omni = None
    HAS_OMNI = False


class MainWindow:
    """The main dockable UI window in Omniverse Kit."""

    WINDOW_TITLE = "Omniverse Improv Starter"

    def __init__(self):
        self._window: Optional[ui.Window] = None
        self._spawn_counter = 0
        self._enable_physics = True
        self._current_material_preset = "neon_cyan"
        self._spawn_height = 60.0
        self._gravity_val = 981.0
        self._domino_count = 25
        self._tower_floors = 7

    def show(self):
        """Creates or shows the dockable window."""
        if not HAS_OMNI or not ui:
            print("[Omniverse Improv Starter] omni.ui is not available (running in standalone/mock mode).")
            return

        if self._window:
            self._window.visible = True
            self._window.focus()
            return

        self._window = ui.Window(
            self.WINDOW_TITLE,
            width=400,
            height=720
        )
        self._window.frame.style = STYLE
        self._window.set_visibility_changed_fn(self._on_visibility_changed)

        with self._window.frame:
            with ui.ScrollingFrame():
                with ui.VStack(spacing=12, style={"padding": 12}):
                    self._build_header()
                    self._build_stage_setup_section()
                    self._build_procedural_physics_section()
                    self._build_quick_spawner_section()
                    self._build_physics_tweaker_section()
                    self._build_footer()

    def hide(self):
        """Hides the window."""
        if self._window:
            self._window.visible = False

    def destroy(self):
        """Cleans up window resources."""
        if self._window:
            self._window.destroy()
            self._window = None

    def _on_visibility_changed(self, visible: bool):
        pass

    def _get_stage(self) -> Optional[Usd.Stage]:
        return StageBuilder.get_current_stage()

    # ================= UI BUILDERS =================

    def _build_header(self):
        with ui.ZStack(height=48):
            ui.Rectangle(style={"background_color": 0xFF24272B, "border_radius": 6, "border_color": 0xFF00B976, "border_width": 1})
            with ui.HStack(style={"padding": 10}, spacing=10):
                ui.Label("⚡", width=24, style={"font_size": 20})
                with ui.VStack(spacing=2):
                    ui.Label("Omniverse Improv Starter", name="header")
                    ui.Label("USD • PhysX Physics • Procedural Workflows", name="subtext")

    def _build_stage_setup_section(self):
        with ui.CollapsableFrame("1. Studio & Stage Setup", collapsed=False):
            with ui.VStack(spacing=8, style={"padding": 8}):
                ui.Label("Initialize your stage with a physics ground collider and lighting rig.", name="subtext", word_wrap=True)
                
                with ui.HStack(spacing=6):
                    btn_setup = ui.Button("🚀 Setup Studio Stage", height=32, name="primary")
                    btn_setup.set_clicked_fn(self._on_setup_studio_stage)

                    btn_lights = ui.Button("💡 Add Lights Only", height=32)
                    btn_lights.set_clicked_fn(self._on_setup_lights)

                btn_clear = ui.Button("🗑️ Clear /World/Props", height=24, name="danger")
                btn_clear.set_clicked_fn(self._on_clear_props)

    def _build_procedural_physics_section(self):
        with ui.CollapsableFrame("2. Procedural Kinetic Generators", collapsed=False):
            with ui.VStack(spacing=10, style={"padding": 8}):
                # Domino Run Card
                create_action_card(
                    title="Arc Domino Chain & Trigger Ball",
                    description="Spawns an arced chain of dynamic dominoes with a rolling kinetic trigger sphere.",
                    button_text="Spawn Domino Run",
                    on_click=self._on_spawn_dominoes,
                    button_style="primary"
                )

                # Jenga Block Tower Card
                create_action_card(
                    title="Destructible Block Tower",
                    description="Stacks alternating wooden-style physics blocks ready for kinetic impact.",
                    button_text="Spawn Block Tower",
                    on_click=self._on_spawn_tower,
                    button_style="primary"
                )

                # Kinetic Ball Drop
                create_action_card(
                    title="Kinetic Ball Shower",
                    description="Spawns 15 randomized bouncy neon spheres dropping from height.",
                    button_text="Drop Kinetic Spheres",
                    on_click=self._on_spawn_ball_shower,
                    button_style="default"
                )

    def _build_quick_spawner_section(self):
        with ui.CollapsableFrame("3. Quick Primitive Spawner", collapsed=False):
            with ui.VStack(spacing=8, style={"padding": 8}):
                # Physics Toggle & Spawn Height
                with ui.HStack(height=24):
                    ui.Label("Dynamic Physics:", width=120)
                    cb = ui.CheckBox()
                    cb.model.set_value(self._enable_physics)
                    cb.model.add_value_changed_fn(lambda m: setattr(self, "_enable_physics", m.as_bool))

                create_slider_row(
                    label="Spawn Height (Y):",
                    min_val=10.0,
                    max_val=200.0,
                    default_val=self._spawn_height,
                    on_changed=lambda v: setattr(self, "_spawn_height", v)
                )

                # Material Preset Selector
                with ui.HStack(height=24):
                    ui.Label("Material Preset:", width=120)
                    presets = ["neon_cyan", "neon_magenta", "gold", "chrome", "matte_black", "rubber_red"]
                    combo = ui.ComboBox(0, *presets)
                    combo.model.add_item_changed_fn(
                        lambda m, item: setattr(self, "_current_material_preset", presets[combo.model.get_item_value_model().as_int])
                    )

                ui.Spacer(height=4)
                ui.Label("Spawn Primitives:", name="subtext")

                # Primitive Buttons Grid
                with ui.HStack(spacing=6):
                    for p_type, icon in [("Cube", "📦"), ("Sphere", "🔮"), ("Cylinder", "🛢️"), ("Capsule", "💊")]:
                        btn = ui.Button(f"{icon} {p_type}", height=30)
                        btn.set_clicked_fn(lambda pt=p_type: self._on_spawn_single_prim(pt))

    def _build_physics_tweaker_section(self):
        with ui.CollapsableFrame("4. Live Physics Controls", collapsed=True):
            with ui.VStack(spacing=8, style={"padding": 8}):
                ui.Label("Adjust stage physics properties in real time:", name="subtext")
                
                create_slider_row(
                    label="Gravity (cm/s²):",
                    min_val=0.0,
                    max_val=3000.0,
                    default_val=self._gravity_val,
                    on_changed=self._on_gravity_changed
                )

                with ui.HStack(spacing=6):
                    btn_zero_g = ui.Button("Zero-G (0.0)", height=26)
                    btn_zero_g.set_clicked_fn(lambda: self._set_gravity(0.0))

                    btn_earth_g = ui.Button("Earth G (981.0)", height=26)
                    btn_earth_g.set_clicked_fn(lambda: self._set_gravity(981.0))

                    btn_moon_g = ui.Button("Moon G (162.0)", height=26)
                    btn_moon_g.set_clicked_fn(lambda: self._set_gravity(162.0))

    def _build_footer(self):
        with ui.VStack(spacing=4):
            ui.Spacer(height=8)
            ui.Line(style={"color": 0xFF383C44})
            with ui.HStack():
                ui.Label("Omniverse Kit Extension v1.0.0", name="subtext")
                ui.Spacer()
                ui.Label("Ready", style={"color": 0xFF00B976, "font_size": 11})

    # ================= ACTION CALLBACKS =================

    def _on_setup_studio_stage(self):
        stage = self._get_stage()
        if not stage:
            print("[Omniverse Improv Starter] No active stage found.")
            return
        StageBuilder.setup_studio_environment(stage, add_ground=True, add_lighting=True)
        print("[Omniverse Improv Starter] Studio environment & physics scene initialized.")

    def _on_setup_lights(self):
        stage = self._get_stage()
        if not stage:
            return
        StageBuilder.spawn_lighting_rig(stage, "/World/Environment/Lights")

    def _on_clear_props(self):
        stage = self._get_stage()
        if not stage:
            return
        props_prim = stage.GetPrimAtPath("/World/Props")
        if props_prim.IsValid():
            stage.RemovePrim("/World/Props")
            print("[Omniverse Improv Starter] Cleared /World/Props.")

    def _on_spawn_dominoes(self):
        stage = self._get_stage()
        if not stage:
            return
        self._spawn_counter += 1
        path = f"/World/Props/DominoRun_{self._spawn_counter}"
        StageBuilder.spawn_domino_run(stage, path, count=28, spacing=16.0)
        print(f"[Omniverse Improv Starter] Spawned domino run at {path}")

    def _on_spawn_tower(self):
        stage = self._get_stage()
        if not stage:
            return
        self._spawn_counter += 1
        path = f"/World/Props/BlockTower_{self._spawn_counter}"
        x_offset = random.uniform(-40.0, 40.0)
        z_offset = random.uniform(-40.0, 40.0)
        StageBuilder.spawn_destructible_tower(stage, path, floors=8, base_pos=(x_offset, 0.0, z_offset))
        print(f"[Omniverse Improv Starter] Spawned block tower at {path}")

    def _on_spawn_ball_shower(self):
        stage = self._get_stage()
        if not stage:
            return
        presets = ["neon_cyan", "neon_magenta", "gold", "chrome", "rubber_red"]
        for i in range(15):
            self._spawn_counter += 1
            path = f"/World/Props/Ball_{self._spawn_counter}"
            rx = random.uniform(-60.0, 60.0)
            ry = self._spawn_height + random.uniform(20.0, 100.0)
            rz = random.uniform(-60.0, 60.0)
            radius = random.uniform(8.0, 18.0)
            preset = random.choice(presets)

            StageBuilder.spawn_primitive(
                stage,
                prim_type="Sphere",
                prim_path=path,
                position=(rx, ry, rz),
                size=radius * 2.0,
                dynamic_physics=True,
                material_preset=preset
            )

    def _on_spawn_single_prim(self, prim_type: str):
        stage = self._get_stage()
        if not stage:
            return
        self._spawn_counter += 1
        path = f"/World/Props/{prim_type}_{self._spawn_counter}"
        rx = random.uniform(-20.0, 20.0)
        rz = random.uniform(-20.0, 20.0)

        StageBuilder.spawn_primitive(
            stage,
            prim_type=prim_type,
            prim_path=path,
            position=(rx, self._spawn_height, rz),
            size=25.0,
            dynamic_physics=self._enable_physics,
            material_preset=self._current_material_preset
        )
        print(f"[Omniverse Improv Starter] Spawned {prim_type} at {path}")

    def _on_gravity_changed(self, val: float):
        self._gravity_val = val
        stage = self._get_stage()
        if stage:
            PhysicsHelper.ensure_physics_scene(stage, "/World/PhysicsScene", gravity_magnitude=val)

    def _set_gravity(self, val: float):
        self._gravity_val = val
        self._on_gravity_changed(val)
