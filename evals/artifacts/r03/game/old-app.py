"""A native Pygame orbital flight scene with a keyboard/controller pause menu."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

ROOT = Path(__file__).resolve().parent
W, H = 1440, 900
INK = (7, 16, 25)
WHITE = (229, 237, 234)
MUTED = (151, 166, 176)
MINT = (192, 233, 221)
RULE = (68, 88, 101)


class Flight:
    def __init__(self, args):
        pygame.display.init()
        pygame.font.init()
        pygame.joystick.init()
        pygame.key.set_repeat(280, 110)
        self.args = args
        self.window = pygame.display.set_mode(tuple(args.size), pygame.RESIZABLE)
        pygame.display.set_caption("ORBIT · 轨道航行")
        self.canvas = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.screen = "paused"
        self.selection = 0
        self.settings_parent = "paused"
        self.mode = "keyboard"
        self.alive = True
        self.simulation_time = 0.0
        self.toast_until = 0.0
        self.axis_time = 0.0
        self.axis_direction = (0, 0)
        self.capture_pending = False
        self.capture_count = 0
        self.last_publish = 0.0
        self.evidence = Path(args.evidence_dir)
        self.evidence.mkdir(parents=True, exist_ok=True)
        self.settings = {"star_brightness": 60, "orbit_guides": True}
        if (ROOT / "settings.json").exists():
            try:
                saved = json.loads((ROOT / "settings.json").read_text())
                self.settings["star_brightness"] = max(10, min(100, int(saved["star_brightness"])))
                self.settings["orbit_guides"] = bool(saved["orbit_guides"])
            except (ValueError, KeyError, OSError):
                pass
        self.fonts = {}
        self.font_path = "/usr/share/fonts/google-noto-cjk/NotoSansCJKsc-Regular.otf"
        self.medium_path = "/usr/share/fonts/google-noto-cjk/NotoSansCJKsc-Medium.otf"
        self.latin_path = "/usr/share/fonts/dejavu/DejaVuSans.ttf"
        self.planet = pygame.image.load(ROOT / "assets" / "planet.png").convert_alpha()
        self.planet = pygame.transform.smoothscale(self.planet, (680, 680))
        self.stars = []
        rng = random.Random(8021)
        for _ in range(620):
            self.stars.append((rng.randrange(W), rng.randrange(H), rng.choice([1, 1, 1, 1, 2]), rng.randint(50, 190)))
        self.orbits = [self.orbit_points(560, 150, .57), self.orbit_points(640, 215, .57)]
        self.background = None
        self.rebuild_background()
        self.controllers = []
        for i in range(pygame.joystick.get_count()):
            device = pygame.joystick.Joystick(i)
            device.init()
            self.controllers.append(device)
        self.probe_fd = None
        self.probe_buffer = ""
        if args.test_pipe:
            pipe = Path(args.test_pipe)
            if not pipe.exists():
                os.mkfifo(pipe, 0o600)
            self.probe_fd = os.open(pipe, os.O_RDONLY | os.O_NONBLOCK)
        self.revision = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self.log("start", {"physical_controllers": len(self.controllers)})

    def font(self, size, medium=False, latin=False):
        key = (size, medium, latin)
        if key not in self.fonts:
            path = self.latin_path if latin else (self.medium_path if medium else self.font_path)
            if not Path(path).exists():
                path = self.font_path if Path(self.font_path).exists() else None
            self.fonts[key] = pygame.font.Font(path, size)
        return self.fonts[key]

    def text(self, value, pos, size=24, color=WHITE, medium=False, latin=False):
        image = self.font(size, medium, latin).render(value, True, color)
        self.canvas.blit(image, pos)
        return image.get_rect(topleft=pos)

    def tracked(self, value, pos, size=13, tracking=5):
        x, y = pos
        for ch in value:
            rect = self.text(ch, (x, y), size, MUTED, latin=True)
            x += rect.width + tracking

    def orbit_points(self, rx, ry, rotation):
        values = []
        for i in range(361):
            a = math.tau * i / 360
            x, y = rx * math.cos(a), ry * math.sin(a)
            values.append((928 + x * math.cos(rotation) - y * math.sin(rotation),
                           435 + x * math.sin(rotation) + y * math.cos(rotation)))
        return values

    def ship_position(self):
        a = .67 + self.simulation_time * .075
        x, y = 560 * math.cos(a), 150 * math.sin(a)
        return (928 + x * math.cos(.57) - y * math.sin(.57),
                435 + x * math.sin(.57) + y * math.cos(.57))

    def rebuild_background(self):
        bg = pygame.Surface((W, H))
        bg.fill(INK)
        strength = self.settings["star_brightness"] / 100
        # A sparse background remains secondary to the game and menu.
        for x, y, radius, intensity in self.stars:
            v = int(intensity * strength)
            pygame.draw.circle(bg, (v, min(255, v + 9), min(255, v + 16)), (x, y), radius)
        if self.settings["orbit_guides"]:
            pygame.draw.aalines(bg, (54, 70, 83), False, self.orbits[1])
            pygame.draw.aalines(bg, (72, 101, 107), False, self.orbits[0])
        bg.blit(self.planet, (588, 95))
        if self.settings["orbit_guides"]:
            # The front half travels over the planet, showing spatial depth.
            pygame.draw.aalines(bg, (111, 170, 172), False, self.orbits[0][0:164])
        self.background = bg

    def state(self):
        return {"screen": self.screen, "selection": self.selection, "input_mode": self.mode,
                "simulation_time": round(self.simulation_time, 5),
                "ship_position": [round(v, 3) for v in self.ship_position()],
                "settings": self.settings.copy(), "window": list(self.window.get_size()),
                "physical_controllers": len(self.controllers), "video_driver": pygame.display.get_driver(),
                "native_window": pygame.display.get_wm_info().get("window"), "revision_sha256": self.revision}

    def log(self, event, detail=None):
        entry = {"time": time.time(), "event": event, "detail": detail or {}, **self.state()}
        with (self.evidence / "events.jsonl").open("a") as sink:
            sink.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def publish(self, force=False):
        if force or time.monotonic() - self.last_publish > .12:
            target = self.evidence / "state.json"
            temporary = target.with_suffix(".tmp")
            temporary.write_text(json.dumps(self.state(), ensure_ascii=False))
            temporary.replace(target)
            self.last_publish = time.monotonic()

    def save_settings(self):
        target = ROOT / "settings.json"
        target.write_text(json.dumps(self.settings, indent=2, ensure_ascii=False) + "\n")
        self.toast_until = time.monotonic() + 2.5
        self.rebuild_background()
        self.log("settings_saved")

    def move(self, direction):
        self.selection = (self.selection + direction) % 3

    def adjust(self, direction):
        if self.screen != "settings":
            return
        if self.selection == 0:
            self.settings["star_brightness"] = max(10, min(100, self.settings["star_brightness"] + 10 * direction))
            self.save_settings()
        elif self.selection == 1:
            self.settings["orbit_guides"] = not self.settings["orbit_guides"]
            self.save_settings()

    def back(self):
        if self.screen == "settings":
            self.screen = self.settings_parent
            self.selection = 1
        elif self.screen == "paused":
            self.screen = "flight"
            self.selection = 0
        elif self.screen == "flight":
            self.screen = "paused"
            self.selection = 0

    def activate(self):
        if self.screen == "paused":
            if self.selection == 0:
                self.screen = "flight"
            elif self.selection == 1:
                self.settings_parent, self.screen, self.selection = "paused", "settings", 0
            else:
                self.screen, self.selection = "title", 0
        elif self.screen == "title":
            if self.selection == 0:
                self.simulation_time = 0
                self.screen = "flight"
            elif self.selection == 1:
                self.settings_parent, self.screen, self.selection = "title", "settings", 0
            else:
                self.alive = False
        elif self.screen == "settings":
            if self.selection < 2:
                self.adjust(1)
            else:
                self.back()

    def rows(self):
        if self.screen == "settings":
            return [pygame.Rect(116, 378 + 98 * i, 432, 84) for i in range(3)]
        return [pygame.Rect(116, 378 + 77 * i, 432, 64) for i in range(3)]

    def handle(self, event):
        detail = {"pygame_type": pygame.event.event_name(event.type)}
        if event.type == pygame.QUIT:
            self.alive = False
        elif event.type == pygame.VIDEORESIZE:
            size = (max(640, event.w), max(400, event.h))
            self.window = pygame.display.set_mode(size, pygame.RESIZABLE)
            detail["size"] = list(size)
        elif event.type == pygame.KEYDOWN:
            detail["key"] = pygame.key.name(event.key)
            if event.key == pygame.K_F12:
                self.capture_pending = True
                self.log("capture_request", detail)
                return
            self.mode = "keyboard"
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.back()
            elif self.screen != "flight":
                if event.key == pygame.K_TAB:
                    self.move(-1 if event.mod & pygame.KMOD_SHIFT else 1)
                elif event.key in (pygame.K_UP, pygame.K_w):
                    self.move(-1)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.move(1)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    self.activate()
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self.adjust(-1)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.adjust(1)
        elif event.type in (pygame.JOYBUTTONDOWN, pygame.JOYHATMOTION, pygame.JOYAXISMOTION):
            self.mode = "controller"
            detail["synthetic"] = bool(getattr(event, "synthetic", False))
            if event.type == pygame.JOYBUTTONDOWN:
                detail["button"] = event.button
                if event.button in (1, 7):
                    self.back()
                elif event.button == 0 and self.screen != "flight":
                    self.activate()
            elif event.type == pygame.JOYHATMOTION and self.screen != "flight":
                detail["value"] = list(event.value)
                if event.value[1]:
                    self.move(-event.value[1])
                elif event.value[0]:
                    self.adjust(event.value[0])
            elif event.type == pygame.JOYAXISMOTION and self.screen != "flight":
                detail.update(axis=event.axis, value=event.value)
                direction = 1 if event.value > .55 else -1 if event.value < -.55 else 0
                if not direction:
                    self.axis_direction = (0, 0)
                elif (event.axis, direction) != self.axis_direction or time.monotonic() - self.axis_time > .2:
                    if event.axis == 1:
                        self.move(direction)
                    elif event.axis == 0:
                        self.adjust(direction)
                    self.axis_direction = (event.axis, direction)
                    self.axis_time = time.monotonic()
        elif event.type == pygame.JOYDEVICEADDED:
            device = pygame.joystick.Joystick(event.device_index)
            device.init()
            self.controllers.append(device)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.screen != "flight":
            self.mode = "keyboard"
            x = event.pos[0] * W / self.window.get_width()
            y = event.pos[1] * H / self.window.get_height()
            for i, row in enumerate(self.rows()):
                if row.collidepoint(x, y):
                    self.selection = i
                    self.activate()
                    break
        else:
            return
        self.log("input", detail)
        self.publish(True)

    def pump_probe(self):
        if self.probe_fd is None:
            return
        try:
            self.probe_buffer += os.read(self.probe_fd, 65536).decode()
        except BlockingIOError:
            return
        while "\n" in self.probe_buffer:
            line, self.probe_buffer = self.probe_buffer.split("\n", 1)
            if not line:
                continue
            data = json.loads(line)
            kind = getattr(pygame, data.pop("type"))
            if kind not in (pygame.JOYBUTTONDOWN, pygame.JOYHATMOTION, pygame.JOYAXISMOTION):
                raise ValueError("Test pipe accepts only explicitly synthetic controller events")
            if "value" in data and isinstance(data["value"], list):
                data["value"] = tuple(data["value"])
            data["synthetic"] = True
            pygame.event.post(pygame.event.Event(kind, data))

    def keycap(self, value, x, y):
        font = self.font(15, latin=True)
        width = max(28, font.size(value)[0] + 16)
        pygame.draw.rect(self.canvas, (102, 122, 133), (x, y, width, 29), 1, border_radius=3)
        label = font.render(value, True, (184, 199, 204))
        self.canvas.blit(label, (x + (width - label.get_width()) / 2, y + 4))
        return width

    def hints(self):
        y, x = 835, 60
        if self.mode == "controller":
            pairs = [("D-pad", "选择"), ("A", "确认"), ("B", "返回" if self.screen in ("settings", "title") else "继续")]
            if self.screen == "settings":
                pairs[0] = ("D-pad", "选择 / 调整")
        else:
            pairs = [("↑ ↓", "选择"), ("Enter", "确认"), ("Esc", "返回" if self.screen in ("settings", "title") else "继续")]
            if self.screen == "settings":
                pairs[0] = ("↑ ↓ / ← →", "选择 / 调整")
        for key, label in pairs:
            width = self.keycap(key, x, y)
            self.text(label, (x + width + 13, y + 1), 17, MUTED)
            x += width + 13 + self.font(17).size(label)[0] + 38

    def draw_selected(self, row):
        x, y, w, h = row
        points = [(x, y), (x + w - 16, y), (x + w, y + 16), (x + w, y + h), (x, y + h)]
        pygame.draw.polygon(self.canvas, MINT, points)

    def arrow(self, pos, color):
        x, y = pos
        pygame.draw.line(self.canvas, color, (x - 16, y), (x + 3, y), 2)
        pygame.draw.lines(self.canvas, color, False, [(x - 4, y - 7), (x + 3, y), (x - 4, y + 7)], 2)

    def draw_ship(self):
        x, y = self.ship_position()
        # A small craft follows the real simulation clock; pause freezes this clock.
        direction = .77
        c, s = math.cos(direction), math.sin(direction)
        def point(a, b):
            return (x + a * c - b * s, y + a * s + b * c)
        pygame.draw.line(self.canvas, (62, 128, 151), point(-30, 0), point(-10, 0), 3)
        pygame.draw.line(self.canvas, (177, 233, 233), point(-21, 0), point(-10, 0), 2)
        pygame.draw.polygon(self.canvas, (161, 179, 185), [point(13, 0), point(-8, -6), point(-5, 0), point(-8, 6)])
        pygame.draw.line(self.canvas, (227, 237, 231), point(-1, 0), point(10, 0), 2)

    def draw(self):
        self.canvas.blit(self.background, (0, 0))
        self.draw_ship()
        if self.screen == "flight":
            self.text("航行中", (1260, 30), 18, MUTED)
            self.keycap("Menu" if self.mode == "controller" else "Esc", 60, 835)
            self.text("暂停", (132, 836), 18, MUTED)
        else:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((2, 7, 12, 18))
            self.canvas.blit(veil, (0, 0))
            if self.screen == "paused":
                self.tracked("FLIGHT PAUSED", (120, 242))
                self.text("已暂停", (116, 269), 60, WHITE, True)
                self.text("Ⅱ", (1286, 27), 24, WHITE, latin=True)
                self.text("航行已冻结", (1320, 31), 17, MUTED)
                labels = ["继续航行", "设置", "返回标题"]
            elif self.screen == "settings":
                self.tracked("FLIGHT SETTINGS", (120, 242))
                self.text("设置", (116, 269), 60, WHITE, True)
                self.text("Ⅱ", (1286, 27), 24, WHITE, latin=True)
                self.text("航行已冻结" if self.settings_parent == "paused" else "标题菜单", (1320, 31), 17, MUTED)
                labels = ["星光亮度", "轨道指引", "返回"]
            else:
                self.tracked("SPACEFLIGHT", (120, 242))
                self.text("轨道航行", (116, 269), 60, WHITE, True)
                labels = ["开始航行", "设置", "退出"]
            for i, row in enumerate(self.rows()):
                selected = i == self.selection
                color = INK if selected else WHITE
                if selected:
                    self.draw_selected(row)
                else:
                    pygame.draw.line(self.canvas, RULE, row.bottomleft, row.bottomright)
                self.text(labels[i], (row.x + 24, row.y + 13), 27, color, selected)
                if self.screen == "settings" and i == 0:
                    value = self.settings["star_brightness"]
                    self.text(str(value) + "%", (row.right - 84, row.y + 16), 22, color, latin=True)
                    track = (39, 74, 78) if selected else RULE
                    pygame.draw.line(self.canvas, track, (row.x + 25, row.y + 65), (row.right - 25, row.y + 65), 2)
                    knob = row.x + 25 + (row.w - 50) * (value - 10) / 90
                    pygame.draw.circle(self.canvas, color, (round(knob), row.y + 65), 5)
                elif self.screen == "settings" and i == 1:
                    self.text("开启" if self.settings["orbit_guides"] else "关闭", (row.right - 82, row.y + 16), 23, color)
                elif selected:
                    self.arrow((row.right - 29, row.centery), color)
            if self.screen == "paused" and self.selection == 0:
                pygame.draw.line(self.canvas, (111, 166, 164), (548, 410), (748, 410), 1)
            if self.screen == "settings" and time.monotonic() < self.toast_until:
                self.text("已保存到此设备", (140, 710), 18, MINT)
            self.hints()
        if self.window.get_size() == (W, H):
            self.window.blit(self.canvas, (0, 0))
        else:
            pygame.transform.smoothscale(self.canvas, self.window.get_size(), self.window)
        pygame.display.flip()
        if self.capture_pending:
            self.capture_count += 1
            width, height = self.window.get_size()
            path = self.evidence / f"{self.capture_count:02d}-{self.screen}-{width}x{height}.png"
            pygame.image.save(self.window, path)
            self.capture_pending = False
            self.log("screenshot", {"path": str(path)})

    def run(self):
        try:
            while self.alive:
                dt = min(self.clock.tick(30) / 1000, .1)
                self.pump_probe()
                for event in pygame.event.get():
                    self.handle(event)
                if self.screen == "flight":
                    self.simulation_time += dt
                self.draw()
                self.publish()
        finally:
            self.log("exit")
            self.publish(True)
            if self.probe_fd is not None:
                os.close(self.probe_fd)
            pygame.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, nargs=2, default=(1440, 900))
    parser.add_argument("--evidence-dir", default=str(ROOT / "evidence" / "session"))
    parser.add_argument("--test-pipe", help="Optional pipe accepting explicitly synthetic joystick events")
    Flight(parser.parse_args()).run()
