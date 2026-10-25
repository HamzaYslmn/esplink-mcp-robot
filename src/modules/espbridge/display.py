"""Connect to the ESP32's OLED over esplink (Bluetooth). Env-driven, BLE-only."""
from __future__ import annotations

import os
import sys
import threading


class NullDisplay:
    """Stand-in panel for running with no board attached."""

    width, height = 128, 64

    def show(self, image=None):
        pass

    def contrast(self, value):
        pass

    def clear(self):
        pass


class WindowDisplay:
    """A 0.96" 128x64 OLED emulated in a desktop window -- develop/run Pip with no board.

    Same duck-typed panel API as Display/NullDisplay (width/height/show/contrast/clear), so it
    drops straight into EyeEngine. Tk isn't thread-safe across threads, so the whole GUI lives
    in one private thread: the engine's show() just parks the latest PIL frame, and a Tk timer
    in that thread tints + scales it (NEAREST, blocky OLED pixels) and blits it. The window is
    frameless and always-on-top; drag it by its body, right-click to resize or close (Esc quits too)."""

    width, height = 128, 64
    _FG, _BG = (150, 220, 255), (8, 10, 14)        # lit pixel (blue-white OLED) on near-black

    _DIAG_IN = 1.4                                 # the panel's advertised diagonal (original 0.96")

    def __init__(self, *, fps=24):
        self._size = None                           # (w, h) px, fixed once the screen PPI is known
        self._frame_ms = max(1, int(1000 / max(5, fps)))
        self._latest = None                         # newest PIL "1" frame (atomic swap)
        self._bright = 255                          # 0..255, dims the lit colour
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, name="oled-window", daemon=True)
        self._thread.start()
        self._ready.wait(5.0)                       # let the window come up before the engine drives it

    # ----------------------------------------------------------- panel API
    def show(self, image=None):
        if image is not None:
            self._latest = image.copy()

    def contrast(self, value):
        self._bright = max(0, min(255, int(value)))

    def clear(self):
        self._latest = None

    # --------------------------------------------------------- GUI thread
    @staticmethod
    def _make_dpi_aware():
        """Windows: stop the OS from up-scaling our window so its pixel size is honoured and
        winfo_fpixels reports the real (scaled) DPI instead of a virtualised 96. No-op elsewhere."""
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)   # per-monitor aware
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()        # older Windows fallback
        except Exception:
            pass                                                 # not Windows / no ctypes

    def _trap_ctrl_c(self):
        """Tcl installs a Windows console handler that swallows Ctrl+C (CPython #94296), so the
        terminal can no longer interrupt us. Register our own *after* Tk -- Windows fires handlers
        newest-first, so ours wins -- turning Ctrl+C / Break / console-close into an immediate exit.
        No-op off Windows, where Tk leaves Ctrl+C alone."""
        try:
            import ctypes
            from ctypes import wintypes
            handler = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)(lambda _ctrl: os._exit(0))
            self._ctrl_handler = handler                         # keep a ref or the GC drops it and Windows ignores it
            ctypes.windll.kernel32.SetConsoleCtrlHandler(handler, True)
        except Exception:
            pass                                                 # not Windows / no console / no ctypes

    def _run(self):
        try:
            import tkinter as tk
            from PIL import Image, ImageTk
        except Exception as e:                      # no Tk / no Pillow -> fail loud, not silent
            print(f"[window] cannot open OLED window ({e}); install pillow + tkinter",
                  file=sys.stderr, flush=True)
            self._ready.set()
            return

        self._make_dpi_aware()                      # must run before the first Tk window
        self._tk, self._Image, self._ImageTk = tk, Image, ImageTk
        root = tk.Tk()
        self._trap_ctrl_c()                         # Tcl just stole Ctrl+C from the terminal -- take it back
        root.title("Pip - 128x64 OLED (emulator)")
        root.overrideredirect(True)                 # frameless: no titlebar / border
        root.attributes("-topmost", True)           # float above every other window
        root.configure(bg="#202428")                # bezel around the panel
        self._size = self._true_size = self._panel_size(root)   # true physical size; the menu can rescale it
        self._label = tk.Label(root, bg="#000000", borderwidth=0)
        self._label.pack(padx=4, pady=4)            # thin bezel; keep the glass close to 0.96"
        self._drag = (0, 0)                          # cursor offset from the window origin
        self._root, self._photo = root, None
        self._build_menu(root)
        root.bind("<Button-1>", self._grab)          # drag the frameless window by its body
        root.bind("<B1-Motion>", self._drag_to)
        root.bind("<Button-3>", self._popup)         # no titlebar -> right-click for resize / close
        root.bind("<Escape>", lambda _e: self._quit())   # ... and Esc quits the session
        self._ready.set()
        root.after(self._frame_ms, self._tick)
        root.mainloop()

    def _panel_size(self, root):
        """The real 0.96" glass in pixels for this screen (2:1 aspect splits the diagonal). Tk's
        DPI tracks the OS scaling, not the monitor's true density -- set ROBOT_SCREEN_PPI to nail it."""
        h_in = self._DIAG_IN / (5 ** 0.5)            # diag^2 = (2h)^2 + h^2 = 5h^2
        ppi = float(os.getenv("ROBOT_SCREEN_PPI") or root.winfo_fpixels("1i"))
        w, h = max(1, round(2 * h_in * ppi)), max(1, round(h_in * ppi))
        print(f"[window] OLED at ~{ppi:.0f} ppi -> {w}x{h}px; set ROBOT_SCREEN_PPI to calibrate",
              file=sys.stderr, flush=True)
        return w, h

    def _build_menu(self, root):
        """Right-click menu for the frameless window: rescale the glass, or close the session."""
        tk = self._tk
        sizes = tk.Menu(root, tearoff=0)
        sizes.add_command(label='True 0.96"', command=lambda: self._resize(self._true_size))
        for k in (2, 3, 4, 6):                       # whole-pixel zoom presets of the 128x64 panel
            sizes.add_command(label=f"{k}x  ({self.width * k}x{self.height * k})",
                              command=lambda k=k: self._resize((self.width * k, self.height * k)))
        self._menu = tk.Menu(root, tearoff=0)
        self._menu.add_cascade(label="Resize", menu=sizes)
        self._menu.add_separator()
        self._menu.add_command(label="Close", command=self._quit)

    def _popup(self, e):
        try:
            self._menu.tk_popup(e.x_root, e.y_root)
        finally:
            self._menu.grab_release()

    def _resize(self, size):
        self._size = size                            # next _tick re-renders at this size
        x, y = self._root.winfo_x(), self._root.winfo_y()
        self._root.geometry(f"{size[0] + 8}x{size[1] + 8}+{x}+{y}")   # +8 for the 4px bezel on each side

    def _quit(self):
        os._exit(0)                                  # close the whole session (daemon Tk can hang a clean exit)

    def _grab(self, e):
        self._drag = (e.x, e.y)                      # where in the window the cursor grabbed

    def _drag_to(self, e):
        dx, dy = self._drag
        self._root.geometry(f"+{e.x_root - dx}+{e.y_root - dy}")

    def _tick(self):
        frame = self._latest
        size = self._size
        if frame is None:
            img = self._Image.new("RGB", size, self._BG)
        else:
            fg = tuple(c * self._bright // 255 for c in self._FG)
            mask = frame.convert("L").point(lambda v: 255 if v else 0)
            lit = self._Image.composite(self._Image.new("RGB", frame.size, fg),
                                        self._Image.new("RGB", frame.size, self._BG), mask)
            img = lit.resize(size, self._Image.NEAREST)
        self._photo = self._ImageTk.PhotoImage(img)   # keep a ref or Tk drops it
        self._label.configure(image=self._photo)
        self._root.after(self._frame_ms, self._tick)


class Display:
    """OLED on BridgeManager's live link. BLE has no in-place reconnect, so a healed drop is a *new*
    Bridge -- rebuild the OLED on it. Render-loop errors are already tolerated by EyeEngine."""

    width, height = 128, 64

    def __init__(self, mgr, *, sda, scl):
        from esplink.drivers.oled import OLED
        self._mgr, self._new = mgr, lambda b: OLED(b, sda=sda, scl=scl)
        self._bridge = mgr.bridge()                 # first connect (raises -> face-only)
        self._oled = self._new(self._bridge)

    def _panel(self):
        b = self._mgr.bridge()                      # live link, reconnecting on demand
        if b is not self._bridge:                   # healed as a new Bridge -> rebind
            self._bridge, self._oled = b, self._new(b)
        return self._oled

    def show(self, image=None):
        self._panel().show(image)

    def contrast(self, value):
        self._panel().contrast(value)               # OLED brightness, 0..255

    def clear(self):
        self._panel().clear()


def connect_display():
    """Open a self-healing, BLE-only bridge + OLED from env. Returns (manager, display)."""
    import esplink
    # ble=True keeps reconnects on Bluetooth; no target = first board found; no password = "esplink"
    mgr = esplink.BridgeManager(name=os.getenv("ROBOT_BLE_TARGET") or None, ble=True,
                                password=os.getenv("ROBOT_PASSWORD"))
    try:
        return mgr, Display(mgr, sda=int(os.getenv("ROBOT_OLED_SDA", "1")),
                            scl=int(os.getenv("ROBOT_OLED_SCL", "2")))
    except Exception:
        mgr.shutdown()                              # board up but no OLED -> don't leak the BLE link
        raise
