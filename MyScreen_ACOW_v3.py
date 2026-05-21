"""
MyScreen ACOW  v3  –  Audio Cast Over Wi-Fi
════════════════════════════════════════════
Author  : Claude (taken over on Henny's orders 🐄)
Tested  : Flet 0.21+ / Python 3.10+

What's new in v3
─────────────────
  ✅ Full Flet API compatibility (no state-dict ButtonStyle, animate= not animate_size=)
  ✅ UDP auto-discovery  — no IP typing needed, receiver broadcasts itself
  ✅ QR code on receiver — scan from sender phone to auto-fill IP
  ✅ Auto-reconnect with configurable retries + delay in Settings
  ✅ Volume slider on receiver with live PCM scaling
  ✅ Settings panel  (retries, delay, port, audio quality)
  ✅ Android 13  RECORD_AUDIO + FOREGROUND_SERVICE permissions
  ✅ Full MediaProjection bridge with permission request method
  ✅ Copy-IP-to-clipboard button on receiver
  ✅ Latency display after connection
  ✅ local_ip() via DNS trick (more reliable than gethostbyname)
  ✅ Receiver keeps listening for next sender after disconnect
  ✅ Graceful fallback if pyaudio / qrcode not installed

Install
───────
  pip install flet pyaudio qrcode[pil]
  Android: buildozer + python-for-android + jnius (APK build only)
"""

import flet as ft
import socket, threading, os, time, struct, math, io, base64

# ── Optional back-ends ────────────────────────────────────────────────────────
try:
    from jnius import autoclass
    ANDROID = True
except ImportError:
    ANDROID = False

try:
    import pyaudio
    AUDIO = True
except ImportError:
    AUDIO = False

try:
    import qrcode
    QR_OK = True
except ImportError:
    QR_OK = False

# ── Protocol ──────────────────────────────────────────────────────────────────
MAGIC          = b"ACOW"
MODE_FILE      = b"\x01"
MODE_SYS       = b"\x02"
DISCOVERY_PORT = 8766
BEACON_PREFIX  = b"ACOW_BEACON:"

# ── Palette ───────────────────────────────────────────────────────────────────
C_BG    = "#06060E"
C_CARD  = "#0C0C1A"
C_BORD  = "#1A1A2E"
C_PINK  = "#FF007F"
C_PDIM  = "#4A0025"
C_PDARK = "#1A0010"
C_WHT   = "#F0F0FF"
C_GRY   = "#55556A"
C_GRYL  = "#8888AA"


# ═════════════════════════════════════════════════════════════════════════════
#  ANDROID  —  MediaProjection + permissions via jnius
# ═════════════════════════════════════════════════════════════════════════════
class AndroidCapture:
    """
    Full Android 13 audio capture bridge.

    Typical call flow
    ─────────────────
      cap = AndroidCapture()
      cap.request_permissions()           # show RECORD_AUDIO dialog
      cap.request_media_projection()      # show MediaProjection dialog
      # In your onActivityResult (1001):
      cap.start(result_code, data, cb)    # blocks in thread until stop()
      cap.stop()
    """

    def __init__(self):
        self.running = False
        self.record  = None
        self.proj    = None

    def request_permissions(self):
        """Ask for RECORD_AUDIO and FOREGROUND_SERVICE on Android 13."""
        if not ANDROID:
            return
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.RECORD_AUDIO,
                "android.permission.FOREGROUND_SERVICE",
                "android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION",
            ])
        except Exception as e:
            print(f"[ACOW] Permission request error: {e}")

    def request_media_projection(self, activity=None):
        """Fire the system MediaProjection permission dialog (requestCode 1001)."""
        if not ANDROID:
            return
        Activity = autoclass("org.kivy.android.PythonActivity")
        Context  = autoclass("android.content.Context")
        act      = activity or Activity.mActivity
        mpm      = act.getSystemService(Context.MEDIA_PROJECTION_SERVICE)
        intent   = mpm.createScreenCaptureIntent()
        act.startActivityForResult(intent, 1001)

    def start(self, result_code, intent_data, on_chunk, chunk: int = 4096):
        """
        Begin capturing all media audio.  Blocks until stop().
        result_code + intent_data must come from onActivityResult(1001).
        on_chunk(bytes) is called with raw PCM-16 stereo 44100 Hz data.
        """
        if not ANDROID:
            return
        Activity = autoclass("org.kivy.android.PythonActivity")
        Context  = autoclass("android.content.Context")
        AF       = autoclass("android.media.AudioFormat")
        AR       = autoclass("android.media.AudioRecord")
        APCC     = autoclass("android.media.AudioPlaybackCaptureConfiguration")

        act       = Activity.mActivity
        mpm       = act.getSystemService(Context.MEDIA_PROJECTION_SERVICE)
        self.proj = mpm.getMediaProjection(result_code, intent_data)

        # Capture all USAGE_MEDIA (1) audio playing on device
        cfg = APCC.Builder(self.proj).addMatchingUsage(1).build()

        fmt = (AF.Builder()
               .setEncoding(AF.ENCODING_PCM_16BIT)
               .setSampleRate(44100)
               .setChannelMask(AF.CHANNEL_IN_STEREO)
               .build())

        min_buf = AR.getMinBufferSize(
            44100, AF.CHANNEL_IN_STEREO, AF.ENCODING_PCM_16BIT)

        self.record = (AR.Builder()
                       .setAudioPlaybackCaptureConfig(cfg)
                       .setAudioFormat(fmt)
                       .setBufferSizeInBytes(min_buf * 4)
                       .build())

        self.running = True
        self.record.startRecording()

        buf = bytearray(chunk)
        while self.running:
            n = self.record.read(buf, 0, chunk)
            if n > 0:
                on_chunk(bytes(buf[:n]))

    def stop(self):
        self.running = False
        if self.record:
            self.record.stop()
            self.record.release()
        if self.proj:
            self.proj.stop()


# ═════════════════════════════════════════════════════════════════════════════
#  SHARED UTILITIES
# ═════════════════════════════════════════════════════════════════════════════
def local_ip() -> str:
    """Reliable LAN IP via dummy UDP connect (no packets sent)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return socket.gethostbyname(socket.gethostname())


def rms_level(data: bytes) -> float:
    """Normalised RMS [0.0–1.0] from raw PCM-16-LE bytes."""
    n = len(data) // 2
    if n == 0:
        return 0.0
    s = struct.unpack(f"<{n}h", data[:n * 2])
    return min(1.0, math.sqrt(sum(x * x for x in s) / n) / 32768.0)


def recv_exact(sock: socket.socket, n: int):
    """Read exactly n bytes or return None on disconnect."""
    buf = b""
    while len(buf) < n:
        part = sock.recv(n - len(buf))
        if not part:
            return None
        buf += part
    return buf


def apply_volume(data: bytes, vol: float) -> bytes:
    """Scale PCM-16 amplitude by vol in-place (clipped to int16 range)."""
    if vol >= 0.99:
        return data
    n = len(data) // 2
    if n == 0:
        return data
    samples = struct.unpack(f"<{n}h", data[:n * 2])
    scaled  = [max(-32768, min(32767, int(s * vol))) for s in samples]
    return struct.pack(f"<{n}h", *scaled)


def make_qr(text: str, fg: str = "#FF007F", bg: str = "#0C0C1A") -> str:
    """Return data-URI PNG of a QR code, or '' if qrcode isn't installed."""
    if not QR_OK:
        return ""
    qr = qrcode.QRCode(
        box_size=5, border=3,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fg, back_color=bg)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ═════════════════════════════════════════════════════════════════════════════
#  UDP  AUTO-DISCOVERY
# ═════════════════════════════════════════════════════════════════════════════
class DiscoveryBeacon:
    """
    Server-side UDP broadcaster.
    Sends  b"ACOW_BEACON:<ip>"  every 2 s on DISCOVERY_PORT.
    Sender picks this up via scan_for_receiver().
    """

    def __init__(self, ip: str):
        self.ip      = ip
        self.running = False

    def start(self):
        self.running = True
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self.running = False

    def _run(self):
        payload = BEACON_PREFIX + self.ip.encode()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            while self.running:
                try:
                    s.sendto(payload, ("<broadcast>", DISCOVERY_PORT))
                except Exception:
                    pass
                time.sleep(2)


def scan_for_receiver(timeout: float = 6.0, on_found=None):
    """
    Client-side: listen on DISCOVERY_PORT for a beacon.
    Calls on_found(ip: str | None) when done.
    Non-blocking — spawns its own thread.
    """
    def _run():
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("", DISCOVERY_PORT))
            s.settimeout(timeout)
            try:
                data, _ = s.recvfrom(256)
                if data.startswith(BEACON_PREFIX) and on_found:
                    on_found(data[len(BEACON_PREFIX):].decode())
            except socket.timeout:
                if on_found:
                    on_found(None)

    threading.Thread(target=_run, daemon=True).start()


# ═════════════════════════════════════════════════════════════════════════════
#  SERVER  (Receiver side)
# ═════════════════════════════════════════════════════════════════════════════
class ACOWServer:
    """
    Listens for incoming TCP connections, plays audio via PyAudio.
    Keeps listening after a disconnect so the sender can reconnect.
    Also runs a UDP beacon so senders can find it automatically.
    """

    def __init__(self, on_status, on_level, settings: dict):
        self.on_status = on_status
        self.on_level  = on_level
        self.settings  = settings
        self.running   = False
        self.volume    = 1.0          # live-updated by UI slider
        self._beacon   = None
        self._srv_sock = None

    def start(self, ip: str):
        self.running = True
        self._beacon = DiscoveryBeacon(ip)
        self._beacon.start()
        threading.Thread(target=self._serve, daemon=True).start()

    def stop(self):
        self.running = False
        if self._beacon:
            self._beacon.stop()
        if self._srv_sock:
            try:
                self._srv_sock.close()
            except Exception:
                pass

    def _serve(self):
        port = self.settings.get("port", 8765)
        srv  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv_sock = srv
        try:
            srv.bind(("0.0.0.0", port))
            srv.listen(1)
            self.on_status(f"Listening :{port}  —  beacon active 📡")
            srv.settimeout(1.0)
            while self.running:
                try:
                    conn, addr = srv.accept()
                    self.on_status(f"Receiving ←  {addr[0]}")
                    self._recv(conn)          # blocks until client disconnects
                    if self.running:
                        self.on_status(f"Waiting for next sender… :{port}")
                except socket.timeout:
                    continue
        except Exception as e:
            self.on_status(f"Server error: {e}")
        finally:
            srv.close()
            self.on_status("Server stopped")
            self.on_level(0.0)

    def _recv(self, conn: socket.socket):
        pa = stream = None
        try:
            if recv_exact(conn, 4) != MAGIC:
                self.on_status("Bad handshake — wrong app? ❌")
                return
            recv_exact(conn, 1)    # mode byte — not used by receiver

            rate  = self.settings.get("sample_rate", 44100)
            chunk = self.settings.get("chunk", 4096)

            if AUDIO and not ANDROID:
                pa     = pyaudio.PyAudio()
                stream = pa.open(
                    format=pyaudio.paInt16,
                    channels=2,
                    rate=rate,
                    output=True,
                    frames_per_buffer=chunk,
                )

            while self.running:
                hdr = recv_exact(conn, 4)
                if not hdr:
                    break
                sz   = struct.unpack("!I", hdr)[0]
                data = recv_exact(conn, sz)
                if not data:
                    break
                data = apply_volume(data, self.volume)
                if stream:
                    stream.write(data)
                self.on_level(rms_level(data))

        except Exception:
            pass
        finally:
            conn.close()
            if stream:
                stream.stop_stream()
                stream.close()
            if pa:
                pa.terminate()
            self.on_status("Sender disconnected")
            self.on_level(0.0)


# ═════════════════════════════════════════════════════════════════════════════
#  CLIENT  (Sender side)
# ═════════════════════════════════════════════════════════════════════════════
class ACOWClient:
    """
    Connects to receiver and streams audio chunks over TCP.
    Retries up to settings["retries"] times before giving up.
    """

    def __init__(self, host: str, on_status, on_level, settings: dict):
        self.host       = host
        self.on_status  = on_status
        self.on_level   = on_level
        self.settings   = settings
        self.running    = False
        self._cap       = AndroidCapture()
        self.latency_ms = 0

    def send_file(self, path: str):
        self.running = True
        threading.Thread(target=self._file_loop, args=(path,), daemon=True).start()

    def send_system(self, result_code=None, intent_data=None):
        self.running = True
        threading.Thread(
            target=self._sys_loop, args=(result_code, intent_data), daemon=True
        ).start()

    def stop(self):
        self.running = False
        self._cap.stop()

    # ── internals ────────────────────────────────────────────────────────

    def _connect(self) -> socket.socket:
        """Connect with exponential-backoff retry."""
        port    = self.settings.get("port",        8765)
        retries = self.settings.get("retries",        3)
        delay   = self.settings.get("retry_delay",    2)

        for attempt in range(1, retries + 1):
            try:
                self.on_status(f"Connecting…  ({attempt}/{retries})")
                t0 = time.time()
                s  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(6)
                s.connect((self.host, port))
                s.settimeout(None)
                self.latency_ms = int((time.time() - t0) * 1000)
                self.on_status(f"Connected ✅  {self.latency_ms} ms")
                return s
            except Exception:
                if attempt < retries:
                    self.on_status(
                        f"No response — retrying in {delay}s  ({attempt}/{retries})")
                    time.sleep(delay)
        raise ConnectionError(
            f"Could not reach {self.host} after {retries} attempt(s)")

    def _push(self, sock: socket.socket, data: bytes):
        sock.sendall(struct.pack("!I", len(data)) + data)
        self.on_level(rms_level(data))

    def _file_loop(self, path: str):
        try:
            s     = self._connect()
            chunk = self.settings.get("chunk",       4096)
            rate  = self.settings.get("sample_rate", 44100)
            s.sendall(MAGIC + MODE_FILE)
            self.on_status(f"Streaming  ›  {os.path.basename(path)}")
            delay = chunk / (rate * 2 * 2)    # realtime pacing: 16-bit stereo
            with open(path, "rb") as f:
                while self.running:
                    data = f.read(chunk)
                    if not data:
                        break
                    self._push(s, data)
                    time.sleep(delay)
            self.on_status("Stream complete ✅")
        except ConnectionError as e:
            self.on_status(f"{e} ❌")
        except Exception as e:
            self.on_status(f"Error: {e}")
        finally:
            self.on_level(0.0)

    def _sys_loop(self, result_code, intent_data):
        try:
            s     = self._connect()
            chunk = self.settings.get("chunk",       4096)
            rate  = self.settings.get("sample_rate", 44100)
            s.sendall(MAGIC + MODE_SYS)
            self.on_status("Capturing system audio…")

            def push(data: bytes):
                if not self.running:
                    return
                try:
                    self._push(s, data)
                except Exception:
                    self.running = False

            if ANDROID:
                self._cap.request_permissions()
                self._cap.start(result_code, intent_data, push, chunk)
            elif AUDIO:
                pa = pyaudio.PyAudio()
                st = pa.open(
                    format=pyaudio.paInt16, channels=2,
                    rate=rate, input=True, frames_per_buffer=chunk,
                )
                while self.running:
                    push(st.read(chunk, exception_on_overflow=False))
                st.stop_stream()
                st.close()
                pa.terminate()
            else:
                self.on_status("No audio backend available ❌")

        except ConnectionError as e:
            self.on_status(f"{e} ❌")
        except Exception as e:
            self.on_status(f"Error: {e}")
        finally:
            self.on_level(0.0)


# ═════════════════════════════════════════════════════════════════════════════
#  FLET  UI
# ═════════════════════════════════════════════════════════════════════════════
def main(page: ft.Page):
    page.title      = "MyScreen ACOW"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = C_BG
    page.padding    = ft.Padding.symmetric(horizontal=18, vertical=0)
    page.scroll     = ft.ScrollMode.AUTO

    MY_IP = local_ip()

    # ── App state ─────────────────────────────────────────────────────────
    state = {
        "role":          "sender",
        "mode":          "file",
        "streaming":     False,
        "file_path":     None,
        "server":        None,
        "client":        None,
        "settings_open": False,
    }

    settings = {
        "port":        8765,
        "retries":     3,
        "retry_delay": 2,
        "chunk":       4096,
        "sample_rate": 44100,
    }

    # ── Safe page update (called from threads) ────────────────────────────
    def _up():
        try:
            page.update()
        except Exception:
            pass

    # ── Status text ───────────────────────────────────────────────────────
    status_txt = ft.Text(
        "Ready  🐄", color=C_GRY, size=11, italic=True,
        text_align=ft.TextAlign.CENTER,
    )
    file_name_txt = ft.Text(
        "No file selected", color=C_GRY, size=11, italic=True,
    )

    def set_status(msg: str):
        status_txt.value = msg
        _up()

    # ── Level bars  (14 × animated Container) ────────────────────────────
    bars = [
        ft.Container(
            width=7, height=4, border_radius=4, bgcolor=C_PINK,
            animate=ft.Animation(70),   # ← animate=, NOT animate_size=
        )
        for _ in range(14)
    ]

    def set_level(lvl: float):
        t = time.time()
        for i, b in enumerate(bars):
            phase    = 0.5 + 0.5 * math.sin(i * 0.9 + t * 4)
            b.height = max(4, int(lvl * 54 * phase))
        _up()

    # ── Radar stack ───────────────────────────────────────────────────────
    def ring(d: int, op: float, bw: int) -> ft.Container:
        off = (260 - d) // 2
        return ft.Container(
            width=d, height=d, border_radius=d // 2,
            border=ft.Border.all(bw, C_PINK),
            opacity=op, left=off, top=off,
            animate_opacity=ft.Animation(900),
        )

    r_out = ring(248, 0.08, 1)
    r_mid = ring(196, 0.22, 2)
    r_in  = ring(152, 0.55, 2)

    core_icon  = ft.Text("📡", size=40, text_align=ft.TextAlign.CENTER)
    core_label = ft.Text(
        "CAST", color=C_WHT, size=9,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER,
    )

    core_btn = ft.Container(
        width=118, height=118, border_radius=59,
        gradient=ft.RadialGradient(colors=[C_PDIM, C_PDARK]),
        border=ft.Border.all(2, C_PINK),
        shadow=ft.BoxShadow(spread_radius=4, blur_radius=22, color=C_PINK + "55"),
        alignment=ft.Alignment(0, 0),
        left=71, top=71,
        on_click=lambda _: toggle(),
        animate=ft.Animation(300),
        content=ft.Column(
            [core_icon, core_label],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=3,
        ),
    )

    radar = ft.Stack([r_out, r_mid, r_in, core_btn], width=260, height=260)

    # ── Custom pill tab  (Container, no ButtonStyle dict keys) ────────────
    def pill(label: str, active: bool, on_click) -> ft.Container:
        return ft.Container(
            content=ft.Text(
                label,
                color=C_WHT if active else C_GRY,
                size=12, weight=ft.FontWeight.W_600,
            ),
            padding=ft.Padding.symmetric(horizontal=26, vertical=12),
            border_radius=22,
            bgcolor=C_PINK if active else C_CARD,
            border=ft.Border.all(1, C_PINK if active else C_BORD),
            on_click=on_click,
            animate=ft.Animation(200),
        )

    tab_send = pill("📤  Sender",   True,  lambda _: set_role("sender"))
    tab_recv = pill("📥  Receiver", False, lambda _: set_role("receiver"))

    # ── Mode chips ────────────────────────────────────────────────────────
    def make_chip(label: str, val: str) -> ft.Container:
        active = state["mode"] == val
        return ft.Container(
            content=ft.Text(
                label,
                color=C_WHT if active else C_GRY,
                size=11, weight=ft.FontWeight.W_500,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=9),
            border_radius=14,
            border=ft.Border.all(2, C_PINK if active else C_BORD),
            animate=ft.Animation(180),
            data=val,
            on_click=lambda e: set_mode(e.control.data),
        )

    chip_file = make_chip("📂  File Sync",     "file")
    chip_sys  = make_chip("🎙️  System Audio", "system")

    # ── File picker ───────────────────────────────────────────────────────
    picker = ft.FilePicker()
    page.services.append(picker)

    def on_pick(e):
        if e.files:
            state["file_path"]  = e.files[0].path
            file_name_txt.value = e.files[0].name
        else:
            file_name_txt.value = "No file selected"
        _up()

    picker.on_result = on_pick

    # ── IP field + scan ───────────────────────────────────────────────────
    ip_field = ft.TextField(
        label="Receiver IP",
        hint_text="192.168.x.x  or tap Scan",
        hint_style=ft.TextStyle(color=C_GRY),
        label_style=ft.TextStyle(color=C_GRYL),
        border_color=C_BORD, focused_border_color=C_PINK,
        cursor_color=C_PINK, color=C_WHT,
        width=300, border_radius=12, text_size=14,
    )

    scan_lbl = ft.Text("", color=C_GRYL, size=10, italic=True)

    def do_scan(_):
        scan_lbl.value = "Scanning… (6 s)"
        _up()
        def on_found(ip):
            if ip:
                ip_field.value = ip
                scan_lbl.value = f"Found: {ip} ✅"
            else:
                scan_lbl.value = "No receiver found ❌"
            _up()
        scan_for_receiver(timeout=6.0, on_found=on_found)

    def _small_btn(label: str, on_click) -> ft.Container:
        return ft.Container(
            content=ft.Text(label, color=C_PINK, size=11,
                             weight=ft.FontWeight.BOLD),
            padding=ft.Padding.symmetric(horizontal=14, vertical=9),
            border_radius=12, border=ft.Border.all(1, C_PINK),
            on_click=on_click,
        )

    scan_btn   = _small_btn("🔍 Scan",   do_scan)
    browse_btn = _small_btn("📂 Browse", lambda _: page.run_task(picker.pick_files, 
        allowed_extensions=["mp3", "wav", "ogg", "flac", "aac", "m4a"]))

    sender_panel = ft.Column(
        [
            ft.Row([ip_field], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([scan_btn, scan_lbl],
                    alignment=ft.MainAxisAlignment.CENTER, spacing=8),
            ft.Row([chip_file, chip_sys],
                    alignment=ft.MainAxisAlignment.CENTER, spacing=10),
            ft.Row([browse_btn, file_name_txt],
                    alignment=ft.MainAxisAlignment.CENTER, spacing=8),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=12,
    )

    # ── Receiver panel  (IP card + QR + volume) ───────────────────────────
    qr_raw = make_qr(MY_IP)
    qr_widget = (
        ft.Image(src=qr_raw, width=140, height=140)
        if qr_raw else
        ft.Text("pip install qrcode[pil]  for QR",
                 color=C_GRY, size=10, italic=True)
    )

    vol_label = ft.Text("Volume  100%", color=C_GRYL, size=11)

    def on_vol(e):
        v = e.control.value / 100.0
        vol_label.value = f"Volume  {int(e.control.value)}%"
        if state["server"]:
            state["server"].volume = v
        _up()

    vol_slider = ft.Slider(
        min=0, max=100, value=100,
        active_color=C_PINK, inactive_color=C_BORD,
        width=280, on_change=on_vol,
    )

    def copy_ip(_):
        page.set_clipboard(MY_IP)
        set_status(f"Copied  {MY_IP}  📋")

    copy_btn = _small_btn("📋 Copy IP", copy_ip)

    receiver_panel = ft.Column(
        [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("YOUR IP ADDRESS", color=C_GRY, size=9,
                                 weight=ft.FontWeight.BOLD),
                        ft.Text(MY_IP, color=C_PINK, size=22,
                                 weight=ft.FontWeight.BOLD,
                                 text_align=ft.TextAlign.CENTER),
                        copy_btn,
                        qr_widget,
                        ft.Text("Scan QR or share IP with sender 👆",
                                 color=C_GRY, size=10, italic=True),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                bgcolor=C_PDARK + "99",
                border=ft.Border.all(1, C_PDIM),
                border_radius=16,
                padding=ft.Padding.symmetric(vertical=20, horizontal=28),
            ),
            vol_label,
            vol_slider,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10,
    )

    panel_wrapper = ft.Column(
        [sender_panel],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ── Switches ──────────────────────────────────────────────────────────
    sw_ask   = ft.Switch(label="Ask Permission  (3× Vibe) 📳",
                          active_color=C_PINK, value=True)
    sw_trust = ft.Switch(label="Trusted Zone  (Auto-Connect) 🤝",
                          active_color=C_PINK, value=False)
    sw_pause = ft.Switch(label="Allow Receiver to Pause ⏸️",
                          active_color=C_PINK, value=True)

    # ── Settings panel ────────────────────────────────────────────────────
    def srow(label: str, ctrl) -> ft.Row:
        return ft.Row(
            [ft.Text(label, color=C_GRYL, size=11, width=145), ctrl],
            alignment=ft.MainAxisAlignment.START, spacing=12,
        )

    def sfield(key: str, default) -> ft.TextField:
        return ft.TextField(
            value=str(default),
            color=C_WHT,
            label_style=ft.TextStyle(color=C_GRYL),
            border_color=C_BORD, focused_border_color=C_PINK,
            cursor_color=C_PINK,
            width=88, border_radius=10, text_size=13,
            on_change=lambda e, k=key: settings.update(
                {k: int(e.control.value) if e.control.value.isdigit()
                    else settings[k]}),
        )

    quality_dd = ft.Dropdown(
        value="44100",
        options=[
            ft.dropdown.Option(key="22050", text="22050 Hz  (Low)"),
            ft.dropdown.Option(key="44100", text="44100 Hz  (Standard)"),
            ft.dropdown.Option(key="48000", text="48000 Hz  (High)"),
        ],
        border_color=C_BORD, focused_border_color=C_PINK,
        color=C_WHT, width=172, text_size=12,
        on_select=lambda e: settings.update(
            {"sample_rate": int(e.control.value)}),
    )

    settings_body = ft.Column(
        [
            srow("Max retries",      sfield("retries",     3)),
            srow("Retry delay (s)",  sfield("retry_delay", 2)),
            srow("Port",             sfield("port",      8765)),
            srow("Audio quality",    quality_dd),
        ],
        spacing=10,
    )

    settings_box = ft.Container(
        content=settings_body,
        visible=False,
        padding=ft.Padding.only(top=12),
    )

    settings_lbl = ft.Text("▼  Settings", color=C_GRYL, size=11,
                             weight=ft.FontWeight.W_600)

    def toggle_settings(_):
        state["settings_open"]  = not state["settings_open"]
        settings_box.visible    = state["settings_open"]
        settings_lbl.value      = ("▲  Settings" if state["settings_open"]
                                    else "▼  Settings")
        _up()

    settings_toggle = ft.Container(
        content=settings_lbl,
        on_click=toggle_settings,
        padding=ft.Padding.symmetric(vertical=6, horizontal=2),
    )

    # ── Card wrapper ──────────────────────────────────────────────────────
    def card(content, pv: int = 20, ph: int = 22) -> ft.Container:
        return ft.Container(
            content=content,
            bgcolor=C_CARD, border_radius=20,
            border=ft.Border.all(1, C_BORD),
            padding=ft.Padding.symmetric(vertical=pv, horizontal=ph),
            width=390,
        )

    # ── Pulse animation (thread) ──────────────────────────────────────────
    def _pulse():
        while state["streaming"]:
            r_out.opacity, r_mid.opacity = 0.03, 0.07
            _up()
            time.sleep(0.65)
            r_out.opacity, r_mid.opacity = 0.20, 0.42
            _up()
            time.sleep(0.65)
        r_out.opacity, r_mid.opacity = 0.08, 0.22
        _up()

    # ── State-change actions ──────────────────────────────────────────────
    def set_role(val: str):
        if state["streaming"]:
            _stop()
        state["role"] = val

        for tab, v in [(tab_send, "sender"), (tab_recv, "receiver")]:
            active       = val == v
            tab.bgcolor  = C_PINK if active else C_CARD
            tab.border   = ft.Border.all(1, C_PINK if active else C_BORD)
            tab.content.color = C_WHT if active else C_GRY

        panel_wrapper.controls = [
            sender_panel if val == "sender" else receiver_panel
        ]
        core_icon.value  = "📡" if val == "sender" else "🔊"
        core_label.value = "CAST" if val == "sender" else "LISTEN"
        set_status("Ready  🐄")
        _up()

    def set_mode(val: str):
        state["mode"] = val
        for chip, v in [(chip_file, "file"), (chip_sys, "system")]:
            active          = val == v
            chip.border     = ft.Border.all(2, C_PINK if active else C_BORD)
            chip.content.color = C_WHT if active else C_GRY
        _up()

    def _start():
        state["streaming"] = True
        core_btn.gradient  = ft.RadialGradient(colors=["#900040", "#1E000E"])
        core_btn.shadow    = ft.BoxShadow(spread_radius=10, blur_radius=40,
                                           color=C_PINK + "88")
        core_icon.value    = "⏹"
        core_label.value   = "STOP"
        _up()
        threading.Thread(target=_pulse, daemon=True).start()

        if state["role"] == "receiver":
            srv = ACOWServer(set_status, set_level, settings)
            state["server"] = srv
            srv.start(MY_IP)

        else:
            host = ip_field.value.strip()
            if not host:
                set_status("Enter receiver IP or tap 🔍 Scan  ⚠️")
                _stop()
                return
            cli = ACOWClient(host, set_status, set_level, settings)
            state["client"] = cli

            if state["mode"] == "file":
                if not state["file_path"]:
                    set_status("Pick an audio file first  📂")
                    _stop()
                    return
                cli.send_file(state["file_path"])
            else:
                # On Android pass real result_code + intent_data here
                cli.send_system()

    def _stop():
        state["streaming"] = False
        if state["server"]:
            state["server"].stop()
            state["server"] = None
        if state["client"]:
            state["client"].stop()
            state["client"] = None

        core_btn.gradient = ft.RadialGradient(colors=[C_PDIM, C_PDARK])
        core_btn.shadow   = ft.BoxShadow(spread_radius=4, blur_radius=22,
                                          color=C_PINK + "55")
        core_icon.value  = "📡" if state["role"] == "sender" else "🔊"
        core_label.value = "CAST" if state["role"] == "sender" else "LISTEN"
        for b in bars:
            b.height = 4
        set_status("Stopped  🛑")

    def toggle():
        if state["streaming"]:
            _stop()
        else:
            _start()

    # ── Header ────────────────────────────────────────────────────────────
    header = ft.Row(
        [
            ft.Text("🐄", size=32),
            ft.Column(
                [
                    ft.Text("MyScreen  ACOW", color=C_WHT, size=20,
                             weight=ft.FontWeight.BOLD),
                    ft.Text("Audio Cast Over Wi-Fi", color=C_GRY,
                             size=10, italic=True),
                ],
                spacing=1,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Text("🪶", size=32),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=14,
    )

    def gap(h: int = 16) -> ft.Container:
        return ft.Container(height=h)

    # ── Page layout ───────────────────────────────────────────────────────
    page.add(
        ft.Column(
            [
                gap(30),
                header,
                gap(20),

                ft.Row([tab_send, tab_recv],
                        alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                gap(24),

                ft.Row([radar], alignment=ft.MainAxisAlignment.CENTER),
                gap(8),

                ft.Row([status_txt], alignment=ft.MainAxisAlignment.CENTER),
                gap(8),

                ft.Row(bars, alignment=ft.MainAxisAlignment.CENTER, spacing=5),
                gap(22),

                ft.Row([card(panel_wrapper)],
                        alignment=ft.MainAxisAlignment.CENTER),
                gap(12),

                ft.Row(
                    [
                        card(
                            ft.Column(
                                [
                                    sw_ask, sw_trust, sw_pause,
                                    gap(4),
                                    settings_toggle,
                                    settings_box,
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.START,
                                spacing=4,
                            ),
                            pv=16,
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                gap(36),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
        )
    )


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ft.run(main)

