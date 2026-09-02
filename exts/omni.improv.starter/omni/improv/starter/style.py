"""
UI Stylesheet definitions for Omniverse Improv Starter.
Adheres to NVIDIA Omniverse dark theme guidelines with high-contrast accent highlights.
"""

# NVIDIA Green Accent Palette
NVIDIA_GREEN = 0xFF00B976      # 0xAABBGGRR in omni.ui format (or hex colors)
NVIDIA_GREEN_HOVER = 0xFF10D086
DARK_BG_PRIMARY = 0xFF1A1C1E
DARK_BG_SECONDARY = 0xFF24272B
DARK_BG_CARD = 0xFF2D3139
BORDER_COLOR = 0xFF3E434D
TEXT_PRIMARY = 0xFFF0F2F5
TEXT_MUTED = 0xFF8E95A5
ACCENT_BLUE = 0xFFD87820
ACCENT_ORANGE = 0xFF2080E0
ACCENT_RED = 0xFF3845E0

STYLE = {
    "Window": {
        "background_color": DARK_BG_PRIMARY,
        "padding": 12,
    },
    "CollapsableFrame": {
        "background_color": DARK_BG_SECONDARY,
        "secondary_color": DARK_BG_CARD,
        "border_color": BORDER_COLOR,
        "border_width": 1.0,
        "border_radius": 6.0,
        "padding": 8,
    },
    "CollapsableFrame:hover": {
        "border_color": 0xFF5A6270,
    },
    "Label": {
        "color": TEXT_PRIMARY,
        "font_size": 13,
    },
    "Label::header": {
        "color": TEXT_PRIMARY,
        "font_size": 15,
        "font_weight": "bold",
    },
    "Label::subtext": {
        "color": TEXT_MUTED,
        "font_size": 11,
    },
    "Label::accent": {
        "color": 0xFF76B900,
        "font_size": 13,
        "font_weight": "bold",
    },
    "Button": {
        "background_color": DARK_BG_CARD,
        "border_color": BORDER_COLOR,
        "border_width": 1.0,
        "border_radius": 4.0,
        "padding": 6,
        "color": TEXT_PRIMARY,
    },
    "Button:hover": {
        "background_color": 0xFF3D424D,
        "border_color": 0xFF76B900,
    },
    "Button:pressed": {
        "background_color": 0xFF202227,
    },
    "Button::primary": {
        "background_color": 0xFF1A6B38,
        "border_color": 0xFF76B900,
        "border_width": 1.0,
        "border_radius": 4.0,
        "color": 0xFFFFFFFF,
        "font_weight": "bold",
    },
    "Button::primary:hover": {
        "background_color": 0xFF238E4B,
        "border_color": 0xFF90E000,
    },
    "Button::danger": {
        "background_color": 0xFF6B2020,
        "border_color": 0xFFD04040,
        "border_width": 1.0,
        "border_radius": 4.0,
        "color": 0xFFFFFFFF,
    },
    "Button::danger:hover": {
        "background_color": 0xFF8E2A2A,
    },
    "Field": {
        "background_color": DARK_BG_PRIMARY,
        "border_color": BORDER_COLOR,
        "border_width": 1.0,
        "border_radius": 4.0,
        "color": TEXT_PRIMARY,
        "padding": 4,
    },
    "Slider": {
        "background_color": DARK_BG_PRIMARY,
        "secondary_color": 0xFF1A6B38,
        "border_color": BORDER_COLOR,
        "border_width": 1.0,
        "border_radius": 4.0,
    }
}
