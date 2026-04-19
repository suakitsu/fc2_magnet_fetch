from __future__ import annotations

import sys
import threading
import tkinter as tk
from tkinter import messagebox

from .config import load_config, save_cookie_to_config
from .constants import GENRES, VERSION
from .service import FC2Service

try:
    import winreg
except Exception:
    winreg = None


class FC2MagnetGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"FC2 Magnet Tool {VERSION}")
        self.root.geometry("1180x820")
        self.root.minsize(920, 680)

        self.stop_event = threading.Event()
        self.worker_thread: threading.Thread | None = None
        self._effective_theme = ""
        self._compact = False

        self.config = load_config()
        self.service = FC2Service(self.config, self.log)

        self.mode_var = tk.StringVar(value="tags")
        self.theme_var = tk.StringVar(value="浅色")
        self.url_var = tk.StringVar(value="https://adult.contents.fc2.com/search/?")
        self.max_count_var = tk.StringVar(value="100")
        self.fcu_var = tk.StringVar(value=self.config.fcu)
        self.phpsessid_var = tk.StringVar(value=self.config.phpsessid)
        self.status_var = tk.StringVar()
        self.next_var = tk.StringVar()
        self.selection_var = tk.StringVar()
        self.selected_genres: set[int] = set()
        self.log_lines: list[str] = []
        self.output_mode = "log"
        self.running = False
        self.stopping = False

        self.tag_buttons: dict[int, tk.Label] = {}
        self.theme_buttons: dict[str, tk.Label] = {}
        self.mode_buttons: dict[str, tk.Label] = {}
        self.output_buttons: dict[str, tk.Label] = {}

        self._build_layout()
        self._bind_events()
        self._apply_theme(force=True)
        self._refresh_state()
        self.log("欢迎使用 GUI。先应用 Cookie，然后点标签，最后点开始。")
        self._poll_system_theme()

    def _palette(self, theme: str) -> dict[str, str]:
        if theme == "深色":
            return {
                "bg": "#14161a",
                "panel": "#1d2026",
                "panel2": "#252a32",
                "border": "#343a45",
                "text": "#f5f7fb",
                "muted": "#a6afbd",
                "input": "#15191f",
                "accent": "#10a37f",
                "accent_hover": "#0d8d6d",
                "accent_soft": "#123b32",
                "danger": "#ef4444",
                "chip": "#272d36",
                "chip_active": "#10a37f",
                "button": "#2a303a",
                "button_hover": "#343c49",
                "text_area": "#11151b",
            }
        return {
            "bg": "#f6f8fb",
            "panel": "#ffffff",
            "panel2": "#f8fafc",
            "border": "#dfe6ee",
            "text": "#111827",
            "muted": "#667085",
            "input": "#ffffff",
            "accent": "#10a37f",
            "accent_hover": "#0e9272",
            "accent_soft": "#e8f7f2",
            "danger": "#dc2626",
            "chip": "#eef3f8",
            "chip_active": "#10a37f",
            "button": "#edf2f7",
            "button_hover": "#e3eaf2",
            "text_area": "#ffffff",
        }

    def _detect_system_theme(self) -> str:
        if not sys.platform.startswith("win") or winreg is None:
            return "浅色"
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return "浅色" if int(value) == 1 else "深色"
        except Exception:
            return "浅色"

    def _colors(self) -> dict[str, str]:
        mode = self.theme_var.get()
        return self._palette(self._detect_system_theme() if mode == "跟随系统" else mode)

    def _build_layout(self) -> None:
        self.app = tk.Frame(self.root)
        self.app.pack(fill=tk.BOTH, expand=True)
        self.app.grid_columnconfigure(0, weight=1)
        self.app.grid_rowconfigure(3, weight=1)
        self.app.grid_rowconfigure(4, weight=0)

        self.header = tk.Frame(self.app)
        self.header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        self.header.grid_columnconfigure(0, weight=1)

        self.title = tk.Label(self.header, text="FC2 Magnet", anchor="w")
        self.title.grid(row=0, column=0, sticky="w")

        self.theme_bar = tk.Frame(self.header)
        self.theme_bar.grid(row=0, column=1, sticky="e")
        for name in ("跟随系统", "浅色", "深色"):
            btn = tk.Label(self.theme_bar, text=name, cursor="hand2", padx=12, pady=7)
            btn.pack(side=tk.LEFT, padx=(0, 6))
            btn.bind("<Button-1>", lambda _e, n=name: self._set_theme(n))
            self.theme_buttons[name] = btn

        self.status = tk.Label(self.app, textvariable=self.status_var, anchor="w")
        self.status.grid(row=1, column=0, sticky="ew", padx=18)

        self.next_step = tk.Label(self.app, textvariable=self.next_var, anchor="w", padx=12, pady=9)
        self.next_step.grid(row=2, column=0, sticky="ew", padx=18, pady=(8, 10))

        self.main = tk.Frame(self.app)
        self.main.grid(row=3, column=0, sticky="nsew", padx=18)
        self.main.grid_columnconfigure(0, weight=2)
        self.main.grid_columnconfigure(1, weight=1)
        self.main.grid_rowconfigure(0, weight=1)

        self.tags_card = self._card(self.main)
        self.tags_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.tags_card.grid_columnconfigure(0, weight=1)
        self.tags_card.grid_rowconfigure(3, weight=1)

        self.side_card = self._card(self.main)
        self.side_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.side_card.grid_columnconfigure(0, weight=1)

        self._build_tags_card()
        self._build_side_card()

        self.output_card = self._card(self.app)
        self.output_card.grid(row=4, column=0, sticky="nsew", padx=18, pady=(14, 18))
        self.output_card.configure(height=170)
        self.output_card.grid_propagate(False)
        self.output_card.grid_columnconfigure(0, weight=1)
        self.output_card.grid_rowconfigure(1, weight=1)
        self._build_output_card()

    def _card(self, parent: tk.Widget) -> tk.Frame:
        return tk.Frame(parent, highlightthickness=1, bd=0, padx=14, pady=12)

    def _build_tags_card(self) -> None:
        self.tags_title = tk.Label(self.tags_card, text="标签", anchor="w")
        self.tags_title.grid(row=0, column=0, sticky="ew")

        self.mode_bar = tk.Frame(self.tags_card)
        self.mode_bar.grid(row=1, column=0, sticky="w", pady=(10, 10))
        for key, label in (("tags", "标签模式"), ("url", "手动 URL")):
            btn = tk.Label(self.mode_bar, text=label, cursor="hand2", padx=14, pady=8)
            btn.pack(side=tk.LEFT, padx=(0, 8))
            btn.bind("<Button-1>", lambda _e, k=key: self._set_mode(k))
            self.mode_buttons[key] = btn

        self.url_row = tk.Frame(self.tags_card)
        self.url_row.grid(row=2, column=0, sticky="ew")
        self.url_row.grid_columnconfigure(1, weight=1)
        self.url_label = tk.Label(self.url_row, text="URL")
        self.url_label.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.url_entry = tk.Entry(self.url_row, textvariable=self.url_var, relief=tk.FLAT, highlightthickness=1)
        self.url_entry.grid(row=0, column=1, sticky="ew")

        self.selection_label = tk.Label(self.tags_card, textvariable=self.selection_var, anchor="w")
        self.selection_label.grid(row=2, column=0, sticky="ew")

        self.tag_area = tk.Frame(self.tags_card)
        self.tag_area.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        self.tag_area.grid_columnconfigure(0, weight=1)
        self.tag_area.grid_rowconfigure(0, weight=1)

        self.tag_canvas = tk.Canvas(self.tag_area, bd=0, highlightthickness=0)
        self.tag_canvas.grid(row=0, column=0, sticky="nsew")
        self.tag_scroll = tk.Scrollbar(self.tag_area, orient=tk.VERTICAL, command=self.tag_canvas.yview, width=12)
        self.tag_scroll.grid(row=0, column=1, sticky="ns")
        self.tag_canvas.configure(yscrollcommand=self.tag_scroll.set)

        self.tag_frame = tk.Frame(self.tag_canvas)
        self.tag_window = self.tag_canvas.create_window((0, 0), window=self.tag_frame, anchor="nw")
        self.tag_frame.bind("<Configure>", self._update_tag_scroll)
        self.tag_canvas.bind("<Configure>", self._on_tag_canvas_resize)

        for gid, name in sorted(GENRES.items(), key=lambda x: x[0]):
            chip = tk.Label(self.tag_frame, text=name, cursor="hand2", padx=13, pady=8)
            chip.bind("<Button-1>", lambda _e, g=gid: self._toggle_genre(g))
            chip.bind("<Enter>", lambda _e, g=gid: self._hover_genre(g, True))
            chip.bind("<Leave>", lambda _e, g=gid: self._hover_genre(g, False))
            self.tag_buttons[gid] = chip

        self.tag_actions = tk.Frame(self.tags_card)
        self.tag_actions.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        self.tag_actions.grid_columnconfigure(0, weight=1)
        self.tag_actions.grid_columnconfigure(1, weight=1)
        self.btn_all_tags = self._button(self.tag_actions, "全选", self.select_all_genres, primary=False)
        self.btn_all_tags.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.btn_clear_tags = self._button(self.tag_actions, "清空", self.clear_genres, primary=False)
        self.btn_clear_tags.grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _build_side_card(self) -> None:
        self.conn_title = tk.Label(self.side_card, text="开始", anchor="w")
        self.conn_title.grid(row=0, column=0, sticky="ew")

        self.cookie_box = tk.Frame(self.side_card)
        self.cookie_box.grid(row=1, column=0, sticky="ew", pady=(12, 8))
        self.cookie_box.grid_columnconfigure(1, weight=1)

        self.fcu_label = tk.Label(self.cookie_box, text="fcu", anchor="w")
        self.fcu_label.grid(row=0, column=0, sticky="w", pady=(0, 8), padx=(0, 8))
        self.fcu_entry = tk.Entry(self.cookie_box, textvariable=self.fcu_var, relief=tk.FLAT, highlightthickness=1, show="•")
        self.fcu_entry.grid(row=0, column=1, sticky="ew", pady=(0, 8))

        self.sess_label = tk.Label(self.cookie_box, text="PHPSESSID", anchor="w")
        self.sess_label.grid(row=1, column=0, sticky="w", padx=(0, 8))
        self.sess_entry = tk.Entry(self.cookie_box, textvariable=self.phpsessid_var, relief=tk.FLAT, highlightthickness=1, show="•")
        self.sess_entry.grid(row=1, column=1, sticky="ew")

        self.cookie_actions = tk.Frame(self.side_card)
        self.cookie_actions.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.cookie_actions.grid_columnconfigure(0, weight=1)
        self.cookie_actions.grid_columnconfigure(1, weight=1)

        self.btn_apply = self._button(self.cookie_actions, "应用 Cookie", self.apply_runtime_cookie, primary=True)
        self.btn_apply.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.btn_save = self._button(self.cookie_actions, "保存", self.save_cookie, primary=False)
        self.btn_save.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.count_box = tk.Frame(self.side_card)
        self.count_box.grid(row=3, column=0, sticky="ew", pady=(14, 8))
        self.count_box.grid_columnconfigure(1, weight=1)
        self.count_label = tk.Label(self.count_box, text="数量")
        self.count_label.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.count_entry = tk.Entry(self.count_box, textvariable=self.max_count_var, width=8, relief=tk.FLAT, highlightthickness=1)
        self.count_entry.grid(row=0, column=1, sticky="w")
        self.count_hint = tk.Label(self.count_box, text="0 = 全部")
        self.count_hint.grid(row=0, column=2, sticky="w", padx=(8, 0))

        self.run_actions = tk.Frame(self.side_card)
        self.run_actions.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        self.run_actions.grid_columnconfigure(0, weight=1)
        self.run_actions.grid_columnconfigure(1, weight=1)

        self.btn_fetch_ids = self._button(self.run_actions, "采集编号", self.start_fetch_ids, primary=True)
        self.btn_fetch_ids.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.btn_fetch_magnets = self._button(self.run_actions, "检索链接", self.start_fetch_magnets, primary=True)
        self.btn_fetch_magnets.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.btn_stop = self._button(self.side_card, "停止任务", self.stop_running, primary=False)
        self.btn_stop.grid(row=5, column=0, sticky="ew", pady=(8, 0))

    def _build_output_card(self) -> None:
        self.output_top = tk.Frame(self.output_card)
        self.output_top.grid(row=0, column=0, sticky="ew")
        self.output_top.grid_columnconfigure(0, weight=1)
        self.output_title = tk.Label(self.output_top, text="结果", anchor="w")
        self.output_title.grid(row=0, column=0, sticky="w")

        self.output_bar = tk.Frame(self.output_top)
        self.output_bar.grid(row=0, column=1, sticky="e")
        for key, label in (
            ("log", "日志"),
            ("list.txt", "list"),
            ("magnet.txt", "magnet"),
            ("no_magnet.txt", "no result"),
            ("error.txt", "error"),
        ):
            btn = tk.Label(self.output_bar, text=label, cursor="hand2", padx=10, pady=6)
            btn.pack(side=tk.LEFT, padx=(0, 6))
            btn.bind("<Button-1>", lambda _e, k=key: self._switch_output(k))
            self.output_buttons[key] = btn

        self.output_text = tk.Text(self.output_card, wrap=tk.WORD, font=("Consolas", 10), relief=tk.FLAT, highlightthickness=1)
        self.output_text.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

    def _button(self, parent: tk.Widget, text: str, command, primary: bool) -> tk.Label:
        btn = tk.Label(parent, text=text, cursor="hand2", padx=12, pady=9)
        btn._primary = primary  # type: ignore[attr-defined]
        btn._command = command  # type: ignore[attr-defined]
        btn._enabled = True  # type: ignore[attr-defined]
        btn.bind("<Button-1>", lambda _e, b=btn: self._run_button(b))
        btn.bind("<Enter>", lambda _e, b=btn: self._hover_button(b, True))
        btn.bind("<Leave>", lambda _e, b=btn: self._hover_button(b, False))
        return btn

    def _hover_button(self, btn: tk.Label, active: bool) -> None:
        if not getattr(btn, "_enabled", True):
            return
        c = self._colors()
        if active:
            btn.configure(bg=c["accent_hover"] if getattr(btn, "_primary", False) else c["button_hover"])
        else:
            self._refresh_state()

    def _run_button(self, btn: tk.Label) -> None:
        if not getattr(btn, "_enabled", True):
            return
        getattr(btn, "_command")()

    def _set_enabled(self, btn: tk.Label, enabled: bool) -> None:
        btn._enabled = enabled  # type: ignore[attr-defined]
        btn.configure(cursor="hand2" if enabled else "arrow")

    def _bind_events(self) -> None:
        self.theme_var.trace_add("write", lambda *_: self._apply_theme(force=True))
        self.fcu_var.trace_add("write", lambda *_: self._refresh_state())
        self.phpsessid_var.trace_add("write", lambda *_: self._refresh_state())
        self.url_var.trace_add("write", lambda *_: self._refresh_state())
        self.root.bind("<Configure>", self._on_resize)

    def _on_resize(self, event) -> None:
        if event.widget != self.root:
            return
        compact = event.width < 900
        if compact != self._compact:
            self._compact = compact
            self.tags_card.grid_forget()
            self.side_card.grid_forget()
            if compact:
                self.main.grid_columnconfigure(0, weight=1)
                self.main.grid_columnconfigure(1, weight=1)
                self.tags_card.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 10))
                self.side_card.grid(row=1, column=0, sticky="nsew", padx=0, pady=(10, 0))
                self.main.grid_rowconfigure(0, weight=1)
                self.main.grid_rowconfigure(1, weight=0)
            else:
                self.main.grid_columnconfigure(0, weight=2)
                self.main.grid_columnconfigure(1, weight=1)
                self.tags_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
                self.side_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
                self.main.grid_rowconfigure(0, weight=1)
                self.main.grid_rowconfigure(1, weight=0)
        self._layout_tags()

    def _set_theme(self, name: str) -> None:
        self.theme_var.set(name)

    def _set_mode(self, name: str) -> None:
        self.mode_var.set(name)
        self._refresh_state()

    def _toggle_genre(self, gid: int) -> None:
        if gid in self.selected_genres:
            self.selected_genres.remove(gid)
        else:
            self.selected_genres.add(gid)
        self._update_url_from_tags()
        self._refresh_state()

    def _hover_genre(self, gid: int, active: bool) -> None:
        c = self._colors()
        chip = self.tag_buttons[gid]
        if active:
            chip.configure(bg=c["accent_hover"] if gid in self.selected_genres else c["button_hover"])
        else:
            self._refresh_state()

    def _update_url_from_tags(self) -> None:
        if not self.selected_genres:
            self.url_var.set("https://adult.contents.fc2.com/search/?")
            return
        self.url_var.set(self.service.build_search_url(sorted(self.selected_genres)))

    def _layout_tags(self) -> None:
        if not hasattr(self, "tag_frame"):
            return
        width = max(1, self.tag_canvas.winfo_width())
        cols = max(2, min(5, width // 145))
        for child in self.tag_frame.winfo_children():
            child.grid_forget()
        for index, gid in enumerate(sorted(self.tag_buttons)):
            chip = self.tag_buttons[gid]
            row, col = divmod(index, cols)
            chip.grid(row=row, column=col, sticky="ew", padx=5, pady=5)
        for col in range(cols):
            self.tag_frame.grid_columnconfigure(col, weight=1)
        self.tag_canvas.itemconfigure(self.tag_window, width=width)
        self._update_tag_scroll()

    def _on_tag_canvas_resize(self, event) -> None:
        self.tag_canvas.itemconfigure(self.tag_window, width=event.width)
        self._layout_tags()

    def _update_tag_scroll(self, _event=None) -> None:
        self.tag_canvas.configure(scrollregion=self.tag_canvas.bbox("all"))

    def _poll_system_theme(self) -> None:
        if self.theme_var.get() == "跟随系统":
            self._apply_theme(force=False)
        self.root.after(3000, self._poll_system_theme)

    def _apply_theme(self, force: bool = False) -> None:
        mode = self.theme_var.get()
        effective = self._detect_system_theme() if mode == "跟随系统" else mode
        if not force and effective == self._effective_theme:
            return
        self._effective_theme = effective
        c = self._colors()

        self.root.configure(bg=c["bg"])
        for w in (self.app, self.header, self.main, self.theme_bar, self.mode_bar, self.tag_area, self.tag_actions, self.cookie_box, self.cookie_actions, self.count_box, self.run_actions, self.output_top, self.output_bar):
            w.configure(bg=c["bg"] if w in (self.app, self.header, self.main, self.theme_bar) else c["panel"])
        for card in (self.tags_card, self.side_card, self.output_card):
            card.configure(bg=c["panel"], highlightbackground=c["border"])
        for w in (self.tags_title, self.conn_title, self.output_title):
            w.configure(bg=c["panel"], fg=c["text"], font=("Microsoft YaHei UI", 13, "bold"))
        self.title.configure(bg=c["bg"], fg=c["text"], font=("Microsoft YaHei UI", 22, "bold"))
        self.status.configure(bg=c["bg"], fg=c["muted"], font=("Microsoft YaHei UI", 10))
        self.next_step.configure(bg=c["accent_soft"], fg=c["accent"], font=("Microsoft YaHei UI", 10, "bold"))

        for w in (self.url_row, self.tag_frame, self.cookie_box, self.count_box):
            w.configure(bg=c["panel"])
        for w in (self.url_label, self.fcu_label, self.sess_label, self.count_label, self.count_hint, self.selection_label):
            w.configure(bg=c["panel"], fg=c["muted"], font=("Microsoft YaHei UI", 10))

        for entry in (self.url_entry, self.fcu_entry, self.sess_entry, self.count_entry):
            entry.configure(
                bg=c["input"],
                fg=c["text"],
                insertbackground=c["text"],
                highlightbackground=c["border"],
                highlightcolor=c["accent"],
                disabledbackground=c["input"],
                disabledforeground=c["muted"],
            )

        self.tag_canvas.configure(bg=c["panel"])
        self.output_text.configure(
            bg=c["text_area"],
            fg=c["text"],
            insertbackground=c["text"],
            highlightbackground=c["border"],
            highlightcolor=c["accent"],
        )
        self._refresh_state()

    def _style_label_button(self, btn: tk.Label, selected: bool = False, enabled: bool = True) -> None:
        c = self._colors()
        primary = getattr(btn, "_primary", False)
        if not enabled:
            btn.configure(bg=c["button"], fg=c["muted"])
        elif selected or primary:
            btn.configure(bg=c["accent"], fg="#ffffff")
        else:
            btn.configure(bg=c["button"], fg=c["text"])

    def _refresh_state(self) -> None:
        c = self._colors()
        is_tags = self.mode_var.get() == "tags"
        has_cookie = self.service.has_required_cookie()
        has_tags = bool(self.selected_genres)
        has_url = "adult.contents.fc2.com" in self.url_var.get().strip()
        has_list = bool(self.service.read_lines("list.txt"))

        proxy_text = self.config.proxy if self.config.proxy_enabled else "未启用"
        cookie_text = "已就绪" if has_cookie else "未配置"
        state_text = "运行中" if self.running else "空闲"
        self.status_var.set(f"{state_text}  |  Cookie {cookie_text}  |  代理 {proxy_text}  |  输出 Downloads")

        if not has_cookie:
            self.next_var.set("下一步：应用 Cookie")
        elif is_tags and not has_tags:
            self.next_var.set("下一步：点选标签")
        elif not is_tags and not has_url:
            self.next_var.set("下一步：输入 URL")
        elif not has_list:
            self.next_var.set("下一步：采集编号")
        else:
            self.next_var.set("下一步：检索链接")

        if is_tags:
            self.url_row.grid_remove()
            self.selection_label.grid(row=2, column=0, sticky="ew")
        else:
            self.selection_label.grid_remove()
            self.url_row.grid(row=2, column=0, sticky="ew")
        self.url_entry.configure(state=tk.NORMAL)

        if self.selected_genres:
            names = [self.service.genre_name(gid) for gid in sorted(self.selected_genres)]
            preview = "、".join(names[:5])
            if len(names) > 5:
                preview += f" 等 {len(names)} 个"
            self.selection_var.set(f"已选：{preview}")
        else:
            self.selection_var.set("点击下面的标签即可选择，再点一次取消。")

        for name, btn in self.theme_buttons.items():
            self._style_label_button(btn, selected=self.theme_var.get() == name)
        for name, btn in self.mode_buttons.items():
            self._style_label_button(btn, selected=self.mode_var.get() == name)
        for name, btn in self.output_buttons.items():
            self._style_label_button(btn, selected=self.output_mode == name)

        for gid, chip in self.tag_buttons.items():
            active = gid in self.selected_genres
            chip.configure(
                bg=c["chip_active"] if active else c["chip"],
                fg="#ffffff" if active else c["text"],
                font=("Microsoft YaHei UI", 10, "bold" if active else "normal"),
            )

        for btn in (self.btn_all_tags, self.btn_clear_tags, self.btn_apply, self.btn_save):
            self._style_label_button(btn, enabled=not self.running)
            self._set_enabled(btn, not self.running)

        can_fetch_ids = (not self.running) and has_cookie and ((is_tags and has_tags) or ((not is_tags) and has_url))
        can_fetch_magnets = (not self.running) and has_list
        can_stop = self.running and not self.stopping
        self._style_label_button(self.btn_fetch_ids, enabled=can_fetch_ids)
        self._style_label_button(self.btn_fetch_magnets, enabled=can_fetch_magnets)
        self._style_label_button(self.btn_stop, enabled=can_stop)
        self._set_enabled(self.btn_fetch_ids, can_fetch_ids)
        self._set_enabled(self.btn_fetch_magnets, can_fetch_magnets)
        self._set_enabled(self.btn_stop, can_stop)


    def log(self, message: str) -> None:
        self.root.after(0, lambda: self._append_log(message))

    def _append_log(self, message: str) -> None:
        self.log_lines.append(message)
        if self.output_mode == "log":
            self.output_text.insert(tk.END, message + "\n")
            self.output_text.see(tk.END)

    def _switch_output(self, mode: str) -> None:
        self.output_mode = mode
        self.output_text.delete("1.0", tk.END)
        if mode == "log":
            self.output_text.insert(tk.END, "\n".join(self.log_lines))
            if self.log_lines:
                self.output_text.insert(tk.END, "\n")
        else:
            lines = self.service.read_lines(mode)
            self.output_text.insert(tk.END, "\n".join(lines) if lines else f"{mode} 为空或不存在。")
        self._refresh_state()

    def select_all_genres(self) -> None:
        self.selected_genres = set(GENRES.keys())
        self._update_url_from_tags()
        self._refresh_state()

    def clear_genres(self) -> None:
        self.selected_genres.clear()
        self._update_url_from_tags()
        self._refresh_state()

    def apply_runtime_cookie(self) -> None:
        self.service.update_runtime_cookies(self.fcu_var.get().strip(), self.phpsessid_var.get().strip())
        self.log("Cookie 已应用。")
        self._refresh_state()

    def save_cookie(self) -> None:
        save_cookie_to_config(self.fcu_var.get().strip(), self.phpsessid_var.get().strip())
        self.config = load_config()
        self.service.config = self.config
        self.log("Cookie 已保存到 config.ini。")
        self._refresh_state()

    def _start_worker(self, target, start_message: str) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo("提示", "已有任务在运行。")
            return
        self.stop_event.clear()
        self.running = True
        self.stopping = False
        self._refresh_state()
        self.log(start_message)

        def runner():
            try:
                target()
            finally:
                self.root.after(0, self._on_worker_done)

        self.worker_thread = threading.Thread(target=runner, daemon=True)
        self.worker_thread.start()

    def _on_worker_done(self) -> None:
        self.running = False
        self.stopping = False
        self._refresh_state()
        self.log("任务结束。")

    def start_fetch_ids(self) -> None:
        if not self.service.has_required_cookie():
            messagebox.showwarning("提示", "请先应用 Cookie。")
            return
        if self.mode_var.get() == "tags":
            if not self.selected_genres:
                messagebox.showwarning("提示", "请先点选标签。")
                return
            url = self.service.build_search_url(sorted(self.selected_genres))
            self.url_var.set(url)
        else:
            url = self.url_var.get().strip()
            if "adult.contents.fc2.com" not in url:
                messagebox.showwarning("提示", "请输入有效 URL。")
                return

        max_count = self._parse_max_count()
        if max_count is None:
            return
        self._start_worker(lambda: self.service.fetch_ids(url, max_count=max_count, stop_event=self.stop_event), "开始采集编号...")

    def start_fetch_magnets(self) -> None:
        self._start_worker(lambda: self.service.fetch_magnets(stop_event=self.stop_event), "开始检索链接...")

    def stop_running(self) -> None:
        if not self.running:
            return
        self.stop_event.set()
        self.stopping = True
        self.log("已发送停止信号，当前请求结束后会立刻停止。")
        self._refresh_state()

    def load_preview(self, filename: str) -> None:
        self._switch_output(filename)

    def _parse_max_count(self) -> int | None:
        raw = self.max_count_var.get().strip()
        if raw == "":
            self.max_count_var.set("0")
            return 0
        try:
            value = int(raw)
        except ValueError:
            messagebox.showwarning("提示", "数量只能填写数字，比如 8；填 0 表示全部。")
            return None
        if value < 0:
            messagebox.showwarning("提示", "数量不能小于 0。")
            return None
        self.max_count_var.set(str(value))
        self.log(f"本次采集数量上限: {'全部' if value == 0 else value}")
        return value
