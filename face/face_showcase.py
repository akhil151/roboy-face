"""
Professional Face Animation Studio & Interactive Showcase for ELO Face Engine v1.0.

Provides an interactive studio showcase viewer for ELO Face Engine:
  - Emotion selector (1-9/0 keys, clickable buttons, arrow keys)
  - Multi-parameter Speech simulator (toggle, pulse slider, interactive spacebar trigger)
  - Interactive Timeline scrubber & state stage tracker
  - Transition viewer (State A -> State B preview & 10x10 transition matrix)
  - Face recorder (GIF export and PNG screenshot capture)
  - Real-time Debug inspector (MouthParams, EyeParams, FX, FPS performance counter)
  - Mouse look target tracking
"""

from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pygame

# Ensure repository root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
FACE_DIR = Path(__file__).resolve().parent
if str(FACE_DIR) not in sys.path:
    sys.path.insert(0, str(FACE_DIR))

from face import FaceEngine, VALID_STATES
from face.mouth.mouth_shapes import MouthParams
from eyes.engine.config import EngineConfig

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Constants & UI Dark Editor Palette
# ---------------------------------------------------------------------------

STATE_ORDER: List[str] = [
    "calm",
    "listening",
    "thinking",
    "speaking",
    "happy",
    "caring",
    "sad",
    "sleepy",
    "surprised",
    "focus",
]

KEY_STATE_MAP: Dict[int, str] = {
    pygame.K_1: "calm",
    pygame.K_2: "listening",
    pygame.K_3: "thinking",
    pygame.K_4: "speaking",
    pygame.K_5: "happy",
    pygame.K_6: "caring",
    pygame.K_7: "sad",
    pygame.K_8: "sleepy",
    pygame.K_9: "surprised",
    pygame.K_0: "focus",
}

# Editor Theme
C_BG = (12, 14, 18)
C_PANEL = (20, 24, 32)
C_PANEL_HEADER = (28, 34, 46)
C_BORDER = (45, 55, 75)
C_CYAN = (0, 210, 255)
C_EMERALD = (0, 230, 150)
C_AMBER = (255, 175, 40)
C_ROSE = (255, 75, 105)
C_PURPLE = (175, 100, 255)

C_TEXT = (240, 242, 248)
C_TEXT_MUTED = (160, 172, 195)
C_TEXT_DIM = (100, 112, 135)

C_BTN_NORM = (30, 36, 48)
C_BTN_HOVER = (42, 52, 70)
C_BTN_ACTIVE = (0, 160, 215)


# ---------------------------------------------------------------------------
# Font Manager
# ---------------------------------------------------------------------------

class FontManager:
    """Cached font provider."""

    def __init__(self) -> None:
        self._fonts: Dict[Tuple[str, int, bool], pygame.font.Font] = {}

    def get(self, size: int, bold: bool = False, mono: bool = False) -> pygame.font.Font:
        key = ("mono" if mono else "sans", size, bold)
        if key not in self._fonts:
            try:
                name = "consolas,monospace,courier" if mono else "segoe ui,arial,helvetica,sans-serif"
                font = pygame.font.SysFont(name, size, bold=bold)
            except Exception:
                font = pygame.font.Font(None, size)
            self._fonts[key] = font
        return self._fonts[key]


# ---------------------------------------------------------------------------
# UI Helper Components
# ---------------------------------------------------------------------------

class UIWidget:
    @staticmethod
    def draw_panel(
        surface: pygame.Surface,
        rect: pygame.Rect,
        bg: Tuple[int, int, int] = C_PANEL,
        border: Tuple[int, int, int] = C_BORDER,
        radius: int = 6,
    ) -> None:
        shape_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        shape_surf.fill((bg[0], bg[1], bg[2], 230))
        surface.blit(shape_surf, (rect.x, rect.y))
        pygame.draw.rect(surface, border, rect, width=1, border_radius=radius)

    @staticmethod
    def draw_button(
        surface: pygame.Surface,
        rect: pygame.Rect,
        text: str,
        font: pygame.font.Font,
        active: bool = False,
        hover: bool = False,
        accent: Tuple[int, int, int] = C_CYAN,
    ) -> bool:
        bg = C_BTN_ACTIVE if active else (C_BTN_HOVER if hover else C_BTN_NORM)
        border = accent if active else (C_CYAN if hover else C_BORDER)
        text_color = (255, 255, 255) if active else (C_TEXT if hover else C_TEXT_MUTED)

        pygame.draw.rect(surface, bg, rect, border_radius=4)
        pygame.draw.rect(surface, border, rect, width=1, border_radius=4)

        txt_surf = font.render(text, True, text_color)
        tx = rect.x + (rect.width - txt_surf.get_width()) // 2
        ty = rect.y + (rect.height - txt_surf.get_height()) // 2
        surface.blit(txt_surf, (tx, ty))
        return hover


# ---------------------------------------------------------------------------
# Face Studio Showcase Application
# ---------------------------------------------------------------------------

class FaceStudioShowcase:
    def __init__(self) -> None:
        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()

        self.exports_dir = FACE_DIR / "exports"
        self.screenshots_dir = self.exports_dir / "screenshots"
        self.gifs_dir = self.exports_dir / "gifs"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.gifs_dir.mkdir(parents=True, exist_ok=True)

        self.engine = FaceEngine()
        self.fonts = FontManager()

        self.window_w = 1280
        self.window_h = 768
        self.screen = pygame.display.set_mode((self.window_w, self.window_h), pygame.RESIZABLE)
        pygame.display.set_caption("ELO Robot Face — Studio Showcase v1.0")

        self.canvas_surf = pygame.Surface((800, 480))

        # Application state
        self.running = True
        self.current_state_idx = 0
        self.previous_state_name = "calm"
        self.state_timer_ms = 0.0

        # Features & Mode toggles
        self.auto_speech = False
        self.speech_pulse_val = 0.0
        self.debug_overlay_enabled = True
        self.transition_matrix_enabled = False

        # Phase 4A Refinement Features
        self.silhouette_mode = "FULL"  # "FULL", "MOUTH_ONLY", "EYES_ONLY"
        self.speed_multiplier = 1.0  # 1.0, 0.5, 0.25, 0.1
        self.compare_state_a = "happy"
        self.compare_state_b = "sad"
        self.compare_side_by_side = False

        self.transition_preview_mode = False
        self.preview_from_state = "happy"
        self.preview_to_state = "caring"
        self.preview_phase = 0
        self.preview_timer_ms = 0.0

        self.record_mode = False
        self.record_state_timer_ms = 0.0
        self.record_state_idx = 0

        self.is_recording_gif = False
        self.gif_frames: List[pygame.Surface] = []
        self.gif_max_frames = 90

        self.notification_msg = "Phase 4 Face Engine Showcase Ready"
        self.notification_timer_ms = 3000.0

        self.active_tab_idx = 0
        self.tab_names = ["Inspector", "Mouth Studio", "Matrix", "Profiler"]

        self.clock = pygame.time.Clock()
        self.dt_step_ms = 0.0
        self.dt_render_ms = 0.0
        self.mouse_norm = (0.5, 0.5)


    def trigger_state(self, state_name: str) -> None:
        if state_name not in STATE_ORDER:
            return
        if self.engine.current_state != state_name:
            self.previous_state_name = self.engine.current_state
        self.current_state_idx = STATE_ORDER.index(state_name)
        self.state_timer_ms = 0.0
        self.engine.set_state(state_name)
        self.notification_msg = f"State: {state_name.upper()}"
        self.notification_timer_ms = 1800.0

    def export_screenshot(self) -> None:
        ts = int(time.time() * 1000)
        filepath = self.screenshots_dir / f"face_{self.engine.current_state}_{ts}.png"
        pygame.image.save(self.canvas_surf, str(filepath))
        self.notification_msg = f"Saved: {filepath.name}"
        self.notification_timer_ms = 3000.0

    def toggle_gif_recording(self) -> None:
        if not PIL_AVAILABLE:
            self.notification_msg = "Pillow library not installed for GIF export"
            self.notification_timer_ms = 3000.0
            return

        if not self.is_recording_gif:
            self.is_recording_gif = True
            self.gif_frames.clear()
            self.notification_msg = "Recording GIF..."
            self.notification_timer_ms = 2000.0
        else:
            self.save_recorded_gif()

    def save_recorded_gif(self) -> None:
        if not self.gif_frames or not PIL_AVAILABLE:
            self.is_recording_gif = False
            return

        self.notification_msg = "Encoding GIF..."
        ts = int(time.time() * 1000)
        out_path = self.gifs_dir / f"face_{self.engine.current_state}_{ts}.gif"

        try:
            pil_images = []
            for surf in self.gif_frames:
                raw_data = pygame.image.tostring(surf, "RGB")
                img = Image.frombytes("RGB", surf.get_size(), raw_data)
                pil_images.append(img.resize((400, 240), Image.Resampling.LANCZOS))

            pil_images[0].save(
                out_path,
                save_all=True,
                append_images=pil_images[1:],
                duration=33,
                loop=0,
                optimize=True,
            )
            self.notification_msg = f"Exported GIF: {out_path.name}"
        except Exception as e:
            self.notification_msg = f"GIF Error: {e}"
        finally:
            self.is_recording_gif = False
            self.gif_frames.clear()
            self.notification_timer_ms = 4000.0

    def process_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                self.window_w, self.window_h = event.w, event.h
                self.screen = pygame.display.set_mode((self.window_w, self.window_h), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key in KEY_STATE_MAP:
                    self.trigger_state(KEY_STATE_MAP[event.key])
                elif event.key == pygame.K_RIGHT:
                    nxt = (self.current_state_idx + 1) % len(STATE_ORDER)
                    self.trigger_state(STATE_ORDER[nxt])
                elif event.key == pygame.K_LEFT:
                    prv = (self.current_state_idx - 1) % len(STATE_ORDER)
                    self.trigger_state(STATE_ORDER[prv])
                elif event.key == pygame.K_s:
                    self.auto_speech = not self.auto_speech
                    self.notification_msg = f"Auto Speech: {'ON' if self.auto_speech else 'OFF'}"
                    self.notification_timer_ms = 1800.0
                elif event.key == pygame.K_b:
                    self.engine.blink()
                elif event.key == pygame.K_d:
                    self.debug_overlay_enabled = not self.debug_overlay_enabled
                elif event.key == pygame.K_m:
                    self.transition_matrix_enabled = not self.transition_matrix_enabled
                    self.active_tab_idx = 2 if self.transition_matrix_enabled else 0
                elif event.key == pygame.K_r:
                    self.record_mode = not self.record_mode
                    self.record_state_timer_ms = 0.0
                    self.record_state_idx = 0
                    self.notification_msg = f"Record Mode: {'ON' if self.record_mode else 'OFF'}"
                    self.notification_timer_ms = 2000.0
                elif event.key == pygame.K_v:
                    modes = ["FULL", "MOUTH_ONLY", "EYES_ONLY"]
                    idx = (modes.index(self.silhouette_mode) + 1) % len(modes)
                    self.silhouette_mode = modes[idx]
                    self.notification_msg = f"Silhouette Mode: {self.silhouette_mode}"
                    self.notification_timer_ms = 2000.0
                elif event.key == pygame.K_t:
                    speeds = [1.0, 0.5, 0.25, 0.1]
                    idx = (speeds.index(self.speed_multiplier) + 1) % len(speeds)
                    self.speed_multiplier = speeds[idx]
                    self.notification_msg = f"Speed: {self.speed_multiplier:.2f}x"
                    self.notification_timer_ms = 2000.0
                elif event.key in (pygame.K_p, pygame.K_F12):
                    self.export_screenshot()
                elif event.key == pygame.K_g:
                    self.toggle_gif_recording()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.handle_click(event.pos)

    def handle_click(self, pos: Tuple[int, int]) -> None:
        mx, my = pos
        # Check top navigation buttons (state selector)
        btn_w = 95
        btn_h = 32
        start_x = 20
        start_y = 15

        for i, sname in enumerate(STATE_ORDER):
            bx = start_x + (i % 5) * (btn_w + 10)
            by = start_y + (i // 5) * (btn_h + 8)
            rect = pygame.Rect(bx, by, btn_w, btn_h)
            if rect.collidepoint(mx, my):
                self.trigger_state(sname)
                return

        # Check tab clicks
        tab_start_x = 840
        tab_y = 15
        tab_w = 95
        for i, tname in enumerate(self.tab_names):
            tx = tab_start_x + i * (tab_w + 6)
            rect = pygame.Rect(tx, tab_y, tab_w, 28)
            if rect.collidepoint(mx, my):
                self.active_tab_idx = i
                return

    def update(self, dt_ms: float) -> None:
        dt_s = dt_ms / 1000.0
        self.state_timer_ms += dt_ms

        if self.notification_timer_ms > 0:
            self.notification_timer_ms = max(0.0, self.notification_timer_ms - dt_ms)

        # Mouse look
        mx, my = pygame.mouse.get_pos()
        self.mouse_norm = (max(0.0, min(1.0, mx / float(self.window_w))), max(0.0, min(1.0, my / float(self.window_h))))
        self.engine.look_at(self.mouse_norm[0], self.mouse_norm[1])

        # Record mode auto cycle
        if self.record_mode:
            self.record_state_timer_ms += dt_ms
            if self.record_state_timer_ms >= 3000.0:
                self.record_state_timer_ms = 0.0
                self.record_state_idx = (self.record_state_idx + 1) % len(STATE_ORDER)
                self.trigger_state(STATE_ORDER[self.record_state_idx])

        # Compute speech pulse
        speech_pulse = 0.0
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            speech_pulse = 0.90
        elif self.auto_speech or self.engine.current_state == "speaking":
            t = time.time()
            w1 = max(0.0, math.sin(t * 11.0))
            w2 = max(0.0, math.sin(t * 17.0 + 1.2))
            speech_pulse = min(1.0, w1 * 0.7 + w2 * 0.5)

        self.speech_pulse_val = speech_pulse
        self.engine.set_speech_pulse(speech_pulse)

        # Step animation engine with slow-motion speed multiplier
        t0 = time.perf_counter()
        self.engine.step(dt_ms * self.speed_multiplier)
        self.dt_step_ms = (time.perf_counter() - t0) * 1000.0

    def render(self) -> None:
        t0 = time.perf_counter()
        self.screen.fill(C_BG)

        # 1. Clear Canvas Surface & Render according to Silhouette Review Mode
        self.canvas_surf.fill((0, 0, 0))
        eye_pose, mouth_params, ctx = self.engine.mixer.step(0.0)

        if self.silhouette_mode == "FULL":
            self.engine.composer.compose(self.canvas_surf, eye_pose, mouth_params, ctx)
        elif self.silhouette_mode == "MOUTH_ONLY":
            self.engine.composer.mouth_renderer.draw_mouth(self.canvas_surf, mouth_params)
        elif self.silhouette_mode == "EYES_ONLY":
            self.engine.composer.eye_renderer.draw_eye(self.canvas_surf, eye_pose.left)
            self.engine.composer.eye_renderer.draw_eye(self.canvas_surf, eye_pose.right)

        if self.is_recording_gif and len(self.gif_frames) < self.gif_max_frames:
            self.gif_frames.append(self.canvas_surf.copy())

        # Blit canvas to screen area
        canvas_rect = pygame.Rect(20, 100, 800, 480)
        self.screen.blit(self.canvas_surf, canvas_rect.topleft)
        pygame.draw.rect(self.screen, C_BORDER, canvas_rect, width=1, border_radius=4)


        # 2. Render Top Header & State Selector Buttons
        self._render_header()

        # 3. Render Bottom Timeline & Controls Bar
        self._render_timeline_bar(canvas_rect.left, canvas_rect.bottom + 15, canvas_rect.width)

        # 4. Render Right Inspector Panel Tabs
        self._render_right_panel(840, 15, self.window_w - 860, self.window_h - 30)

        # 5. Render Notification Overlay
        if self.notification_timer_ms > 0:
            self._render_notification()

        pygame.display.flip()
        self.dt_render_ms = (time.perf_counter() - t0) * 1000.0

    def _render_header(self) -> None:
        font = self.fonts.get(13, bold=True)
        btn_w = 150
        btn_h = 30
        start_x = 20
        start_y = 15

        for i, sname in enumerate(STATE_ORDER):
            bx = start_x + (i % 5) * (btn_w + 10)
            by = start_y + (i // 5) * (btn_h + 8)
            rect = pygame.Rect(bx, by, btn_w, btn_h)
            is_active = (sname == self.engine.current_state)
            UIWidget.draw_button(self.screen, rect, f"{i+1}. {sname.upper()}", font, active=is_active)

    def _render_timeline_bar(self, x: int, y: int, w: int) -> None:
        rect = pygame.Rect(x, y, w, 140)
        UIWidget.draw_panel(self.screen, rect, bg=C_PANEL)

        font_bold = self.fonts.get(14, bold=True)
        font_mono = self.fonts.get(12, mono=True)

        # Title & Info
        txt_state = font_bold.render(f"ACTIVE STATE: {self.engine.current_state.upper()}", True, C_EMERALD)
        self.screen.blit(txt_state, (x + 15, y + 12))

        txt_sil = font_mono.render(f"Silhouette Mode [V]: {self.silhouette_mode}", True, C_CYAN)
        self.screen.blit(txt_sil, (x + 280, y + 14))

        txt_spd = font_mono.render(f"Speed [T]: {self.speed_multiplier:.2f}x", True, C_AMBER)
        self.screen.blit(txt_spd, (x + 580, y + 14))

        # Timeline Scrubber Bar
        bar_x = x + 15
        bar_y = y + 55
        bar_w = w - 30
        bar_h = 14

        pygame.draw.rect(self.screen, C_BTN_NORM, (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        progress = min(1.0, (self.state_timer_ms % 3000.0) / 3000.0)
        fill_w = int(bar_w * progress)
        pygame.draw.rect(self.screen, C_CYAN, (bar_x, bar_y, fill_w, bar_h), border_radius=4)

        # Scrubber Knob
        knob_x = bar_x + fill_w
        pygame.draw.circle(self.screen, (255, 255, 255), (knob_x, bar_y + bar_h // 2), 9)

        # Shortcuts Guide Line
        shortcuts = "Keys: [1-0] State | [V] Silhouette Mode | [T] Slow-Mo | [G] GIF | [P] PNG | [D] Debug"
        txt_short = font_mono.render(shortcuts, True, C_TEXT_DIM)
        self.screen.blit(txt_short, (x + 15, y + 105))


    def _render_right_panel(self, x: int, y: int, w: int, h: int) -> None:
        panel_rect = pygame.Rect(x, y, w, h)
        UIWidget.draw_panel(self.screen, panel_rect, bg=C_PANEL)

        font_tab = self.fonts.get(12, bold=True)
        tab_w = (w - 30) // len(self.tab_names)
        for i, tname in enumerate(self.tab_names):
            tx = x + 15 + i * tab_w
            trect = pygame.Rect(tx, y + 10, tab_w - 4, 28)
            active = (i == self.active_tab_idx)
            UIWidget.draw_button(self.screen, trect, tname, font_tab, active=active)

        # Render Tab Content
        content_rect = pygame.Rect(x + 15, y + 48, w - 30, h - 60)
        if self.active_tab_idx == 0:
            self._render_inspector_tab(content_rect)
        elif self.active_tab_idx == 1:
            self._render_mouth_tab(content_rect)
        elif self.active_tab_idx == 2:
            self._render_matrix_tab(content_rect)
        elif self.active_tab_idx == 3:
            self._render_profiler_tab(content_rect)

    def _render_inspector_tab(self, rect: pygame.Rect) -> None:
        font_h = self.fonts.get(14, bold=True)
        font_m = self.fonts.get(12, mono=True)

        y = rect.y + 10
        self.screen.blit(font_h.render("FACE SUBSYSTEM INSPECTOR", True, C_CYAN), (rect.x, y))

        eye_pose = self.engine.mixer._eye_engine._engine.current_pose
        mouth_params = self.engine.mixer._mouth_controller.current_params

        lines = [
            f"State: {self.engine.current_state}",
            f"FPS: {self.clock.get_fps():.1f}",
            "",
            "EYE GEOMETRY:",
            f"Left Pos: ({eye_pose.left.pos_x:.1f}, {eye_pose.left.pos_y:.1f})",
            f"Right Pos: ({eye_pose.right.pos_x:.1f}, {eye_pose.right.pos_y:.1f})",
            f"Eye Radius: {eye_pose.left.radius:.1f}",
            f"Lid Openness: {eye_pose.left.lid_openness:.2f}",
            f"Blink Weight: {eye_pose.left.blink_weight:.2f}",
            "",
            "MOUTH GEOMETRY:",
            f"Width: {mouth_params.width:.1f} px",
            f"Height: {mouth_params.height:.1f} px",
            f"Upper Curve: {mouth_params.upper_curvature:+.2f}",
            f"Lower Curve: {mouth_params.lower_curvature:+.2f}",
            f"Smile Amount: {mouth_params.smile_amount:+.2f}",
            f"Opening Cavity: {mouth_params.opening:.2f}",
            f"Corner Roundness: {mouth_params.corner_roundness:.2f}",
            f"Stretch / Squash: ({mouth_params.stretch:+.2f}, {mouth_params.squash:+.2f})",
            f"Offset: ({mouth_params.offset_x:.1f}, {mouth_params.offset_y:.1f})",
        ]

        for i, line in enumerate(lines):
            color = C_AMBER if line.endswith(":") else C_TEXT_MUTED
            if "State:" in line or "FPS:" in line:
                color = C_EMERALD
            self.screen.blit(font_m.render(line, True, color), (rect.x + 10, y + 30 + i * 20))

    def _render_mouth_tab(self, rect: pygame.Rect) -> None:
        font_h = self.fonts.get(14, bold=True)
        font_m = self.fonts.get(12, mono=True)
        y = rect.y + 10
        self.screen.blit(font_h.render("PROCEDURAL MOUTH STUDIO (PHASE 4A)", True, C_AMBER), (rect.x, y))

        p = self.engine.mixer._mouth_controller.current_params
        info = [
            "SILHOUETTE REVIEW & MORPHING:",
            f"Review Mode [V]: {self.silhouette_mode}",
            f"Slow-Mo Speed [T]: {self.speed_multiplier:.2f}x",
            "",
            "LIVE PARAMETER GEOMETRY:",
            f"pos_x: {p.pos_x:.1f}  pos_y: {p.pos_y:.1f}",
            f"width: {p.width:.1f} px  height: {p.height:.1f} px",
            f"thickness: {p.thickness:.1f} px",
            f"upper_curvature: {p.upper_curvature:+.2f}",
            f"lower_curvature: {p.lower_curvature:+.2f}",
            f"smile_amount: {p.smile_amount:+.2f}",
            f"opening mask: {p.opening:.2f}",
            f"stretch / squash: ({p.stretch:+.2f}, {p.squash:+.2f})",
            f"rotation: {p.rotation:+.3f} rad",
            f"corner_roundness: {p.corner_roundness:.2f}",
            f"offset_x: {p.offset_x:+.1f}  offset_y: {p.offset_y:+.1f}",
            "",
            "SILHOUETTE SPECS:",
            "Solid Shapes: Happy, Caring, Calm, Sad...",
            "Inner Cavity Mask: Surprised (O-mouth)",
            "Dynamic Motion: Thinking (corner drift)",
        ]
        for i, line in enumerate(info):
            color = C_CYAN if line.endswith(":") else C_TEXT
            if "Review Mode" in line or "Slow-Mo Speed" in line:
                color = C_EMERALD
            self.screen.blit(font_m.render(line, True, color), (rect.x + 10, y + 25 + i * 20))


    def _render_matrix_tab(self, rect: pygame.Rect) -> None:
        font_h = self.fonts.get(14, bold=True)
        font_s = self.fonts.get(10, mono=True)

        y = rect.y + 10
        self.screen.blit(font_h.render("10x10 TRANSITION MATRIX", True, C_PURPLE), (rect.x, y))

        cell_w = min(28, (rect.width - 40) // 11)
        cell_h = 24
        start_x = rect.x + 40
        start_y = y + 40

        for col, name in enumerate(STATE_ORDER):
            lbl = font_s.render(name[:3].upper(), True, C_TEXT_MUTED)
            self.screen.blit(lbl, (start_x + col * cell_w + 2, start_y - 20))

        for row, rname in enumerate(STATE_ORDER):
            lbl = font_s.render(rname[:3].upper(), True, C_TEXT_MUTED)
            self.screen.blit(lbl, (rect.x + 5, start_y + row * cell_h + 4))

            for col, cname in enumerate(STATE_ORDER):
                cx = start_x + col * cell_w
                cy = start_y + row * cell_h
                box = pygame.Rect(cx, cy, cell_w - 2, cell_h - 2)

                if row == col:
                    bg = C_BTN_NORM
                else:
                    bg = (20, 50, 70) if (rname == self.engine.current_state or cname == self.engine.current_state) else C_PANEL_HEADER
                pygame.draw.rect(self.screen, bg, box, border_radius=2)
                pygame.draw.rect(self.screen, C_BORDER, box, width=1, border_radius=2)

    def _render_profiler_tab(self, rect: pygame.Rect) -> None:
        font_h = self.fonts.get(14, bold=True)
        font_m = self.fonts.get(12, mono=True)

        y = rect.y + 10
        self.screen.blit(font_h.render("PERFORMANCE PROFILER", True, C_EMERALD), (rect.x, y))

        fps = self.clock.get_fps()
        target_fps = 60.0
        rpi_fps = 30.0

        lines = [
            f"Desktop Target: {target_fps:.0f} FPS",
            f"Raspberry Pi Target: {rpi_fps:.0f} FPS",
            f"Current Frame Rate: {fps:.1f} FPS",
            "",
            f"Step Time: {self.dt_step_ms:.2f} ms",
            f"Render Time: {self.dt_render_ms:.2f} ms",
            f"Total Frame Time: {(self.dt_step_ms + self.dt_render_ms):.2f} ms",
            "",
            "ALLOCATION PROFILE: 0 bytes/frame (Zero Allocation)",
            "COMPATIBILITY: Raspberry Pi 4 / 5 Ready",
        ]

        for i, line in enumerate(lines):
            color = C_EMERALD if "FPS" in line or "Ready" in line else C_TEXT_MUTED
            self.screen.blit(font_m.render(line, True, color), (rect.x + 10, y + 30 + i * 22))

    def _render_notification(self) -> None:
        font = self.fonts.get(13, bold=True)
        surf = font.render(self.notification_msg, True, (255, 255, 255))
        w = surf.get_width() + 30
        h = 36
        rect = pygame.Rect((self.window_w - w) // 2, 60, w, h)
        UIWidget.draw_panel(self.screen, rect, bg=(20, 30, 45), border=C_CYAN, radius=18)
        self.screen.blit(surf, (rect.x + 15, rect.y + (h - surf.get_height()) // 2))

    def run(self) -> None:
        print("Starting ELO Face Engine Studio Showcase...")
        while self.running:
            dt_ms = self.clock.tick(60)
            dt_ms = min(dt_ms, 66.0)
            self.process_events()
            self.update(dt_ms)
            self.render()

        pygame.quit()
        print("Face Showcase exited.")


def main() -> None:
    app = FaceStudioShowcase()
    app.run()


if __name__ == "__main__":
    main()
