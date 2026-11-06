"""Cluster view of a project (Computational Chemistry): own Slurm jobs, fetching results over the user's ssh.

Read only by design: the commands below are the only ones ever sent, nothing can submit or cancel a job and the project
file triggers nothing. Host and user live in QSettings, never in a project. No password: key or agent of the user.
"""
from __future__ import annotations

import datetime
import re
import shlex
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath

from PySide6.QtCore import QProcess, QSize, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QPushButton, QSystemTrayIcon, QVBoxLayout, QWidget)

from elucida.app import project as PRJ
from elucida.app import publication as PUB
from elucida.app import style as STYLE
from elucida.app.i18n import T

FETCH = (".out", ".log", ".xyz", ".molden", ".input", ".cube", ".cub", ".spectrum", ".inp")   # gbw/hess: groß, nie
TO_TAB = (".out", ".log", ".xyz", ".molden", ".input", ".cube", ".cub")     # offene Verbindung: direkt im DFT-Tab öffnen
AS_ENTRY = (".out", ".log", ".xyz")                # geschlossenes Ziel: Eintrag im Projekt, der Rest nur als Datei
TICKED = (".out", ".xyz")                          # beim Öffnen eines Ordners vorgewählt
COLOURS = {"RUNNING": "#3B82F6", "COMPLETING": "#3B82F6", "PENDING": "#9CA3AF", "COMPLETED": "#22A06B", "CANCELLED": "#D9A441"}
FAILED_COLOUR = "#E5484D"                          # alle übrigen Slurm-Zustände
POLL_MS = 2 * 60 * 1000          # solange die App offen ist; eine kurze Abfrage über die offene Sammelverbindung
TIMEOUT_MS = 30 * 1000
FETCH_TIMEOUT_MS = 10 * 60 * 1000
DAYS = 7                         # beendete Jobs so weit zurück


def ssh_command(host, user, command):
    """Argumente für ssh. host/user prüfen: ein führendes „-“ wäre sonst eine ssh-Option (ProxyCommand)."""
    for v in (host, user):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", v or ""):
            raise ValueError(T("cluster_bad_login"))
    opts = ["-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=10"]
    if sys.platform != "win32":                    # Windows-OpenSSH kennt keine Sammelverbindung
        opts += ["-o", "ControlMaster=auto", "-o", "ControlPath=~/.ssh/elucida-%C", "-o", "ControlPersist=180"]
    return [*opts, f"{user}@{host}", command]


def remote_dir(text):
    text = (text or "").strip()
    if not text.startswith("/") or re.search(r"[\r\n\0]", text):
        raise ValueError(T("cluster_bad_dir"))
    return text


def jobs_command(today=None):
    since = ((today or datetime.date.today()) - datetime.timedelta(days=DAYS)).isoformat()
    return ("squeue -u \"$USER\" -h -o '%i|%j|%T|%M|%Z'; echo ---; "
            f"sacct -X -n -P -S {since} -o JobID,JobName,State,End,WorkDir")


def files_command(folder):
    return f"find {shlex.quote(remote_dir(folder))} -maxdepth 1 -type f -printf '%s|%f\\n'"


def fetch_command(folder, name):
    return f"cat -- {shlex.quote(str(PurePosixPath(remote_dir(folder)) / name))}"


def parse_jobs(text):
    """Ausgabe von jobs_command -> Jobs, laufende zuerst; live = noch in der Warteschlange."""
    head, _, tail = text.partition("---")
    jobs = {}
    for ln in head.splitlines():
        p = ln.strip().split("|")
        if len(p) == 5:
            jobs[p[0]] = dict(id=p[0], name=p[1], state=p[2], time=p[3], dir=p[4], live=True)
    for ln in tail.splitlines():
        p = ln.strip().split("|")
        if len(p) == 5 and p[0] not in jobs:
            jobs[p[0]] = dict(id=p[0], name=p[1], state=p[2].split()[0] if p[2] else "", time=p[3], dir=p[4], live=False)
    return sorted(jobs.values(), key=lambda j: not j["live"])


def parse_files(text):
    """find-Ausgabe -> [(Name, Bytes)]. Die Gegenseite ist nicht vertrauenswürdig: nur reine Dateinamen, bekannte Endungen."""
    out = []
    for ln in text.splitlines():
        size, _, name = ln.partition("|")
        if size.isdigit() and name and "/" not in name and "\\" not in name and name not in (".", "..") \
                and Path(name).suffix.lower() in FETCH:
            out.append((name, int(size)))
    return sorted(out)


def mac_notification(title, text):
    """Argumente für osascript. Texte nur als Parameter: Jobnamen kommen vom Cluster und dürfen kein Skript werden."""
    return ["-e", "on run argv", "-e", "display notification (item 2 of argv) with title (item 1 of argv)",
            "-e", "end run", title, text]


def state_colour(state):
    return COLOURS.get(state, FAILED_COLOUR)


def dot(colour, size=10):
    d = QLabel()
    d.setFixedSize(size, size)
    d.setStyleSheet(f"background: {colour}; border-radius: {size // 2}px;")
    return d


def add_to_project(target, path):
    """Geholte Datei in ein geschlossenes Projekt (Verbindung oder Reaktionspfad). -> True, wenn sie als Rechnung eingetragen
    wurde; alles andere liegt nur in data/dft."""
    from elucida.tabs import dft as DFT
    p = PRJ.import_file(target, path, PRJ.data_sub("dft"))
    if Path(p).suffix.lower() not in AS_ENTRY:
        return False
    try:
        DFT.read_xyz(p) if Path(p).suffix.lower() == ".xyz" else DFT.read_calc(p)
    except Exception:
        return False                                     # z. B. slurm-123.out: Datei behalten, nicht als Rechnung eintragen
    state = PRJ.load(target)
    dft = state.setdefault("dft", {})
    entry = DFT.new_entry(p)
    dft.setdefault("entries", []).append(entry)
    dft["current"] = entry["uid"]
    PRJ.save(target, state)
    return True


class ClusterCard(QFrame):
    """Kleine Statuskarte unter der Pfadliste: kostet dem Canvas keine Höhe, Klick öffnet die Ansicht."""

    def __init__(self, page):
        super().__init__(objectName="card")
        self.page = page
        self.setCursor(Qt.PointingHandCursor)
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 12, 16, 12)
        self.mark = dot(COLOURS["PENDING"])
        row.addWidget(self.mark)
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(QLabel(T("cluster_title"), objectName="cardTitle"))
        self.text = QLabel(T("cluster_card_idle"))
        self.text.setProperty("formlabel", True)
        col.addWidget(self.text)
        row.addLayout(col, 1)
        row.addWidget(QLabel("›"))

    def mouseReleaseEvent(self, ev):
        self.page.show_cluster()

    def set_status(self, colour, text):
        self.mark.setStyleSheet(f"background: {colour}; border-radius: 5px;")
        self.text.setText(text)


class JobRow(QWidget):
    def __init__(self, job):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(10)
        row.addWidget(dot(state_colour(job["state"])))
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(QLabel(f"<b>{_esc(job['name'])}</b>"))
        where = QLabel(_esc(job["dir"]))
        where.setProperty("formlabel", True)
        col.addWidget(where)
        row.addLayout(col, 1)
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(QLabel(_esc(job["state"].capitalize()), alignment=Qt.AlignRight))
        when = QLabel(_esc(job["time"].replace("T", " ")[:16]), alignment=Qt.AlignRight)
        when.setProperty("formlabel", True)
        col.addWidget(when)
        row.addLayout(col)


def _esc(text):
    import html
    return html.escape(text or "")                       # Jobnamen kommen vom Cluster, nie als Rich Text deuten


class ClusterPage(QWidget):
    def __init__(self, pub_page):
        super().__init__()
        self.pub = pub_page
        self.main = pub_page.main
        self.live = None                               # Job-IDs der letzten Abfrage
        self.busy = False
        self.jobs = []
        self.folder = ""
        self.tray = None
        s = self.main.settings
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 4, 4, 4)
        v.setSpacing(10)
        head = QHBoxLayout()
        head.addWidget(QLabel(f"<b>{T('cluster_title')}</b>", objectName="recentHead"))
        self.lbl_login = QLabel()
        self.lbl_login.setProperty("formlabel", True)
        head.addWidget(self.lbl_login, 1)
        self.btn_access = QPushButton(T("cluster_access"), clicked=lambda: self.access.setVisible(not self.access.isVisible()))
        self.btn_refresh = QPushButton(T("cluster_refresh"), clicked=self.refresh)
        self.btn_refresh.setIcon(STYLE.icon("reset"))
        head.addWidget(self.btn_access)
        head.addWidget(self.btn_refresh)
        v.addLayout(head)
        self.access = QFrame(objectName="card")
        form = QFormLayout(self.access)
        form.setContentsMargins(16, 12, 16, 12)
        self.ed_host = QLineEdit(s.value("cluster/host", ""), placeholderText=T("cluster_host_ph"))
        self.ed_user = QLineEdit(s.value("cluster/user", ""), placeholderText=T("cluster_user_ph"))
        form.addRow(T("cluster_host"), self.ed_host)
        form.addRow(T("cluster_user"), self.ed_user)
        self.cb_notify = QCheckBox(T("cluster_notify"), checked=s.value("cluster/notify", True, type=bool))
        self.cb_notify.setToolTip(T("cluster_notify_tip"))
        self.cb_notify.toggled.connect(lambda on: s.setValue("cluster/notify", on))
        form.addRow(self.cb_notify)
        v.addWidget(self.access)
        body = QHBoxLayout()
        body.setSpacing(12)
        self.lst_jobs = QListWidget()
        self.lst_jobs.setFrameShape(QFrame.NoFrame)
        self.lst_jobs.setSpacing(2)
        self.lst_jobs.setStyleSheet("QListWidget::item:selected { background: rgba(59, 130, 246, 0.18); border-radius: 6px; }")
        self.lst_jobs.currentRowChanged.connect(self.job_selected)
        body.addWidget(self.lst_jobs, 5)
        detail = QFrame(objectName="card")
        d = QVBoxLayout(detail)
        d.setContentsMargins(16, 12, 16, 16)
        d.setSpacing(8)
        self.lbl_job = QLabel(T("cluster_pick_job"), objectName="cardTitle")
        d.addWidget(self.lbl_job)
        row = QHBoxLayout()
        self.ed_dir = QLineEdit(s.value("cluster/dir", ""), placeholderText=T("cluster_dir_ph"))
        self.btn_files = QPushButton(T("cluster_files"), clicked=self.list_files)
        row.addWidget(self.ed_dir, 1)
        row.addWidget(self.btn_files)
        d.addLayout(row)
        self.lst = QListWidget()
        d.addWidget(self.lst, 1)
        row = QHBoxLayout()
        lab = QLabel(T("cluster_target"))
        lab.setProperty("formlabel", True)
        row.addWidget(lab)
        self.cmb_target = QComboBox()
        row.addWidget(self.cmb_target, 1)
        d.addLayout(row)
        self.btn_fetch = QPushButton(T("cluster_fetch"), clicked=self.fetch)
        self.btn_fetch.setProperty("accent", True)
        d.addWidget(self.btn_fetch)
        body.addWidget(detail, 4)
        v.addLayout(body, 1)
        self.status = STYLE.HintLabel("")
        self.status.setWordWrap(True)
        v.addWidget(self.status)
        self.timer = QTimer(self, interval=POLL_MS)
        self.timer.timeout.connect(self.poll)
        self.timer.start()                             # läuft, solange die App offen ist, unabhängig von der Ansicht
        QTimer.singleShot(0, self.poll)
        self.show_login()

    def configured(self):
        return bool(self.ed_host.text().strip() and self.ed_user.text().strip())

    def show_login(self):
        self.access.setVisible(not self.configured())
        self.lbl_login.setText(f"{self.ed_user.text().strip()}@{self.ed_host.text().strip()}" if self.configured() else "")

    def poll(self):
        if self.configured() and not self.busy:
            self.refresh()

    def showEvent(self, ev):
        super().showEvent(ev)
        self.fill_targets()

    # -- ssh ---------------------------------------------------------------------------
    def run(self, command, done, out_file=None, timeout=TIMEOUT_MS):
        """Einen Lesebefehl ausführen, ohne die Oberfläche anzuhalten; done(Text) nur bei Erfolg."""
        if self.busy:                                  # Abfrage im Hintergrund läuft noch: kurz danach dran
            return QTimer.singleShot(300, lambda: self.run(command, done, out_file, timeout))
        ssh = shutil.which("ssh")
        if not ssh:
            return self.fail(T("cluster_no_ssh"))
        try:
            args = ssh_command(self.ed_host.text().strip(), self.ed_user.text().strip(), command)
        except ValueError as ex:
            return self.fail(str(ex))
        s = self.main.settings
        s.setValue("cluster/host", self.ed_host.text().strip())
        s.setValue("cluster/user", self.ed_user.text().strip())
        s.setValue("cluster/dir", self.ed_dir.text().strip())
        self.show_login()
        self.busy = True
        p = QProcess(self)
        if out_file:
            p.setStandardOutputFile(str(out_file))
        limit = QTimer(p, singleShot=True, interval=timeout)
        limit.timeout.connect(p.kill)

        def finished(code, _status):
            self.busy = False
            err = bytes(p.readAllStandardError()).decode("utf-8", "replace").strip()
            out = "" if out_file else bytes(p.readAllStandardOutput()).decode("utf-8", "replace")
            p.deleteLater()
            if code == 0:
                done(out)
            else:
                self.fail(T("cluster_failed", err=err.splitlines()[-1] if err else T("cluster_timeout")))
        p.finished.connect(finished)
        p.start(ssh, args)
        limit.start()

    def say(self, text):
        self.status.setText(text)

    def notify(self, jobs):
        """Einblendung in der App; ist sie nicht im Vordergrund, zusätzlich Mitteilung des Systems und Hinweis im Dock."""
        text = T("cluster_ended", jobs=jobs)
        self.main.statusBar().showMessage(text, 15000)
        if not self.cb_notify.isChecked() or self.main.isActiveWindow() or QGuiApplication.platformName() == "offscreen":
            return
        QApplication.alert(self.main)
        if sys.platform == "darwin":
            QProcess.startDetached("osascript", mac_notification("Elucida", text))
        elif QSystemTrayIcon.isSystemTrayAvailable():
            if self.tray is None:
                self.tray = QSystemTrayIcon(self.main.windowIcon(), self)
                self.tray.show()
            self.tray.showMessage("Elucida", text)

    def fail(self, text):
        self.say(text)
        self.pub.cluster_card.set_status(FAILED_COLOUR, T("cluster_card_off"))

    # -- Abfragen ----------------------------------------------------------------------
    def refresh(self):
        self.run(jobs_command(), self.show_jobs)

    def show_jobs(self, text):
        self.jobs = parse_jobs(text)
        now = {j["id"] for j in self.jobs if j["live"]}
        ended = [j for j in self.jobs if self.live is not None and j["id"] in self.live - now]
        self.live = now
        names = [self.cmb_target.itemText(i).lower() for i in range(self.cmb_target.count())]
        self.jobs.sort(key=lambda j: (not j["live"], not any(n and n in (j["dir"] + j["name"]).lower() for n in names)))
        keep = self.lst_jobs.currentRow()
        self.lst_jobs.blockSignals(True)
        self.lst_jobs.clear()
        for j in self.jobs:
            it = QListWidgetItem()
            row = JobRow(j)
            it.setSizeHint(QSize(0, row.sizeHint().height()))
            self.lst_jobs.addItem(it)
            self.lst_jobs.setItemWidget(it, row)
        self.lst_jobs.setCurrentRow(keep if 0 <= keep < len(self.jobs) else -1)
        self.lst_jobs.blockSignals(False)
        done = len(self.jobs) - len(now)
        self.say(T("cluster_ended", jobs=", ".join(j["name"] for j in ended)) if ended else T("cluster_status", n=len(now), m=done))
        if ended:
            self.notify(", ".join(f"{j['name']} ({j['state'].capitalize()})" for j in ended))
        self.pub.cluster_card.set_status(COLOURS["RUNNING"] if now else COLOURS["COMPLETED"] if ended else COLOURS["PENDING"],
                                         T("cluster_card", n=len(now), m=done))

    def job_selected(self, row):
        if 0 <= row < len(self.jobs):
            j = self.jobs[row]
            self.lbl_job.setText(j["name"])
            self.ed_dir.setText(j["dir"])
            for i in range(self.cmb_target.count()):          # Vorschlag: Ziel, dessen Name im Ordner oder Jobnamen steht
                if self.cmb_target.itemText(i).lower() in (j["dir"] + j["name"]).lower():
                    self.cmb_target.setCurrentIndex(i)
                    break
            self.list_files()

    def list_files(self):
        try:
            self.run(files_command(self.ed_dir.text()), self.show_files)
        except ValueError as ex:
            self.say(str(ex))

    def show_files(self, text):
        self.lst.clear()
        files = parse_files(text)
        for name, size in files:
            it = QListWidgetItem(f"{name}  ·  " + (f"{size / 1e6:.1f} MB" if size >= 1e5 else f"{size / 1e3:.1f} kB"))
            it.setData(Qt.UserRole, (name, size))
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if Path(name).suffix.lower() in TICKED else Qt.Unchecked)
            self.lst.addItem(it)
        self.folder = self.ed_dir.text().strip()
        self.say(T("cluster_files_found", n=len(files)) if files else T("cluster_files_none"))

    # -- Holen -------------------------------------------------------------------------
    def fill_targets(self):
        """Verbindungen und Reaktionspfade des Projekts: Rechnungen gehören selten nur zu einem Molekül."""
        from elucida.app.reaction_paths import directory
        keep = self.cmb_target.currentData()
        self.cmb_target.clear()
        if not self.pub.pdir:
            return
        for d in self.pub.compound_dirs():
            self.cmb_target.addItem(PUB.compound_name(d), str(Path(d).resolve()))
        for item in PUB.load(self.pub.pdir).get("reaction_paths", []):
            self.cmb_target.addItem(item["name"], str(directory(self.pub.pdir, item["uid"])))
        self.cmb_target.setCurrentIndex(max(0, self.cmb_target.findData(keep)))

    def fetch(self):
        todo = [self.lst.item(i).data(Qt.UserRole) for i in range(self.lst.count()) if self.lst.item(i).checkState() == Qt.Checked]
        target = self.cmb_target.currentData()
        if not todo or not target:
            return self.say(T("cluster_pick"))
        self.tmp = tempfile.TemporaryDirectory()
        self.todo, self.got, self.loose, self.target = todo, [], [], target
        self.next_file()

    def next_file(self):
        if not self.todo:
            self.tmp.cleanup()
            text = T("cluster_fetched", n=len(self.got), target=self.cmb_target.currentText())
            return self.say(text + (" " + T("cluster_loose", files=", ".join(self.loose)) if self.loose else ""))
        name, size = self.todo.pop(0)
        path = Path(self.tmp.name) / name
        self.say(T("cluster_fetching", name=name))
        self.run(fetch_command(self.folder, name), lambda _: self.fetched(path, size), out_file=path, timeout=FETCH_TIMEOUT_MS)

    def live_tab(self):
        """Offener DFT-Tab des Ziels: dort eintragen, sonst überschreibt er das Projekt beim nächsten Speichern."""
        ws = self.pub.path_workspace
        if ws and str(ws.host.project_dir.resolve()) == self.target:
            return ws.host.tab
        if self.main.project_dir and str(Path(self.main.project_dir).resolve()) == self.target:
            return self.main.dft_tab
        return None

    def fetched(self, path, size):
        if path.stat().st_size != size:                  # abgebrochene Übertragung nie als Ergebnis übernehmen
            self.tmp.cleanup()
            return self.say(T("cluster_incomplete", name=path.name))
        tab = self.live_tab()
        if tab is not None and path.suffix.lower() in TO_TAB:
            tab.load_xyz(str(path))
        elif tab is not None:
            tab.main.import_file(str(path), PRJ.data_sub("dft"))
            self.loose.append(path.name)
        elif not add_to_project(self.target, path):
            self.loose.append(path.name)
        self.got.append(path.name)
        self.next_file()
