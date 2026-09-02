"""
Omniverse Kit Extension Entry Point.
Implements the omni.ext.IExt lifecycle hooks for startup and shutdown.
"""

from typing import Optional
from .ui.main_window import MainWindow

try:
    import omni.ext
    import omni.kit.ui
    HAS_OMNI_EXT = True
except ImportError:
    HAS_OMNI_EXT = False
    # Mock base class when running in standalone Python outside Omniverse Kit
    class MockIExt:
        pass
    omni = type("omni", (), {"ext": type("ext", (), {"IExt": MockIExt})})()


class ImprovStarterExtension(omni.ext.IExt if HAS_OMNI_EXT else object):
    """
    Main Omniverse Kit Extension lifecycle class.
    Handles startup, menu registration, window lifecycle, and graceful shutdown.
    """

    MENU_PATH = "Window/Improv Starter"

    def __init__(self):
        super().__init__()
        self._window: Optional[MainWindow] = None
        self._menu_item = None

    def on_startup(self, ext_id: str):
        """
        Called when the extension is loaded and initialized by Omniverse Kit.
        
        Args:
            ext_id: Unique extension identifier string provided by Kit runtime.
        """
        print(f"[omni.improv.starter] Starting extension (ext_id: {ext_id})")

        self._window = MainWindow()

        # Register menu item under Window > Improv Starter
        if HAS_OMNI_EXT:
            try:
                editor_menu = omni.kit.ui.get_editor_menu()
                if editor_menu:
                    self._menu_item = editor_menu.add_item(
                        self.MENU_PATH,
                        self._on_menu_click,
                        toggle=True,
                        value=True
                    )
            except Exception as e:
                print(f"[omni.improv.starter] Note: Menu registration warning: {e}")

        # Show the main window on startup
        if self._window:
            self._window.show()

    def on_shutdown(self):
        """
        Called when the extension is disabled or Omniverse Kit is exiting.
        Cleans up UI windows, menu items, and event handlers.
        """
        print("[omni.improv.starter] Shutting down extension...")

        if self._window:
            self._window.destroy()
            self._window = None

        if HAS_OMNI_EXT and self._menu_item:
            try:
                editor_menu = omni.kit.ui.get_editor_menu()
                if editor_menu:
                    editor_menu.remove_item(self._menu_item)
            except Exception as e:
                print(f"[omni.improv.starter] Warning removing menu item: {e}")
            self._menu_item = None

    def _on_menu_click(self, menu, value):
        """Toggles window visibility when user clicks the menu entry."""
        if not self._window:
            return
        if value:
            self._window.show()
        else:
            self._window.hide()
