# Octet Draw in LibreOffice Writer, Impress and Draw. A double-click on a structure that Octet or ChemDraw made (a PDF
# picture with the drawing's CDXML in it) opens it in an Octet object window. Each Update in Octet puts the new
# picture in its place as one undo step, with its anchor, wrap and alt text kept. Other pictures keep LibreOffice's
# own double-click. The context menu gets Edit in Octet Draw, and Insert gets Octet Drawing for a new one.
#
# The picture's own bytes go into a new folder (mode 0700) under $XDG_RUNTIME_DIR/app/io.github.samchemman.octet-draw/,
# which a Flatpak Octet can read and write. The extension runs `octet --object <folder>/drawing.pdf --app Writer --host
# <document>` (or Impress, Draw; or the Flatpak's Octet), with those fixed arguments, through the user's service manager
# and never through a shell. Octet writes each Update over the file in one step, and an empty `closed` file when its
# window closes. The extension looks at the folder four times a second, as LibreOffice's own external editing does,
# and writes an empty `gone` file when the document closes first. No port, socket or network. Each file from Octet is
# read as hostile: a PDF of 64 MB at most, which LibreOffice's PDF reader opens.
import os
import re
import shutil
import stat
import struct
import subprocess
import tempfile
import threading
import time
import zlib

import uno
import unohelper
from com.sun.star.awt import XCallback, XMouseClickHandler
from com.sun.star.document import XUndoAction
from com.sun.star.lang import XEventListener
from com.sun.star.util import XCloseListener
from com.sun.star.task import XJob, XJobExecutor
from com.sun.star.ui import XContextMenuInterceptor

APP_ID = "io.github.samchemman.octet-draw"
SERVICE = "io.github.samchemman.octet.LibreOffice"
MAX_BYTES = 64 << 20
# What Octet's window needs from the session, when the user's service manager starts it.
PASS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS", "XDG_SESSION_TYPE", "XDG_CURRENT_DESKTOP", "LANG")
# The documents the extension works in, and each program's name for Octet's Update button (Update in Writer).
DOCUMENTS = (("com.sun.star.text.TextDocument", "Writer"), ("com.sun.star.presentation.PresentationDocument", "Impress"), ("com.sun.star.drawing.DrawingDocument", "Draw"))
NOT_FOUND = "LibreOffice cannot find Octet Draw. Open Octet Draw once, then try again."

SESSIONS = []  # the pictures open in Octet
ATTACHED = []  # the views with the double-click and the context menu item
LOCK = threading.Lock()
WATCHER = []  # the thread that looks at the folders, while there are sessions


def prop(name, value):
    p = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    p.Name, p.Value = name, value
    return p


def service(ctx, name, *args):
    if args:
        return ctx.ServiceManager.createInstanceWithArgumentsAndContext(name, args, ctx)
    return ctx.ServiceManager.createInstanceWithContext(name, ctx)


# ---- What Octet can open ----

# The picture's PDF as LibreOffice keeps it: its graphic written in LibreOffice's own form, which for a PDF is "0fdp",
# the length, then the PDF. None for every other picture.
def pdf_of(ctx, graphic):
    try:
        if graphic is None or graphic.MimeType != "application/pdf":
            return None
        stream = service(ctx, "com.sun.star.comp.MemoryStream")
        service(ctx, "com.sun.star.graphic.GraphicProvider").storeGraphic(graphic, (prop("OutputStream", stream), prop("MimeType", "image/x-vclgraphic")))
        stream.seek(0)
        data = bytes(stream.readBytes(None, min(stream.getLength(), MAX_BYTES + 8))[1].value)
    except Exception:
        return None
    if data[:4] != b"0fdp" or len(data) < 8:
        return None
    n = struct.unpack("<I", data[4:8])[0]
    pdf = data[8:8 + n]
    return pdf if len(pdf) == n and pdf.startswith(b"%PDF") else None


# Whether a PDF holds a drawing: a stream marked /Type /Metadata /Subtype /XML (Octet's and ChemDraw's catalog
# /Metadata) whose text starts as CDXML. Octet reads the PDF again with its own limits; this only decides whether a
# double-click is Octet's. At most 2,000 places with the word `stream` (a stream has two: `stream` and `endstream`),
# and the first 4 KB of each stream.
def has_drawing(pdf):
    at, seen = 0, 0
    while seen < 2000:
        at = pdf.find(b"stream", at)
        if at < 0:
            return False
        start, at = at, at + 6
        seen += 1
        if pdf[start - 3:start] == b"end":
            continue
        head = pdf[max(0, start - 2048):start]
        if b"obj" not in head:
            continue
        d = head[head.rfind(b"obj"):]
        if not (re.search(rb"/Type\s*/Meta[Dd]ata\b", d) and re.search(rb"/Subtype\s*/XML\b", d)):
            continue
        data = pdf[at:at + 65536].lstrip(b"\r\n")
        text = data[:4096]
        # Deflated with /FlateDecode, or with no filter: LibreOffice keeps a PDF newer than 1.6 as pdfium saves it at
        # 1.6, which takes the /Filter off this stream.
        if b"/FlateDecode" in d or data[:1] == b"x":
            try:
                text = zlib.decompressobj().decompress(data, 4096)
            except zlib.error:
                continue
        if b"<CDXML" in text or b"<!DOCTYPE CDXML" in text:
            return True
    return False


# The one picture selected: Writer's image, or one image in Impress or Draw.
def selected_picture(controller):
    try:
        sel = controller.getSelection()
        if sel.supportsService("com.sun.star.text.TextGraphicObject"):
            return sel
        if sel.getCount() == 1 and sel.getByIndex(0).supportsService("com.sun.star.drawing.GraphicObjectShape"):
            return sel.getByIndex(0)
    except Exception:
        pass
    return None


# ---- Octet ----

# The program Octet says it is (an AppImage can be anywhere): the path in $XDG_CONFIG_HOME/<Octet's id>/octet-path,
# which Octet writes when it starts. The file is the user's own, only the user can change it, and it is no link. The
# program is a real path (no link in it) to a file that runs, that the user or root owns, and that other users cannot
# change. None if not.
def noted_octet():
    config = os.environ.get("XDG_CONFIG_HOME", "")
    if not os.path.isabs(config):
        config = os.path.expanduser("~/.config")
    try:
        fd = os.open(os.path.join(config, APP_ID, "octet-path"), os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as f:
            st = os.fstat(f.fileno())
            data = f.read(4097)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o022 or len(data) > 4096:
            return None
        path = os.fsdecode(data)
        program = os.lstat(path)
    except (OSError, ValueError):
        return None
    if not os.path.isabs(path) or os.path.realpath(path) != path or not stat.S_ISREG(program.st_mode):
        return None
    if program.st_uid not in (0, os.getuid()) or program.st_mode & 0o002 or not os.access(path, os.X_OK):
        return None
    return path


# Octet as it said it is (an AppImage, or any build), else from the .deb or .rpm, else the Flatpak, else an `octet` on
# the PATH.
def octet():
    noted = noted_octet()
    if noted:
        return [noted]
    if os.access("/usr/bin/octet", os.X_OK):
        return ["/usr/bin/octet"]
    flatpak = shutil.which("flatpak")
    if flatpak and any(os.path.isdir(os.path.join(d, "app", APP_ID)) for d in (os.path.expanduser("~/.local/share/flatpak"), "/var/lib/flatpak")):
        return [flatpak, "run", APP_ID]
    found = shutil.which("octet")
    return [found] if found else None


# A new private folder: in the folder a Flatpak Octet shares with the system, else a temporary folder.
def new_folder():
    run = os.environ.get("XDG_RUNTIME_DIR")
    if not run:
        return tempfile.mkdtemp(prefix="octet-")
    base = os.path.join(run, "app", APP_ID)
    os.makedirs(base, mode=0o700, exist_ok=True)
    st = os.lstat(base)
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid():
        raise OSError("Octet's folder is not the user's own: " + base)
    return tempfile.mkdtemp(prefix="libreoffice-", dir=base)


# A new file: never through a link, and never over a file that is there.
def write_new(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)


# The file as it is now: a new file (Octet's Update renames one over it) or new bytes. None if it is not a file.
def stamp(path):
    try:
        st = os.lstat(path)
    except OSError:
        return None
    return (st.st_ino, st.st_mtime_ns, st.st_size) if stat.S_ISREG(st.st_mode) else None


# The PDF that Octet wrote: 64 MB at most, never through a link.
def read_pdf(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as f:
            if os.fstat(f.fileno()).st_size > MAX_BYTES:
                return None
            data = f.read(MAX_BYTES + 1)
    except OSError:
        return None
    return data if len(data) <= MAX_BYTES and data.startswith(b"%PDF") else None


def message(ctx, controller, text):
    try:
        window = controller.getFrame().getContainerWindow()
        kind = uno.Enum("com.sun.star.awt.MessageBoxType", "WARNINGBOX")
        service(ctx, "com.sun.star.awt.Toolkit").createMessageBox(window, kind, 1, "Octet Draw", text).execute()
    except Exception:
        pass


# Runs `f` on LibreOffice's main thread, where documents change.
class Call(unohelper.Base, XCallback):
    def __init__(self, f):
        self.f = f

    def notify(self, data):
        self.f()


def on_main(ctx, f):
    service(ctx, "com.sun.star.awt.AsyncCallback").addCallback(Call(f), None)


# ---- One picture open in Octet ----

class Session:
    def __init__(self, ctx, controller, shape, at=None):
        self.ctx, self.controller, self.doc, self.shape, self.at = ctx, controller, controller.getModel(), shape, at
        self.folder = new_folder()
        self.path = os.path.join(self.folder, "drawing.pdf")
        self.seen = None  # the file as the extension last read it
        self.gone = False

    # Octet opens the file, or brings its window to the front. False if Octet is not there or does not start: the
    # user hears it. Octet notes its place each time it starts, so an Octet that was moved is found after it opens once.
    def launch(self):
        command = octet()
        if command is None:
            message(self.ctx, self.controller, NOT_FOUND)
            return False
        # The program's name for Octet's Update button (Update in Writer), and the document's.
        args = command + ["--object", self.path]
        try:
            args += next((["--app", name] for service_name, name in DOCUMENTS if self.doc.supportsService(service_name)), [])
            title = self.doc.getTitle()
        except Exception:
            title = "Document"
        # The first 260 characters of the name, which is all Octet keeps of it.
        args += ["--host", title[:260]]
        # Through the user's service manager, as the desktop starts programs, not as LibreOffice's child: Ubuntu
        # confines LibreOffice with AppArmor, and a Flatpak cannot start under it ("bwrap: setting up uid map:
        # Permission denied"). The window's environment goes with it. systemd reads $ in a command as a variable: $$
        # is a $. With no user service manager, Octet starts as LibreOffice's child. KillMode=process: when that Octet
        # ends, the service manager leaves the programs it started (the Octet that starts after an update, a browser
        # for a link).
        manager = shutil.which("systemd-run")
        if manager:
            setenv = ["--setenv=%s=%s" % (k, os.environ[k]) for k in PASS if k in os.environ]
            try:
                if subprocess.run([manager, "--user", "--quiet", "--collect", "--property=KillMode=process"] + setenv + ["--"] + [a.replace("$", "$$") for a in args], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10).returncode == 0:
                    return True
            except (OSError, ValueError, subprocess.TimeoutExpired):
                pass
        env = {k: v for k, v in os.environ.items() if k not in ("LD_LIBRARY_PATH", "LD_PRELOAD")}
        # A start that fails (the program is gone, or the system cannot pass the document's name): the user hears it.
        try:
            child = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True, env=env)
        except (OSError, ValueError):
            message(self.ctx, self.controller, NOT_FOUND)
            return False
        threading.Thread(target=child.wait, daemon=True).start()
        return True

    # Octet's new picture goes in place of the old one, as one undo step. The picture keeps its anchor, wrap, alt text
    # and name, and takes the new drawing's own size, as on Windows.
    def put(self, data):
        if self.gone:
            return
        try:
            stream = service(self.ctx, "com.sun.star.io.SequenceInputStream", uno.ByteSequence(data))
            graphic = service(self.ctx, "com.sun.star.graphic.GraphicProvider").queryGraphic((prop("InputStream", stream),))
            size = graphic.Size100thMM
        except Exception:
            return
        undo = self.doc.getUndoManager()
        try:
            if self.shape is None:
                undo.enterUndoContext("Octet Drawing")
                try:
                    self.shape = self.insert(graphic, size, data)
                finally:
                    undo.leaveUndoContext()
                return
            # Impress and Draw keep no undo step for a changed picture, so the step is Octet's own, in every program.
            before = (self.shape.Graphic, self.shape.Size)
            undo.lock()
            try:
                swap(self.shape, graphic, size)
            finally:
                undo.unlock()
            undo.addUndoAction(Swap(self.shape, before, (graphic, self.shape.Size)))
        except Exception:
            self.went()  # the picture or its document is gone

    # A new drawing. In Writer, in line at the cursor (Writer's Insert > Image would put it over a picture that is
    # selected). In Impress and Draw, LibreOffice's own Insert > Image, for its usual place and size: a picture they add
    # through the API has no undo step. Insert > Image reads a private copy of the PDF checked above. Octet's file can
    # be gone by now (its window closed), or be a link.
    def insert(self, graphic, size, data):
        if self.at is not None:
            shape = self.doc.createInstance("com.sun.star.text.TextGraphicObject")
            shape.AnchorType = uno.Enum("com.sun.star.text.TextContentAnchorType", "AS_CHARACTER")
            swap(shape, graphic, size)
            self.at.getText().insertTextContent(self.at, shape, False)
            return shape
        fd, name = tempfile.mkstemp(suffix=".pdf")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            url = uno.systemPathToFileUrl(name)
            service(self.ctx, "com.sun.star.frame.DispatchHelper").executeDispatch(self.controller.getFrame(), ".uno:InsertGraphic", "", 0, (prop("FileName", url), prop("AsLink", False)))
        finally:
            os.unlink(name)
        return selected_picture(self.controller)

    # The document closed, or the picture is gone: Octet's window says so and keeps the drawing for Save Copy As.
    def went(self):
        if not self.gone:
            self.gone = True
            try:
                write_new(os.path.join(self.folder, "gone"), b"")
            except OSError:
                pass


def swap(shape, graphic, size):
    shape.Graphic = graphic
    if size.Width > 0 and size.Height > 0:
        shape.Size = size


# Edit > Undo and Redo of an Update: the picture and size before it, and after it.
class Swap(unohelper.Base, XUndoAction):
    def __init__(self, shape, before, after):
        self.Title = "Octet Drawing"
        self.shape, self.before, self.after = shape, before, after

    def undo(self):
        swap(self.shape, *self.before)

    def redo(self):
        swap(self.shape, *self.after)


class Closing(unohelper.Base, XCloseListener):
    def __init__(self, session):
        self.session = session

    def queryClosing(self, event, ownership):
        pass

    def notifyClosing(self, event):
        self.session.went()

    def disposing(self, event):
        self.session.went()


def start(session):
    if not session.launch():
        shutil.rmtree(session.folder, ignore_errors=True)
        return
    session.seen = stamp(session.path)
    session.doc.addCloseListener(Closing(session))
    with LOCK:
        SESSIONS.append(session)
        if not WATCHER:
            WATCHER.append(threading.Thread(target=watch, daemon=True))
            WATCHER[0].start()


# Four times a second: each new picture from Octet goes into its document, and a closed window's folder goes. `closed`
# is looked for first: Octet writes the last picture before it.
def watch():
    while True:
        time.sleep(0.25)
        with LOCK:
            sessions = list(SESSIONS)
            if not sessions:
                WATCHER.clear()
                return
        for s in sessions:
            closed = os.path.lexists(os.path.join(s.folder, "closed"))
            now = stamp(s.path)
            if now is not None and now != s.seen:
                s.seen = now
                data = read_pdf(s.path)
                if data is not None:
                    on_main(s.ctx, lambda s=s, data=data: s.put(data))
            if closed:
                with LOCK:
                    SESSIONS.remove(s)
                shutil.rmtree(s.folder, ignore_errors=True)


# Opens the picture in Octet. False if it holds no drawing. A picture open already brings Octet's window to the front.
def edit(ctx, controller, shape):
    with LOCK:
        open_already = [s for s in SESSIONS if s.shape == shape and not s.gone]
    if open_already:
        open_already[0].launch()
        return True
    pdf = pdf_of(ctx, shape.Graphic)
    if pdf is None or not has_drawing(pdf):
        return False
    session = Session(ctx, controller, shape)
    write_new(session.path, pdf)
    start(session)
    return True


# Insert > Octet Drawing: an empty file is a new drawing. In Writer it goes in where the cursor is now, or beside the
# picture selected now. In Impress and Draw it goes on the slide or page in front at the first Update.
def insert(ctx, controller):
    at = None
    if controller.getModel().supportsService("com.sun.star.text.TextDocument"):
        try:
            cursor = controller.getViewCursor()
            at = cursor.getText().createTextCursorByRange(cursor.getStart())
        except Exception:
            anchor = controller.getSelection().getAnchor()
            at = anchor.getText().createTextCursorByRange(anchor)
    session = Session(ctx, controller, None, at)
    write_new(session.path, b"")
    start(session)


# ---- The views ----

class Clicks(unohelper.Base, XMouseClickHandler):
    def __init__(self, ctx, controller):
        self.ctx, self.controller = ctx, controller

    # A double-click with the left button on a drawing: Octet opens it, and LibreOffice does nothing more.
    def mousePressed(self, event):
        if event.ClickCount != 2 or event.Buttons != 1:
            return False
        shape = selected_picture(self.controller)
        try:
            return shape is not None and edit(self.ctx, self.controller, shape)
        except Exception:
            return False

    def mouseReleased(self, event):
        return False

    def disposing(self, event):
        pass


class Menu(unohelper.Base, XContextMenuInterceptor):
    def __init__(self, ctx):
        self.ctx = ctx

    # Edit in Octet Draw, first in the context menu of a drawing.
    def notifyContextMenuExecute(self, event):
        ignored = uno.Enum("com.sun.star.ui.ContextMenuInterceptorAction", "IGNORED")
        try:
            shape = selected_picture(event.Selection)
            pdf = shape and pdf_of(self.ctx, shape.Graphic)
            if not pdf or not has_drawing(pdf):
                return ignored
            menu = event.ActionTriggerContainer
            item = menu.createInstance("com.sun.star.ui.ActionTrigger")
            item.setPropertyValue("Text", "Edit in Octet Draw")
            item.setPropertyValue("CommandURL", "service:" + SERVICE + "?edit")
            line = menu.createInstance("com.sun.star.ui.ActionTriggerSeparator")
            line.setPropertyValue("SeparatorType", 0)
            menu.insertByIndex(0, item)
            menu.insertByIndex(1, line)
            return uno.Enum("com.sun.star.ui.ContextMenuInterceptorAction", "EXECUTE_MODIFIED")
        except Exception:
            return ignored


class Forget(unohelper.Base, XEventListener):
    def disposing(self, event):
        ATTACHED[:] = [c for c in ATTACHED if c != event.Source]


def attach(ctx, controller):
    try:
        if controller is None or any(c == controller for c in ATTACHED):
            return
        if not any(controller.getModel().supportsService(n) for n, _ in DOCUMENTS):
            return
        controller.addMouseClickHandler(Clicks(ctx, controller))
        controller.registerContextMenuInterceptor(Menu(ctx))
        controller.addEventListener(Forget())
        ATTACHED.append(controller)
    except Exception:
        pass


# The job for each new view (Jobs.xcu), and the commands of the menu items (Addons.xcu and the context menu).
class Octet(unohelper.Base, XJob, XJobExecutor):
    def __init__(self, ctx):
        self.ctx = ctx

    def execute(self, args):
        for arg in args:
            if arg.Name == "Environment":
                env = {v.Name: v.Value for v in arg.Value}
                frame, model = env.get("Frame"), env.get("Model")
                attach(self.ctx, frame.getController() if frame else model and model.getCurrentController())
        return None

    def trigger(self, command):
        controller = service(self.ctx, "com.sun.star.frame.Desktop").getCurrentFrame().getController()
        attach(self.ctx, controller)
        if command == "insert":
            insert(self.ctx, controller)
        elif command == "edit":
            shape = selected_picture(controller)
            if shape is not None:
                edit(self.ctx, controller, shape)


g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(Octet, SERVICE, (SERVICE,))
