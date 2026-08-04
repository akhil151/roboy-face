"""
Professional Animation Studio & Interactive Showcase for ELO Robot Eye Engine.

This application wraps the ELO Eye Animation Engine without modifying any engine,
renderer, or state architecture code.

Key Features & Shortcuts:
    1-9/0    Direct state selection (Calm, Listening, Thinking, Speaking, Happy, Caring, Sad, Sleepy, Surprised, Focus)
    SPACE    Replay Enter Animation
    TAB      Toggle Loop Only vs Full Performance (Enter -> Hold -> Loop -> Exit)
    ENTER    Auto-cycle through all emotions
    LEFT/RIGHT ARROW  Previous / Next emotion
    MOUSE    Move cursor to drive look_at()
    S        Toggle simulated Speech Pulse
    B        Force Blink
    D        Toggle Debug Overlay / Parameter Inspector
    T        Toggle Transition Preview Mode (Loops FROM -> TO transition)
    C        Toggle Split-Screen Comparison Mode (Current vs Previous)
    R        Toggle Record Mode (Showcase all emotions 5s each)
    G        Toggle Ghost Pose Overlay
    M        Toggle 10x10 Transition Matrix Viewer
    P / F12  Export Screenshot PNG
    [ / ]    Slow-motion decrease / increase or Frame Step (when paused)
    ESC      Exit Application
"""

from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pygame

# Ensure repository root is in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
EYES_DIR = Path(__file__).resolve().parent
if str(EYES_DIR) not in sys.path:
    sys.path.insert(0, str(EYES_DIR))

from eyes import EyeEngine, VALID_STATES
from eyes.engine.eye_pair import EyePair
from eyes.engine.config import EngineConfig

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Constants & Colors (Dark Editor Theme)
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

# Theme Palette
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
    """Manages cached fonts for smooth UI rendering."""

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
# Animation Studio Showcase Core Application
# ---------------------------------------------------------------------------

class AnimationStudioShowcase:
    def __init__(self) -> None:
        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()

        self.exports_dir = EYES_DIR / "exports"
        self.screenshots_dir = self.exports_dir / "screenshots"
        self.gifs_dir = self.exports_dir / "gifs"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.gifs_dir.mkdir(parents=True, exist_ok=True)

        # Main Animation Engine (Primary)
        self.engine = EyeEngine()
        self.cfg: EngineConfig = self.engine._engine.config

        # Secondary Engine for Comparison Mode
        self.compare_engine = EyeEngine()

        self.fonts = FontManager()

        # Display Setup
        self.window_w = 1280
        self.window_h = 768
        self.screen = pygame.display.set_mode(
            (self.window_w, self.window_h), pygame.RESIZABLE
        )
        pygame.display.set_caption("ELO Robot Eyes - Animation Studio & Showcase")

        # Application State
        self.running = True
        self.current_state_idx = 0
        self.previous_state_name = "calm"
        self.state_timer_ms = 0.0

        # Operational Modes
        self.is_paused = False
        self.loop_only_mode = False          # False = Full Performance, True = Loop Only
        self.auto_cycle_mode = False        # ENTER key toggle
        self.speech_pulse_enabled = False   # S key toggle
        self.speech_pulse_val = 0.0
        self.debug_overlay_enabled = True   # D key toggle
        self.ghost_overlay_enabled = False  # G key toggle
        self.transition_matrix_enabled = False  # M key toggle

        # Special Modes
        self.transition_preview_mode = False  # T key
        self.preview_from_state = "happy"
        self.preview_to_state = "caring"
        self.preview_phase = 0              # 0 = FROM hold, 1 = Transition, 2 = TO hold, 3 = Transition back
        self.preview_phase_timer_ms = 0.0

        self.comparison_mode = False         # C key
        self.record_mode = False             # R key
        self.record_state_timer_ms = 0.0
        self.record_state_idx = 0

        # Playback Controls
        self.playback_speed = 1.0            # 0.25x, 0.5x, 1.0x, 2.0x
        self.speed_options = [0.25, 0.5, 1.0, 2.0]

        # Recording / GIF Export
        self.is_recording_gif = False
        self.gif_frames: List[pygame.Surface] = []
        self.gif_max_frames = 90
        self.notification_msg = ""
        self.notification_timer_ms = 0.0

        # Ghost Pose Storage
        self.ghost_pose: Optional[EyePair] = None

        # Sidebar Tabs: 0=Inspector, 1=Docs, 2=Matrix, 3=Profiler, 4=Snapshots
        self.active_tab_idx = 0
        self.tab_names = ["Inspector", "Docs", "Matrix", "Profiler", "Snapshots"]

        # Pose Snapshots
        self.snapshots: List[Dict] = []

        # Interactive Parameter Editing Overrides
        self.param_overrides: Dict[str, float] = {}

        # Timing / Profiling Telemetry
        self.clock = pygame.time.Clock()
        self.fps_smooth = float(self.cfg.display.fps)
        self.dt_step_ms = 0.0
        self.dt_render_ms = 0.0
        self.mouse_norm = (0.5, 0.5)

        # Timeline Scrubber Interactivity
        self.timeline_dragging = False

    # -----------------------------------------------------------------------
    # Public State Trigger
    # -----------------------------------------------------------------------

    def trigger_state(self, state_name: str) -> None:
        if state_name not in STATE_ORDER:
            return
        if self.engine.current_state != state_name:
            self.previous_state_name = self.engine.current_state
            self.ghost_pose = self.engine._engine.current_pose.copy()

        self.current_state_idx = STATE_ORDER.index(state_name)
        self.state_timer_ms = 0.0

        if self.loop_only_mode:
            # Loop Only: immediate jump to state loop without enter transition
            state_obj = self.engine._engine.state_machine.get_state(state_name)
            if state_obj is not None:
                self.engine._engine.mixer.set_state_immediate(state_obj)
        else:
            # Full Performance: Enter -> Hold -> Loop -> Exit
            self.engine.set_state(state_name)

        if self.comparison_mode:
            self.compare_engine.set_state(self.previous_state_name)

    def trigger_replay_enter(self) -> None:
        """Replay the Enter animation for the currently active state."""
        current_name = self.engine.current_state
        state_obj = self.engine._engine.state_machine.get_state(current_name)
        if state_obj is not None:
            self.engine._engine.mixer.transition_to(state_obj, duration_ms=self.cfg.timing.state_transition_ms)

    def show_notification(self, msg: str, duration_s: float = 3.0) -> None:
        self.notification_msg = msg
        self.notification_timer_ms = duration_s * 1000.0

    # -----------------------------------------------------------------------
    # Main Event Loop
    # -----------------------------------------------------------------------

    def handle_events(self) -> None:
        disp_w, disp_h = self.screen.get_size()
        self.window_w, self.window_h = disp_w, disp_h

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                break

            elif event.type == pygame.VIDEORESIZE:
                self.window_w, self.window_h = event.w, event.h
                self.screen = pygame.display.set_mode(
                    (self.window_w, self.window_h), pygame.RESIZABLE
                )

            elif event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                self.mouse_norm = (
                    max(0.0, min(1.0, mx / max(1, disp_w))),
                    max(0.0, min(1.0, my / max(1, disp_h))),
                )
                self.engine.look_at(self.mouse_norm[0], self.mouse_norm[1])
                if self.comparison_mode:
                    self.compare_engine.look_at(self.mouse_norm[0], self.mouse_norm[1])

                if self.timeline_dragging:
                    self._scrub_timeline(mx)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if event.button == 1:
                    self.handle_mouse_click(mx, my)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.timeline_dragging = False

            elif event.type == pygame.KEYDOWN:
                self.handle_key_down(event.key)

    def handle_key_down(self, key: int) -> None:
        # State Selection Keys 1..9 and 0
        if key in KEY_STATE_MAP:
            target_state = KEY_STATE_MAP[key]
            self.trigger_state(target_state)
            return

        if key == pygame.K_ESCAPE:
            self.running = False

        elif key == pygame.K_SPACE:
            # Replay Enter Animation as specified
            self.trigger_replay_enter()

        elif key == pygame.K_TAB:
            # Toggle Loop Only vs Full Performance
            self.loop_only_mode = not self.loop_only_mode
            mode_desc = "Loop Only" if self.loop_only_mode else "Full Performance (Enter -> Hold -> Loop -> Exit)"
            self.show_notification(f"Playback Mode: {mode_desc}")

        elif key == pygame.K_RETURN:
            # ENTER: Toggle Auto-cycle through all emotions
            self.auto_cycle_mode = not self.auto_cycle_mode
            self.show_notification(f"Auto Cycle Mode: {'ON' if self.auto_cycle_mode else 'OFF'}")

        elif key == pygame.K_LEFT:
            # Previous Emotion
            next_idx = (self.current_state_idx - 1) % len(STATE_ORDER)
            self.trigger_state(STATE_ORDER[next_idx])

        elif key == pygame.K_RIGHT:
            # Next Emotion
            next_idx = (self.current_state_idx + 1) % len(STATE_ORDER)
            self.trigger_state(STATE_ORDER[next_idx])

        elif key == pygame.K_s:
            # Toggle Speech Pulse Simulation
            self.speech_pulse_enabled = not self.speech_pulse_enabled
            self.show_notification(f"Simulated Speech Pulse: {'ENABLED' if self.speech_pulse_enabled else 'DISABLED'}")

        elif key == pygame.K_b:
            # Force Blink
            self.engine.blink()

        elif key == pygame.K_d:
            # Toggle Debug Overlay
            self.debug_overlay_enabled = not self.debug_overlay_enabled

        elif key == pygame.K_t:
            # Toggle Transition Preview Mode
            self.transition_preview_mode = not self.transition_preview_mode
            self.preview_phase = 0
            self.preview_phase_timer_ms = 0.0
            self.show_notification(f"Transition Preview Mode: {'ON' if self.transition_preview_mode else 'OFF'}")

        elif key == pygame.K_c:
            # Toggle Comparison Mode
            self.comparison_mode = not self.comparison_mode
            if self.comparison_mode:
                self.compare_engine.set_state(self.previous_state_name)
            self.show_notification(f"Comparison Mode: {'ON' if self.comparison_mode else 'OFF'}")

        elif key == pygame.K_r:
            # Toggle Record Mode
            self.record_mode = not self.record_mode
            if self.record_mode:
                self.record_state_idx = 0
                self.record_state_timer_ms = 0.0
                self.trigger_state(STATE_ORDER[0])
            self.show_notification(f"Record Mode: {'ACTIVE' if self.record_mode else 'OFF'}")

        elif key == pygame.K_g:
            # Toggle Ghost Overlay
            self.ghost_overlay_enabled = not self.ghost_overlay_enabled
            self.show_notification(f"Ghost Overlay: {'ON' if self.ghost_overlay_enabled else 'OFF'}")

        elif key == pygame.K_m:
            # Toggle Matrix View
            self.transition_matrix_enabled = not self.transition_matrix_enabled
            if self.transition_matrix_enabled:
                self.active_tab_idx = 2

        elif key == pygame.K_p or key == pygame.K_F12:
            # Export Screenshot PNG
            self.capture_screenshot()

        elif key == pygame.K_LEFTBRACKET:
            # Slow motion decrease or Step Back
            if self.is_paused:
                self._step_frame(-16.6)
            else:
                self._cycle_speed(-1)

        elif key == pygame.K_RIGHTBRACKET:
            # Slow motion increase or Step Forward
            if self.is_paused:
                self._step_frame(16.6)
            else:
                self._cycle_speed(1)

    def _cycle_speed(self, direction: int) -> None:
        curr_idx = self.speed_options.index(self.playback_speed)
        new_idx = max(0, min(len(self.speed_options) - 1, curr_idx + direction))
        self.playback_speed = self.speed_options[new_idx]
        self.show_notification(f"Playback Speed: {self.playback_speed}x")

    def _step_frame(self, dt_ms: float) -> None:
        self.engine._engine.step(abs(dt_ms), self.speech_pulse_val)

    # -----------------------------------------------------------------------
    # Mouse Click Handler (UI Buttons & Panels)
    # -----------------------------------------------------------------------

    def handle_mouse_click(self, mx: int, my: int) -> None:
        # 1. Left Sidebar State Buttons
        sb_w = 180
        sb_y = 60
        btn_h = 32
        for i, sname in enumerate(STATE_ORDER):
            by = sb_y + 40 + i * (btn_h + 6)
            brect = pygame.Rect(12, by, sb_w - 24, btn_h)
            if brect.collidepoint(mx, my):
                self.trigger_state(sname)
                return

        # 2. Right Panel Tabs
        rp_w = 320
        rp_x = self.window_w - rp_w
        if mx >= rp_x and my <= 50:
            tab_w = rp_w // len(self.tab_names)
            t_idx = (mx - rp_x) // tab_w
            if 0 <= t_idx < len(self.tab_names):
                self.active_tab_idx = t_idx
                return

        # 3. Top Toolbar Controls (Play/Pause, Speed, Record, Screenshot, GIF)
        tb_rect = pygame.Rect(sb_w + 10, 10, self.window_w - sb_w - rp_w - 20, 40)
        if tb_rect.collidepoint(mx, my):
            # Play / Pause
            pause_btn = pygame.Rect(tb_rect.x + 10, tb_rect.y + 6, 70, 28)
            if pause_btn.collidepoint(mx, my):
                self.is_paused = not self.is_paused
                self.show_notification("PAUSED" if self.is_paused else "PLAYING")
                return

            # Speed Buttons (0.25, 0.5, 1.0, 2.0)
            sx = pause_btn.right + 15
            for spd in self.speed_options:
                sbtn = pygame.Rect(sx, tb_rect.y + 6, 45, 28)
                if sbtn.collidepoint(mx, my):
                    self.playback_speed = spd
                    self.show_notification(f"Speed: {spd}x")
                    return
                sx += 50

            # PNG Screenshot Button
            pbtn = pygame.Rect(sx + 10, tb_rect.y + 6, 75, 28)
            if pbtn.collidepoint(mx, my):
                self.capture_screenshot()
                return

            # GIF Export Button
            gbtn = pygame.Rect(pbtn.right + 8, tb_rect.y + 6, 75, 28)
            if gbtn.collidepoint(mx, my):
                self.toggle_gif_recording()
                return

        # 4. Timeline Deck Scrubber Bar
        tl_h = 60
        tl_y = self.window_h - tl_h
        if my >= tl_y and mx > sb_w and mx < (self.window_w - rp_w):
            self.timeline_dragging = True
            self._scrub_timeline(mx)

    def _scrub_timeline(self, mx: int) -> None:
        sb_w = 180
        rp_w = 320
        track_x = sb_w + 100
        track_w = self.window_w - sb_w - rp_w - 200
        if track_w > 0:
            rel_x = max(0, min(track_w, mx - track_x))
            frac = rel_x / track_w
            self.state_timer_ms = frac * 4000.0  # 4s timeline span

    # -----------------------------------------------------------------------
    # Screenshot & GIF Export
    # -----------------------------------------------------------------------

    def capture_screenshot(self) -> None:
        ts = time.strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{self.engine.current_state}_{ts}.png"
        filepath = self.screenshots_dir / filename
        pygame.image.save(self.screen, str(filepath))
        self.show_notification(f"Saved Screenshot: {filename}")

    def toggle_gif_recording(self) -> None:
        if not PIL_AVAILABLE:
            self.show_notification("PIL not available for GIF export!")
            return
        if not self.is_recording_gif:
            self.is_recording_gif = True
            self.gif_frames.clear()
            self.show_notification("GIF Recording STARTED...")
        else:
            self.finish_gif_recording()

    def finish_gif_recording(self) -> None:
        if not self.gif_frames:
            self.is_recording_gif = False
            return
        ts = time.strftime("%Y%m%d_%H%M%S")
        filename = f"anim_{self.engine.current_state}_{ts}.gif"
        filepath = self.gifs_dir / filename

        try:
            pil_images = []
            for surf in self.gif_frames:
                data = pygame.image.tostring(surf, "RGB")
                img = Image.frombytes("RGB", surf.get_size(), data)
                pil_images.append(img)
            if pil_images:
                pil_images[0].save(
                    str(filepath),
                    save_all=True,
                    append_images=pil_images[1:],
                    duration=33,
                    loop=0,
                )
                self.show_notification(f"GIF Exported: {filename}")
        except Exception as ex:
            self.show_notification(f"GIF Export Failed: {ex}")
        finally:
            self.is_recording_gif = False
            self.gif_frames.clear()

    # -----------------------------------------------------------------------
    # Simulation & Update Step
    # -----------------------------------------------------------------------

    def update(self, dt_ms: float) -> None:
        if self.notification_timer_ms > 0:
            self.notification_timer_ms -= dt_ms

        if self.is_paused:
            return

        effective_dt = dt_ms * self.playback_speed
        self.state_timer_ms += effective_dt

        # Speech Pulse Synthesis (when S key enabled)
        if self.speech_pulse_enabled:
            t = time.time()
            # Speech envelope modulation
            base_wave = abs(math.sin(t * 12.0))
            envelope = 0.5 + 0.5 * math.sin(t * 3.5)
            self.speech_pulse_val = base_wave * envelope
        else:
            self.speech_pulse_val = 0.0

        # Special Mode: Transition Preview Mode (T)
        if self.transition_preview_mode:
            self._update_transition_preview(effective_dt)
            t_start = time.perf_counter()
            self.engine._engine.step(effective_dt, self.speech_pulse_val)
            self.dt_step_ms = (time.perf_counter() - t_start) * 1000.0
            return

        # Special Mode: Record Mode (R) - 5 seconds per emotion
        if self.record_mode:
            self.record_state_timer_ms += effective_dt
            if self.record_state_timer_ms >= 5000.0:
                self.record_state_timer_ms = 0.0
                self.record_state_idx = (self.record_state_idx + 1) % len(STATE_ORDER)
                self.trigger_state(STATE_ORDER[self.record_state_idx])

        # Special Mode: Auto Cycle Mode (ENTER)
        elif self.auto_cycle_mode:
            if self.state_timer_ms >= 3500.0:
                self.state_timer_ms = 0.0
                next_idx = (self.current_state_idx + 1) % len(STATE_ORDER)
                self.trigger_state(STATE_ORDER[next_idx])

        # Step Engine Simulation
        t_start = time.perf_counter()
        self.engine._engine.step(effective_dt, self.speech_pulse_val)
        self.dt_step_ms = (time.perf_counter() - t_start) * 1000.0

        if self.comparison_mode:
            self.compare_engine._engine.step(effective_dt, self.speech_pulse_val)

        # Apply Live Parameter Inspector Overrides (if set)
        if self.param_overrides:
            pose = self.engine._engine.current_pose
            for key, val in self.param_overrides.items():
                if hasattr(pose.left, key):
                    setattr(pose.left, key, val)
                if hasattr(pose.right, key):
                    setattr(pose.right, key, val)

    def _update_transition_preview(self, dt_ms: float) -> None:
        self.preview_phase_timer_ms += dt_ms
        if self.preview_phase == 0:  # Hold FROM
            if self.preview_phase_timer_ms >= 1200.0:
                self.preview_phase = 1
                self.preview_phase_timer_ms = 0.0
                self.engine.set_state(self.preview_to_state)
        elif self.preview_phase == 1:  # Transitioning to TO
            if not self.engine._engine.mixer.is_blending:
                self.preview_phase = 2
                self.preview_phase_timer_ms = 0.0
        elif self.preview_phase == 2:  # Hold TO
            if self.preview_phase_timer_ms >= 1200.0:
                self.preview_phase = 3
                self.preview_phase_timer_ms = 0.0
                self.engine.set_state(self.preview_from_state)
        elif self.preview_phase == 3:  # Transitioning back to FROM
            if not self.engine._engine.mixer.is_blending:
                self.preview_phase = 0
                self.preview_phase_timer_ms = 0.0

    # -----------------------------------------------------------------------
    # Rendering Pipeline
    # -----------------------------------------------------------------------

    def render(self) -> None:
        t_start = time.perf_counter()
        self.screen.fill(C_BG)

        # Viewport layout bounds
        sb_w = 180
        rp_w = 320
        top_h = 55
        btm_h = 65

        view_rect = pygame.Rect(
            sb_w, top_h, self.window_w - sb_w - rp_w, self.window_h - top_h - btm_h
        )

        # Draw Viewport Canvas
        if self.comparison_mode:
            self._render_comparison_view(view_rect)
        else:
            self._render_single_view(view_rect)

        # Draw Ghost Pose Overlay (G key)
        if self.ghost_overlay_enabled and self.ghost_pose is not None:
            self._render_ghost_overlay(view_rect)

        # Draw Studio UI Layer
        self._render_top_bar(top_h, sb_w, rp_w)
        self._render_left_sidebar(sb_w, top_h, btm_h)
        self._render_right_panel(rp_w, top_h, btm_h)
        self._render_bottom_timeline(btm_h, sb_w, rp_w)

        # Notification Banner
        if self.notification_timer_ms > 0:
            self._render_notification()

        # Capture frame for GIF export
        if self.is_recording_gif and len(self.gif_frames) < self.gif_max_frames:
            self.gif_frames.append(self.screen.copy())
            if len(self.gif_frames) >= self.gif_max_frames:
                self.finish_gif_recording()

        pygame.display.flip()
        self.dt_render_ms = (time.perf_counter() - t_start) * 1000.0

    # -----------------------------------------------------------------------
    # Canvas Viewports Rendering
    # -----------------------------------------------------------------------

    def _render_single_view(self, rect: pygame.Rect) -> None:
        view_surf = pygame.Surface((rect.width, rect.height))
        view_surf.fill((0, 0, 0))

        # Render procedural eyes using renderer onto surface
        self.engine._engine.renderer.render_to_surface(
            view_surf, self.engine._engine.current_pose
        )

        self.screen.blit(view_surf, (rect.x, rect.y))
        pygame.draw.rect(self.screen, C_BORDER, rect, width=1)

    def _render_comparison_view(self, rect: pygame.Rect) -> None:
        half_w = rect.width // 2

        # Left Surface (Current State)
        left_surf = pygame.Surface((half_w, rect.height))
        left_surf.fill((0, 0, 0))
        self.engine._engine.renderer.render_to_surface(
            left_surf, self.engine._engine.current_pose
        )
        self.screen.blit(left_surf, (rect.x, rect.y))

        # Right Surface (Previous State)
        right_surf = pygame.Surface((half_w, rect.height))
        right_surf.fill((0, 0, 0))
        self.compare_engine._engine.renderer.render_to_surface(
            right_surf, self.compare_engine._engine.current_pose
        )
        self.screen.blit(right_surf, (rect.x + half_w, rect.y))

        # Divider & Labels
        pygame.draw.line(
            self.screen, C_CYAN, (rect.x + half_w, rect.y), (rect.x + half_w, rect.bottom), 2
        )
        pygame.draw.rect(self.screen, C_BORDER, rect, width=1)

        font = self.fonts.get(13, bold=True)
        l_label = font.render(f"CURRENT: {self.engine.current_state.upper()}", True, C_CYAN)
        r_label = font.render(f"PREVIOUS: {self.previous_state_name.upper()}", True, C_AMBER)
        self.screen.blit(l_label, (rect.x + 10, rect.y + 10))
        self.screen.blit(r_label, (rect.x + half_w + 10, rect.y + 10))

    def _render_ghost_overlay(self, rect: pygame.Rect) -> None:
        ghost_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        ghost_surf.fill((0, 0, 0, 0))
        temp_surf = pygame.Surface((rect.width, rect.height))
        temp_surf.fill((0, 0, 0))

        self.engine._engine.renderer.render_to_surface(temp_surf, self.ghost_pose)
        temp_surf.set_alpha(90)
        ghost_surf.blit(temp_surf, (0, 0))

        self.screen.blit(ghost_surf, (rect.x, rect.y))
        font = self.fonts.get(11, bold=True)
        g_lbl = font.render("GHOST OVERLAY", True, C_PURPLE)
        self.screen.blit(g_lbl, (rect.x + rect.width - 110, rect.y + 10))

    # -----------------------------------------------------------------------
    # HUD & Panels Rendering
    # -----------------------------------------------------------------------

    def _render_top_bar(self, top_h: int, sb_w: int, rp_w: int) -> None:
        rect = pygame.Rect(0, 0, self.window_w, top_h)
        UIWidget.draw_panel(self.screen, rect, bg=C_PANEL_HEADER, radius=0)

        # Title
        f_title = self.fonts.get(15, bold=True)
        t_surf = f_title.render("ELO ROBOT EYES - ANIMATION STUDIO", True, C_TEXT)
        self.screen.blit(t_surf, (15, 16))

        # Top Bar HUD Items
        f_hud = self.fonts.get(12, bold=True, mono=True)

        state_str = f"EMOTION: {self.engine.current_state.upper()}"
        stage_str = f"STAGE: {self._get_current_timeline_stage()}"
        tr_str = f"TRANSITION: {self._get_transition_info()}"
        fps_str = f"FPS: {self.fps_smooth:.1f}"
        pulse_str = f"PULSE: {'ON (' + f'{self.speech_pulse_val:.2f}' + ')' if self.speech_pulse_enabled else 'OFF'}"

        hx = sb_w + 10
        for item, col in [
            (state_str, C_CYAN),
            (stage_str, C_EMERALD),
            (tr_str, C_AMBER),
            (fps_str, C_TEXT),
            (pulse_str, C_ROSE if self.speech_pulse_enabled else C_TEXT_MUTED),
        ]:
            isurf = f_hud.render(item, True, col)
            self.screen.blit(isurf, (hx, 18))
            hx += isurf.get_width() + 18

    def _render_left_sidebar(self, sb_w: int, top_h: int, btm_h: int) -> None:
        rect = pygame.Rect(0, top_h, sb_w, self.window_h - top_h - btm_h)
        UIWidget.draw_panel(self.screen, rect, radius=0)

        f_hdr = self.fonts.get(12, bold=True)
        h_surf = f_hdr.render("EMOTIONS (1-0)", True, C_TEXT_MUTED)
        self.screen.blit(h_surf, (12, top_h + 12))

        btn_h = 30
        f_btn = self.fonts.get(13)
        mx, my = pygame.mouse.get_pos()

        for i, sname in enumerate(STATE_ORDER):
            by = top_h + 38 + i * (btn_h + 5)
            brect = pygame.Rect(10, by, sb_w - 20, btn_h)
            is_active = self.engine.current_state == sname
            is_hover = brect.collidepoint(mx, my)

            label = f"{ (i+1)%10 }. {sname.capitalize()}"
            UIWidget.draw_button(
                self.screen, brect, label, f_btn, active=is_active, hover=is_hover, accent=C_CYAN
            )

    def _render_right_panel(self, rp_w: int, top_h: int, btm_h: int) -> None:
        rp_x = self.window_w - rp_w
        rect = pygame.Rect(rp_x, top_h, rp_w, self.window_h - top_h - btm_h)
        UIWidget.draw_panel(self.screen, rect, radius=0)

        # Tab Header Bar
        tab_w = rp_w // len(self.tab_names)
        f_tab = self.fonts.get(11, bold=True)

        for i, tname in enumerate(self.tab_names):
            t_rect = pygame.Rect(rp_x + i * tab_w, top_h, tab_w, 32)
            is_sel = i == self.active_tab_idx
            bg = C_PANEL if is_sel else C_BTN_NORM
            border = C_CYAN if is_sel else C_BORDER
            pygame.draw.rect(self.screen, bg, t_rect)
            pygame.draw.rect(self.screen, border, t_rect, width=1)
            tsurf = f_tab.render(tname, True, C_CYAN if is_sel else C_TEXT_MUTED)
            self.screen.blit(
                tsurf,
                (
                    t_rect.x + (t_rect.width - tsurf.get_width()) // 2,
                    t_rect.y + (t_rect.height - tsurf.get_height()) // 2,
                ),
            )

        # Tab Content Area
        content_rect = pygame.Rect(rp_x + 10, top_h + 40, rp_w - 20, rect.height - 50)
        if self.active_tab_idx == 0:
            self._render_inspector_tab(content_rect)
        elif self.active_tab_idx == 1:
            self._render_docs_tab(content_rect)
        elif self.active_tab_idx == 2:
            self._render_matrix_tab(content_rect)
        elif self.active_tab_idx == 3:
            self._render_profiler_tab(content_rect)
        elif self.active_tab_idx == 4:
            self._render_snapshots_tab(content_rect)

    # -----------------------------------------------------------------------
    # Tab Content Panels
    # -----------------------------------------------------------------------

    def _render_inspector_tab(self, rect: pygame.Rect) -> None:
        pose = self.engine._engine.current_pose
        f_font = self.fonts.get(11, mono=True)

        lines = [
            f"=== POSE PARAMETERS ===",
            f"Left Radius:   {pose.left.radius:.2f}",
            f"Right Radius:  {pose.right.radius:.2f}",
            f"Scale X:       {pose.left.scale_x:.3f}",
            f"Scale Y:       {pose.left.scale_y:.3f}",
            f"Rotation:      {pose.left.rotation:.2f} deg",
            f"Lid Openness:  {pose.left.lid_openness:.3f}",
            f"Blink Weight:  {pose.left.blink_weight:.3f}",
            f"Upper Lid Curv:{pose.left.upper_lid_curvature:.3f}",
            f"Lower Lid Curv:{pose.left.lower_lid_curvature:.3f}",
            f"Look Offset X: {pose.left.look_offset_x:.2f}",
            f"Look Offset Y: {pose.left.look_offset_y:.2f}",
            f"Bounce Y:      {pose.left.bounce_offset_y:.2f}",
            f"Stretch:       {pose.left.stretch:.3f}",
            f"Squash:        {pose.left.squash:.3f}",
            f"Micro Offset X:{pose.left.micro_offset_x:.2f}",
            f"Micro Offset Y:{pose.left.micro_offset_y:.2f}",
            f"Speech Pulse:  {self.speech_pulse_val:.3f}",
            f"Blend Progress:{self.engine._engine.mixer.blend_progress*100:.1f}%",
        ]

        for i, line in enumerate(lines):
            col = C_CYAN if line.startswith("===") else C_TEXT
            lsurf = f_font.render(line, True, col)
            self.screen.blit(lsurf, (rect.x, rect.y + i * 19))

    def _render_docs_tab(self, rect: pygame.Rect) -> None:
        current_name = self.engine.current_state
        state_obj = self.engine._engine.state_machine.get_state(current_name)

        f_hdr = self.fonts.get(13, bold=True)
        f_txt = self.fonts.get(11)

        self.screen.blit(f_hdr.render(f"STATE: {current_name.upper()}", True, C_CYAN), (rect.x, rect.y))

        if hasattr(state_obj, "direction"):
            d = state_obj.direction
            doc_lines = [
                f"Goal: {d.emotion_goal}",
                f"Viewer: {d.viewer_response}",
                f"Motion: {d.signature_motion}",
                f"Attention: {d.attention_style}",
                f"Interaction: {d.interaction_style}",
                f"Energy: {d.energy:.2f} | Warmth: {d.warmth:.2f}",
                f"Calmness: {d.calmness:.2f}",
                f"Enter Dur: {d.enter_duration:.0f}ms",
                f"Exit Dur:  {d.exit_duration:.0f}ms",
            ]
            for i, line in enumerate(doc_lines):
                lsurf = f_txt.render(line, True, C_TEXT_MUTED)
                self.screen.blit(lsurf, (rect.x, rect.y + 26 + i * 20))
        else:
            self.screen.blit(f_txt.render("No direction metadata available.", True, C_TEXT_DIM), (rect.x, rect.y + 30))

    def _render_matrix_tab(self, rect: pygame.Rect) -> None:
        f_lbl = self.fonts.get(10, mono=True)
        f_title = self.fonts.get(12, bold=True)
        self.screen.blit(f_title.render("10x10 TRANSITION MATRIX", True, C_AMBER), (rect.x, rect.y))

        mx, my = pygame.mouse.get_pos()
        cell_size = 24
        grid_x = rect.x + 30
        grid_y = rect.y + 30

        # Draw Grid
        for r, from_s in enumerate(STATE_ORDER):
            # Row header
            self.screen.blit(f_lbl.render(from_s[:3].upper(), True, C_TEXT_MUTED), (rect.x, grid_y + r * cell_size + 4))
            for c, to_s in enumerate(STATE_ORDER):
                if r == 0:
                    # Col header
                    self.screen.blit(f_lbl.render(to_s[:3].upper(), True, C_TEXT_MUTED), (grid_x + c * cell_size + 2, rect.y + 15))

                crect = pygame.Rect(grid_x + c * cell_size, grid_y + r * cell_size, cell_size - 2, cell_size - 2)
                is_same = r == c
                is_hover = crect.collidepoint(mx, my)

                bg = C_CYAN if (self.engine.current_state == to_s and self.previous_state_name == from_s) else (C_BTN_HOVER if is_hover else (C_PANEL_HEADER if is_same else C_BTN_NORM))
                pygame.draw.rect(self.screen, bg, crect, border_radius=2)
                pygame.draw.rect(self.screen, C_BORDER, crect, width=1, border_radius=2)

                if is_hover and pygame.mouse.get_pressed()[0]:
                    self.previous_state_name = from_s
                    self.trigger_state(to_s)

    def _render_profiler_tab(self, rect: pygame.Rect) -> None:
        f_mono = self.fonts.get(11, mono=True)
        lines = [
            "=== PERFORMANCE PROFILER ===",
            f"FPS (Smoothed):   {self.fps_smooth:6.1f}",
            f"Step Time:        {self.dt_step_ms:6.2f} ms",
            f"Render Time:      {self.dt_render_ms:6.2f} ms",
            f"Total Frame Time: {self.dt_step_ms + self.dt_render_ms:6.2f} ms",
            f"Target Budget:    {1000.0/self.cfg.display.fps:6.2f} ms",
            "",
            "=== LAYER WEIGHT TELEMETRY ===",
            f"Blink Layer W:    {self.engine._engine.mixer.layer_weights.blink:.3f}",
            f"Look Offsets:     ({self.engine._engine.mixer.layer_weights.look[0]:.2f}, {self.engine._engine.mixer.layer_weights.look[1]:.2f})",
            f"Micro Offsets:    ({self.engine._engine.mixer.layer_weights.micro[0]:.2f}, {self.engine._engine.mixer.layer_weights.micro[1]:.2f})",
            f"Speech Pulse:     {self.speech_pulse_val:.3f}",
        ]
        for i, line in enumerate(lines):
            col = C_EMERALD if line.startswith("===") else C_TEXT
            self.screen.blit(f_mono.render(line, True, col), (rect.x, rect.y + i * 19))

    def _render_snapshots_tab(self, rect: pygame.Rect) -> None:
        f_btn = self.fonts.get(12)
        f_mono = self.fonts.get(10, mono=True)

        cap_rect = pygame.Rect(rect.x, rect.y, rect.width, 28)
        mx, my = pygame.mouse.get_pos()
        is_hover = cap_rect.collidepoint(mx, my)

        if UIWidget.draw_button(self.screen, cap_rect, "+ Capture Pose Snapshot", f_btn, hover=is_hover, accent=C_EMERALD):
            if pygame.mouse.get_pressed()[0]:
                snap = {
                    "state": self.engine.current_state,
                    "time": time.time(),
                    "pose": self.engine._engine.current_pose.copy(),
                }
                self.snapshots.append(snap)
                self.show_notification("Captured Pose Snapshot!")

        y_off = 38
        for i, snap in enumerate(self.snapshots[-8:]):
            s_line = f"#{i+1} [{snap['state'].upper()}] - {time.strftime('%H:%M:%S', time.localtime(snap['time']))}"
            self.screen.blit(f_mono.render(s_line, True, C_TEXT_MUTED), (rect.x, rect.y + y_off))
            y_off += 18

    # -----------------------------------------------------------------------
    # Timeline Deck Rendering
    # -----------------------------------------------------------------------

    def _render_bottom_timeline(self, btm_h: int, sb_w: int, rp_w: int) -> None:
        rect = pygame.Rect(sb_w, self.window_h - btm_h, self.window_w - sb_w - rp_w, btm_h)
        UIWidget.draw_panel(self.screen, rect, radius=0)

        # Stages: ENTER -> HOLD -> LOOP -> EXIT
        stages = ["ENTER", "HOLD", "LOOP", "EXIT"]
        curr_stage = self._get_current_timeline_stage()

        sw = (rect.width - 200) // len(stages)
        sx = rect.x + 20
        f_stg = self.fonts.get(11, bold=True)

        for i, stg in enumerate(stages):
            is_active = stg == curr_stage
            stg_rect = pygame.Rect(sx + i * (sw + 8), rect.y + 12, sw, 24)
            bg = C_EMERALD if is_active else C_PANEL_HEADER
            border = C_EMERALD if is_active else C_BORDER
            pygame.draw.rect(self.screen, bg, stg_rect, border_radius=3)
            pygame.draw.rect(self.screen, border, stg_rect, width=1, border_radius=3)

            tcolor = (0, 0, 0) if is_active else C_TEXT_MUTED
            tsurf = f_stg.render(stg, True, tcolor)
            self.screen.blit(tsurf, (stg_rect.x + (sw - tsurf.get_width()) // 2, stg_rect.y + 4))

        # Scrubber Track
        track_x = rect.x + 100
        track_w = rect.width - 200
        track_y = rect.y + 44
        pygame.draw.line(self.screen, C_BORDER, (track_x, track_y), (track_x + track_w, track_y), 4)

        # Scrubber Playhead Cursor
        progress_frac = min(1.0, (self.state_timer_ms % 4000.0) / 4000.0)
        head_x = track_x + int(progress_frac * track_w)
        pygame.draw.circle(self.screen, C_CYAN, (head_x, track_y), 6)

        # Keybind Hint Bar
        f_hint = self.fonts.get(10)
        hint_txt = "1-0: State | SPACE: Replay Enter | TAB: Mode | ENTER: Auto Cycle | S: Speech Pulse | B: Blink | D: Debug | T: Transition | C: Compare | R: Record | P: PNG"
        self.screen.blit(f_hint.render(hint_txt, True, C_TEXT_DIM), (rect.x + 10, rect.y + rect.height - 14))

    def _get_current_timeline_stage(self) -> str:
        if self.engine._engine.mixer.is_blending:
            p = self.engine._engine.mixer.blend_progress
            return "ENTER" if p < 0.5 else "HOLD"
        return "LOOP"

    def _get_transition_info(self) -> str:
        if self.engine._engine.mixer.is_blending:
            p = self.engine._engine.mixer.blend_progress
            return f"{self.previous_state_name.upper()} -> {self.engine.current_state.upper()} ({int(p*100)}%)"
        return "NONE"

    def _render_notification(self) -> None:
        f_notif = self.fonts.get(12, bold=True)
        nsurf = f_notif.render(self.notification_msg, True, (0, 0, 0))
        nw, nh = nsurf.get_width() + 20, nsurf.get_height() + 10
        nx = (self.window_w - nw) // 2
        ny = 65

        nrect = pygame.Rect(nx, ny, nw, nh)
        pygame.draw.rect(self.screen, C_AMBER, nrect, border_radius=4)
        self.screen.blit(nsurf, (nx + 10, ny + 5))

    # -----------------------------------------------------------------------
    # Main Application Run Loop
    # -----------------------------------------------------------------------

    def run(self) -> int:
        print("Starting ELO Robot Eyes - Animation Studio & Showcase...")
        target_fps = self.cfg.display.fps

        while self.running:
            self.handle_events()
            dt_ms = self.clock.tick(target_fps)
            dt_ms = min(dt_ms, 66.0)

            # FPS Smoothing
            fps_meas = 1000.0 / max(1.0, dt_ms)
            self.fps_smooth += (fps_meas - self.fps_smooth) * 0.08

            self.update(dt_ms)
            self.render()

        pygame.quit()
        print("Animation Studio Showcase exited.")
        return 0


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main() -> int:
    app = AnimationStudioShowcase()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
