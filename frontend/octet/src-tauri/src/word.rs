// Edit Picture from Word on the Mac (plan step 2 and 3, decision 0023's object window). Word for Mac runs no OLE
// servers, so Octet asks Word through Apple Events, on the user's command only (File > Edit Picture from Word, the
// Service "Edit in Octet Draw", or a double-click in Word when Settings allows it, below):
// - The picture selected in Word is copied to the clipboard, and paste's reader takes the CDXML from its PDF. The
//   user's clipboard is saved first and put back after.
// - A hidden bookmark marks the picture (or Word's cursor, for a new drawing). The object window opens on the drawing.
// - Update puts the new picture in the bookmark's place, at its own size, with the old picture's alt text. Word gets
//   the picture as Copy gives it: Office's own copy when Octet can make it, then the PDF, both with the CDXML in them
//   (clipboard::mac_picture). Word pastes it into a document of its own first, then the picture goes into the user's
//   document in one step, so one Undo in Word puts the old picture back.
// - The bookmark stays in the document: making or removing one is an Undo step in Word of its own.
//
// The events go only to Word, by its bundle id. The scripts are fixed text; what changes goes in as arguments, never
// into the script. What Word gives is read as hostile: the PDF through paste's 64 MB limit and export's reader, the
// document's name through host_name.
use std::cell::{Cell, RefCell};
use std::io::Write;
use std::process::{Command, Stdio};
use std::ptr::NonNull;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Mutex, OnceLock, TryLockError};
use std::time::{Duration, Instant};

use objc2::rc::Retained;
use objc2::runtime::AnyObject;
use objc2_app_kit::{NSEvent, NSEventMask};
use tauri::AppHandle;

use crate::clipboard::mac as clip;

// One borrow of the clipboard at a time, and one script at a time.
static BUSY: Mutex<()> = Mutex::new(());
static APP: OnceLock<AppHandle> = OnceLock::new();

// Edit Picture from Word: the selection's kind, where it starts and the document's name, one a line. A picture is
// copied to the clipboard. "busy": Word's scripting gives missing values. Seen when a script started Word, which then
// stays hidden until it comes to the front once; a click in Word ends it.
const EDIT: &str = r#"on run argv
	if not (application id "com.microsoft.Word" is running) then return "none"
	tell application id "com.microsoft.Word"
		with timeout of 10 seconds
			if (count of documents) is 0 then return "none"
			set s to selection
			set n to name of document of s
			if n is missing value then return "busy"
			set k to selection type of s
			if k is selection inline shape then
				if (count of inline shapes of s) is not 1 then return "none"
				set startAt to selection start of s
				copy object (text object of inline shape 1 of s)
				return "picture" & linefeed & startAt & linefeed & n
			end if
			if k is selection ip then
				set startAt to selection start of s
				return "new" & linefeed & startAt & linefeed & n
			end if
		end timeout
	end tell
	return "none"
end run"#;

// The hidden bookmark (argument 1) on the selected picture, or at the cursor (argument 2: "picture" or "new"), if the
// selection is still that and still starts where EDIT read it (argument 3). EDIT and MARK are two runs, and the user
// can select another picture between them: that picture gets no bookmark, so Update never replaces it.
const MARK: &str = r#"on run argv
	set b to item 1 of argv
	set k to item 2 of argv
	set startAt to item 3 of argv
	tell application id "com.microsoft.Word"
		with timeout of 10 seconds
			set s to selection
			set startNow to selection start of s
			if (startNow as text) is not startAt then return "none"
			if k is "picture" and (selection type of s is selection inline shape) then
				set r to text object of inline shape 1 of s
			else if k is "new" and (selection type of s is selection ip) then
				set r to text object of s
			else
				return "none"
			end if
			make new bookmark at (document of s) with properties {name:b, text object:r}
		end timeout
	end tell
	return "ok"
end run"#;

// Update: the picture on the clipboard replaces the picture at the bookmark (argument 1), in the document that has it.
// Word's own Paste takes the first type it reads (Office's copy, else the PDF): the script names no type, and reads
// the pasted picture as the document's first inline picture, whatever file Word keeps for it.
// Argument 2 "1": the picture is in the document. A new drawing's bookmark stays empty at the cursor, and its picture
// is the character after it. No picture there (deleted, or text typed in its place): "lost", so no text is replaced.
// Only the picture is replaced, so text typed into the bookmark next to it stays. Argument 3: the document's name as
// Word gave it last, or empty. No open document has the bookmark: "lost" if a document of that name is open (the
// picture was deleted, or an Undo in Word took the bookmark away), else "gone" (the document is closed). Returns the
// document's name, "gone", "lost" or "busy". The picture stays selected if it was. Each command waits 10 s for Word
// at most (a dialog open in Word), so the clipboard is never borrowed for long.
const UPDATE: &str = r#"on run argv
	set b to item 1 of argv
	set placed to (item 2 of argv) is "1"
	set h to item 3 of argv
	if not (application id "com.microsoft.Word" is running) then return "gone"
	tell application id "com.microsoft.Word"
		with timeout of 10 seconds
			set n to missing value
			repeat with i from 1 to (count of documents)
				set x to document i
				if (name of x) is missing value then return "busy"
				if exists bookmark b of x then
					set n to name of x
					exit repeat
				end if
			end repeat
			if n is missing value then
				if h is not "" and (exists document h) then return "lost"
				return "gone"
			end if
			set d to document n
			set m to bookmark b of d
			if m is missing value then return "busy"
			set r to text object of m
			set at0 to start of bookmark of m
			if placed and (empty of m) then set r to create range d start at0 end (at0 + 1)
			set alt to ""
			try
				set alt to alternative text of inline shape 1 of r
				if placed then set r to text object of inline shape 1 of r
			on error
				if placed then return "lost"
			end try
			set s to selection
			set picked to (name of document of s is n) and (selection start of s is start of content of r) and (selection end of s is end of content of r)
			set t to make new document
			try
				paste object (text object of t)
				set p to inline shape 1 of t
				set alternative text of p to alt
				make new bookmark at t with properties {name:b, text object:(text object of p)}
				set formatted text of r to formatted text of (text object of bookmark b of t)
			on error e number k
				close t saving no
				error e number k
			end try
			close t saving no
			if picked then
				set m to bookmark b of d
				if empty of m then
					select (create range d start at0 end (at0 + 1))
				else
					select (text object of m)
				end if
			end if
			return n
		end timeout
	end tell
end run"#;

// Close and Return: Word comes to the front.
const BACK: &str = r#"if application id "com.microsoft.Word" is running then tell application id "com.microsoft.Word" to activate"#;

#[derive(Debug, PartialEq, Eq)]
pub enum Fail {
    Denied, // the user did not allow Octet to control Word (System Settings > Privacy & Security > Automation)
    Gone,   // the document is closed, or Word quit
    Lost,   // the document is open, and the picture or its bookmark is no longer in it
    Busy,   // Word did not answer
    Failed,
}

// What Edit Picture from Word found: the document's name, the drawing (empty for a new one), whether it is a picture
// in the document already, and its bookmark.
pub struct Found {
    pub host: String,
    pub oct: String,
    pub placed: bool,
    pub mark: String,
}

// The script's answer, or why it failed, from the error number osascript gives last: errAEEventNotPermitted (-1743),
// errAETimeout (-1712), and the program not running (procNotFound -600, connectionInvalid -609).
fn run(script: &str, args: &[&str]) -> Result<String, Fail> {
    let mut child = Command::new("/usr/bin/osascript").arg("-").args(args).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn().map_err(|_| Fail::Failed)?;
    child.stdin.take().ok_or(Fail::Failed)?.write_all(script.as_bytes()).map_err(|_| Fail::Failed)?;
    let out = child.wait_with_output().map_err(|_| Fail::Failed)?;
    if out.status.success() {
        return Ok(String::from_utf8_lossy(&out.stdout).trim_end().to_string());
    }
    let err = String::from_utf8_lossy(&out.stderr);
    Err(match number(&err) {
        Some(-1743) => Fail::Denied,
        Some(-1712) => Fail::Busy,
        Some(-600 | -609) => Fail::Gone,
        _ => {
            // The crash log on this computer (crashlog.rs), as Windows' objects log theirs.
            if let Some(app) = APP.get() {
                let _ = crate::crashlog::log_error(app.clone(), format!("Word: {}", err.trim()), false);
            }
            Fail::Failed
        }
    })
}

// The error number at the end of osascript's message: "…: execution error: Not authorized … (-1743)".
fn number(err: &str) -> Option<i32> {
    let e = err.trim_end();
    let open = e.strip_suffix(')')?.rfind('(')?;
    e[open + 1..e.len() - 1].parse().ok()
}

// A bookmark name of Octet's: hidden (it starts with _), 40 characters at most, letters, digits and _ only, and new
// each time, so a bookmark a crash left behind is never taken for another.
fn new_mark() -> String {
    let t = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map_or(0, |d| d.as_nanos() as u64);
    format!("_Octet_{:016x}", t ^ ((std::process::id() as u64) << 48))
}

const WORD: &str = "com.microsoft.Word";

// Word is running.
fn running() -> bool {
    objc2::rc::autoreleasepool(|_| objc2_app_kit::NSRunningApplication::runningApplicationsWithBundleIdentifier(&objc2_foundation::NSString::from_str(WORD)).count() > 0)
}

// Edit Picture from Word, on a thread of its own: the selected picture's drawing (None: nothing Octet can edit).
// marks: the bookmarks of the pictures open in object windows.
fn find(marks: &[String]) -> Result<Option<Pick>, Fail> {
    // Word closed or not installed: a beep, with no Apple Event and no clipboard borrowed.
    if !running() {
        return Ok(None);
    }
    let _one = BUSY.lock().unwrap_or_else(|e| e.into_inner());
    // A picture that is open in an object window already: that window, as a double-click in Word gives it, and never a
    // second window on one picture. Word is asked only when such a window is open. If Word does not answer this, the
    // read below says why.
    if !marks.is_empty() {
        let marks: Vec<&str> = marks.iter().map(String::as_str).collect();
        if let Ok(answer) = run(PICKED, &marks) {
            if let Some(("open", mark)) = answer.split_once('\n') {
                return Ok(Some(Pick::Front(mark.to_string())));
            }
        }
    }
    Ok(read(true)?.map(Pick::Open))
}

// EDIT's answer for a picture or a cursor, in its three lines: the kind, where the selection starts, and the
// document's name. None for any other answer. The start goes back to Word as MARK's argument, so only digits pass,
// nine at most.
fn parts(answer: &str) -> Option<(&str, &str, &str)> {
    let mut lines = answer.splitn(3, '\n');
    let (kind, at, host) = (lines.next()?, lines.next()?, lines.next().unwrap_or(""));
    (!at.is_empty() && at.len() <= 9 && at.bytes().all(|b| b.is_ascii_digit())).then_some((kind, at, host))
}

// The name Word gave last for the document that has each bookmark. Update gives it to Word, which tells a closed
// document from a picture that is no longer in an open one by it. The newest 64 bookmarks: an older one's document
// counts as closed.
static DOCS: Mutex<Vec<(String, String)>> = Mutex::new(Vec::new());
const DOCS_MOST: usize = 64;

fn remember(mark: &str, name: &str) {
    let mut docs = DOCS.lock().unwrap_or_else(|e| e.into_inner());
    docs.retain(|(m, _)| m != mark);
    if docs.len() >= DOCS_MOST {
        docs.remove(0);
    }
    docs.push((mark.to_string(), name.to_string()));
}

fn document(mark: &str) -> String {
    DOCS.lock().unwrap_or_else(|e| e.into_inner()).iter().find(|(m, _)| m == mark).map(|(_, name)| name.clone()).unwrap_or_default()
}

// The selected picture's drawing, with BUSY held. new: Word's cursor with nothing selected gives a new drawing.
fn read(new: bool) -> Result<Option<Found>, Fail> {
    let pb = clip::general();
    let (saved, before) = (clip::save(&pb), pb.changeCount());
    let answer = run(EDIT, &[]);
    // Word copied the picture: paste's reader takes it, and the user's clipboard goes back. It goes back even if the
    // clipboard changed again while Octet read it: Word may write twice, and the user rarely copies in that moment.
    let copied = pb.changeCount() != before;
    let oct = if copied { clip::drawing(&pb) } else { None };
    if copied {
        clip::restore(&pb, &saved);
    }
    let answer = answer?;
    if answer == "busy" {
        return Err(Fail::Busy);
    }
    let Some((kind, at, host)) = parts(&answer) else { return Ok(None) };
    let (oct, placed) = match kind {
        "picture" => match oct {
            Some(o) => (o, true),
            None => return Ok(None),
        },
        "new" if new => (String::new(), false),
        _ => return Ok(None),
    };
    let mark = new_mark();
    if run(MARK, &[&mark, kind, at])? != "ok" {
        return Ok(None);
    }
    let host = crate::ole::host_name(host);
    remember(&mark, &host);
    Ok(Some(Found { host, oct, placed, mark }))
}

// The picture Update gives Word, for a drawing's SVG and CDXML: the Mac's picture types as Copy puts them on
// (clipboard::mac_picture: Office's own copy when Octet can make it, then the PDF). An object window's session keeps
// a picture as one run of bytes (objects.rs), so each type goes in as its name's length, its name, its bytes' length
// and its bytes (lengths as 8 bytes).
pub fn picture(svg: &str, cdxml: &str) -> Result<Vec<u8>, String> {
    let mut out = Vec::new();
    for (name, bytes) in crate::clipboard::mac_picture(svg, Some(cdxml))? {
        for part in [name.as_bytes(), &bytes] {
            out.extend((part.len() as u64).to_le_bytes());
            out.extend(part);
        }
    }
    Ok(out)
}

// Clipboard managers skip a copy that has this type (http://nspasteboard.org).
const TRANSIENT: &str = "org.nspasteboard.TransientType";

// The types in `picture` (word::picture's bytes) in their order, then the transient mark. None for other bytes.
fn types(picture: &[u8]) -> Option<Vec<(&str, &[u8])>> {
    fn part<'a>(rest: &mut &'a [u8]) -> Option<&'a [u8]> {
        let n = usize::try_from(u64::from_le_bytes(rest.get(..8)?.try_into().ok()?)).ok()?;
        let (part, after) = rest[8..].split_at_checked(n)?;
        *rest = after;
        Some(part)
    }
    let (mut rest, mut out) = (picture, Vec::new());
    while !rest.is_empty() {
        out.push((std::str::from_utf8(part(&mut rest)?).ok()?, part(&mut rest)?));
    }
    out.push((TRANSIENT, &[][..]));
    Some(out)
}

// Update: `picture` (word::picture's bytes) replaces the picture at the bookmark `mark`. The document's name (it
// changes with Save As), else why not. The picture's types go on the clipboard with nothing else, marked transient,
// and the user's clipboard goes back after.
pub fn put(mark: &str, placed: bool, picture: &[u8]) -> Result<String, Fail> {
    let _one = BUSY.lock().unwrap_or_else(|e| e.into_inner());
    let pb = clip::general();
    let saved = clip::save(&pb);
    if !types(picture).is_some_and(|t| clip::write(&pb, &t).is_ok()) {
        clip::restore(&pb, &saved);
        return Err(Fail::Failed);
    }
    let ours = pb.changeCount();
    let answer = run(UPDATE, &[mark, if placed { "1" } else { "0" }, &document(mark)]);
    if pb.changeCount() == ours {
        clip::restore(&pb, &saved);
    }
    let name = placed_in(&answer?)?;
    remember(mark, &name);
    Ok(name)
}

// UPDATE's answer: the document's name, or why the picture is not in it.
fn placed_in(answer: &str) -> Result<String, Fail> {
    match answer {
        "gone" => Err(Fail::Gone),
        "lost" => Err(Fail::Lost),
        "busy" => Err(Fail::Busy),
        name => Ok(crate::ole::host_name(name)),
    }
}

// Close and Return to <document>.
pub fn back() {
    let _ = run(BACK, &[]);
}

// File > Edit Picture from Word and the Service: an object window for the picture selected in Word, or for a new
// drawing at Word's cursor. A picture that is open in an object window already brings that window to the front. A
// selection that is neither, or a picture with no drawing in it, gives a beep.
pub fn edit(app: &AppHandle) {
    let app = app.clone();
    tauri::async_runtime::spawn(async move {
        let marks = crate::objects::word_marks(&app);
        match tauri::async_runtime::spawn_blocking(move || find(&marks)).await.unwrap_or(Err(Fail::Failed)) {
            Ok(Some(Pick::Open(found))) => crate::objects::open_word(&app, found).await,
            Ok(Some(Pick::Front(mark))) => crate::objects::front_word(&app, &mark).await,
            Ok(None) => beep(&app),
            Err(f) => tell(&app, &f, None),
        }
    });
}

#[tauri::command]
pub fn word_edit(app: AppHandle) {
    edit(&app);
}

fn beep(app: &AppHandle) {
    let _ = app.run_on_main_thread(|| objc2_app_kit::NSBeep());
}

// Why Octet cannot edit or update the picture, as the page and the alert say it. `host`: the document, for Update.
pub fn message(f: &Fail, host: Option<&str>) -> String {
    match (f, host) {
        (Fail::Denied, _) => "Octet Draw is not allowed to control Microsoft Word.".into(),
        (Fail::Busy, _) => "Microsoft Word does not answer. Click in the Word document, then try again.".into(),
        (Fail::Gone, Some(h)) => format!("{h} is closed. Save a copy to keep this drawing."),
        (Fail::Lost, Some(h)) => format!("Octet cannot find this picture in {h}. Save a copy to keep this drawing."),
        (_, Some(h)) => format!("Octet cannot update {h}. Try again."),
        (_, None) => "Octet cannot open this picture from Word.".into(),
    }
}

// An alert. When the user did not allow Octet to control Word, its button opens System Settings at Automation.
pub fn tell(app: &AppHandle, f: &Fail, host: Option<&str>) {
    use tauri_plugin_dialog::{DialogExt, MessageDialogButtons, MessageDialogKind};
    let text = match f {
        Fail::Denied => format!("{} Allow it in Privacy & Security > Automation.", message(f, host)),
        _ => message(f, host),
    };
    let dialog = app.dialog().message(text).title(crate::ole::APP).kind(MessageDialogKind::Warning);
    if *f != Fail::Denied {
        return dialog.show(|_| {});
    }
    dialog.buttons(MessageDialogButtons::OkCancelCustom("Open System Settings".into(), "Cancel".into())).show(|open| {
        if open {
            let _ = crate::open_external("x-apple.systempreferences:com.apple.preference.security?Privacy_Automation");
        }
    });
}

// The Service "Edit in Octet Draw" (NSServices in Info.plist): macOS starts Octet if it is not running, and calls
// editInOctet:userData:error: on Tao's application delegate, which is the services provider.
pub fn install(app: &AppHandle) {
    use objc2::runtime::{AnyClass, AnyObject, Imp, Sel};

    extern "C" fn service(_: &AnyObject, _: Sel, _: *mut AnyObject, _: *mut AnyObject, _: *mut *mut AnyObject) {
        if let Some(app) = APP.get() {
            edit(app);
        }
    }
    let _ = APP.set(app.clone());
    let (Some(class), Some(mtm)) = (AnyClass::get(c"TaoAppDelegateParent"), objc2::MainThreadMarker::new()) else { return };
    type Method = extern "C" fn(&AnyObject, Sel, *mut AnyObject, *mut AnyObject, *mut *mut AnyObject);
    let ns = objc2_app_kit::NSApplication::sharedApplication(mtm);
    // SAFETY: the function takes the method's arguments (the delegate, the selector, the pasteboard, the user data and
    // the error out-pointer) and returns nothing, as the type string "v@:@@^@" says. class_addMethod never replaces a
    // method tao has. The provider is the application's own delegate, which lives as long as the application.
    unsafe {
        let imp: Imp = std::mem::transmute(service as Method);
        objc2::ffi::class_addMethod(class as *const AnyClass as *mut AnyClass, objc2::sel!(editInOctet:userData:error:), imp, c"v@:@@^@".as_ptr());
        let delegate: Option<objc2::rc::Retained<AnyObject>> = objc2::msg_send![&*ns, delegate];
        if let Some(d) = delegate {
            ns.setServicesProvider(Some(&d));
        }
    }
}

// ---------------------------------------------------------------------------------------------------------------
// Double-click in Word (Settings > General > Word, off until the user turns it on: before then Octet watches no mouse
// and sends Word nothing for a click). Word for Mac tells no other program about a double-click, so while the setting
// is on, Octet watches the mouse: a global monitor of left mouse-downs, which macOS gives with no permission (Apple
// asks for Accessibility only to monitor keys; tried on macOS 27.2). The monitor reads the click count and the bundle
// id of the program in front. It never reads where a click was, or a key, and sends nothing anywhere.
// - No Apple Event goes out unless Word is in front and the click is a double-click's second, once a second at most:
//   a triple-click or a burst of clicks asks Word once.
// - Octet asks Word whether one inline picture is selected (PICKED, no clipboard). Only then is it read, as Edit
//   Picture from Word reads it.
// - A picture with a drawing in it (Octet's or ChemDraw's CDXML) opens in an object window. A picture open in one
//   already brings that window to the front.
// - Anything else does nothing: no beep, and the clipboard as it was. Word's own double-click (its Picture Format
//   tab) goes ahead.
// - A user who did not allow Octet to control Word gets no alert here: a double-click in Word is not a command to
//   Octet. File > Edit Picture from Word and Update show the alert.

// One inline picture selected: "picture", or "open" and the bookmark (an argument: those of the object windows whose
// picture is in the document) that holds it. An empty bookmark holds the character after it, as in UPDATE.
const PICKED: &str = r#"on run argv
	if not (application id "com.microsoft.Word" is running) then return "none"
	tell application id "com.microsoft.Word"
		with timeout of 2 seconds
			if (count of documents) is 0 then return "none"
			set s to selection
			if selection type of s is not selection inline shape then return "none"
			if (count of inline shapes of s) is not 1 then return "none"
			set d to document of s
			repeat with i from 1 to count of argv
				set b to item i of argv
				if exists bookmark b of d then
					set m to bookmark b of d
					set b0 to start of bookmark of m
					set b1 to end of bookmark of m
					if empty of m then set b1 to b0 + 1
					if b0 <= (selection start of s) and b1 >= (selection end of s) then return "open" & linefeed & b
				end if
			end repeat
		end timeout
	end tell
	return "picture"
end run"#;

// Word selects the picture and opens its Picture Format tab first.
const SETTLE: Duration = Duration::from_millis(200);
// A double-click this soon after the last one taken asks Word nothing.
const QUIET: Duration = Duration::from_secs(1);

// The click filter: a double-click's second click, with Word in front, and none taken in the last second.
fn wanted(count: isize, front: Option<&str>, now: Instant, last: &Cell<Option<Instant>>) -> bool {
    if count != 2 || front != Some(WORD) || last.get().is_some_and(|t| now.duration_since(t) < QUIET) {
        return false;
    }
    last.set(Some(now));
    true
}

// The bundle id of the program in front.
fn front() -> Option<String> {
    objc2::rc::autoreleasepool(|_| objc2_app_kit::NSWorkspace::sharedWorkspace().frontmostApplication()?.bundleIdentifier().map(|b| b.to_string()))
}

thread_local! {
    // The monitor while the setting is on. AppKit's, so on the main thread only.
    static MONITOR: RefCell<Option<Retained<AnyObject>>> = const { RefCell::new(None) };
}

// The page sends the setting when it opens and when it changes. Off: no monitor.
#[tauri::command]
pub fn set_word_click(app: AppHandle, on: bool) {
    let _ = app.run_on_main_thread(move || watch(on));
}

fn watch(on: bool) {
    MONITOR.with_borrow_mut(|monitor| {
        if on == monitor.is_some() {
            return;
        }
        if let Some(m) = monitor.take() {
            // SAFETY: `m` is the monitor addGlobalMonitorForEventsMatchingMask gave.
            return unsafe { NSEvent::removeMonitor(&m) };
        }
        let last = Cell::new(None);
        let block = block2::RcBlock::new(move |e: NonNull<NSEvent>| {
            // SAFETY: AppKit gives the handler a valid event, on the main thread.
            let count = unsafe { e.as_ref() }.clickCount();
            let front = if count == 2 { front() } else { None };
            if wanted(count, front.as_deref(), Instant::now(), &last) {
                if let Some(app) = APP.get() {
                    double_click(app);
                }
            }
        });
        *monitor = NSEvent::addGlobalMonitorForEventsMatchingMask_handler(NSEventMask::LeftMouseDown, &block);
    });
}

// What a double-click in Word or Edit Picture from Word found: a picture's drawing, or the bookmark of the object
// window it is open in.
enum Pick {
    Open(Found),
    Front(String),
}

// On a thread of its own. Octet busy with Word already (Edit Picture from Word, Update): the double-click is dropped.
fn picked(marks: &[String]) -> Result<Option<Pick>, Fail> {
    std::thread::sleep(SETTLE);
    let _one = match BUSY.try_lock() {
        Ok(one) => one,
        Err(TryLockError::Poisoned(e)) => e.into_inner(),
        Err(TryLockError::WouldBlock) => return Ok(None),
    };
    let marks: Vec<&str> = marks.iter().map(String::as_str).collect();
    let answer = run(PICKED, &marks)?;
    Ok(match answer.split_once('\n') {
        Some(("open", mark)) => Some(Pick::Front(mark.to_string())),
        _ if answer == "picture" => read(false)?.map(Pick::Open),
        _ => None,
    })
}

// A double-click is in hand until its window is open: one that comes before then is dropped, so it never opens the
// same picture in a second window.
static PENDING: AtomicBool = AtomicBool::new(false);

fn double_click(app: &AppHandle) {
    if PENDING.swap(true, Ordering::AcqRel) {
        return;
    }
    let app = app.clone();
    tauri::async_runtime::spawn(async move {
        let marks = crate::objects::word_marks(&app);
        match tauri::async_runtime::spawn_blocking(move || picked(&marks)).await.unwrap_or(Err(Fail::Failed)) {
            Ok(Some(Pick::Open(found))) => crate::objects::open_word(&app, found).await,
            Ok(Some(Pick::Front(mark))) => crate::objects::front_word(&app, &mark).await,
            // Nothing to open, or Word did not answer or is not allowed: nothing shows.
            _ => {}
        }
        PENDING.store(false, Ordering::Release);
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn error_numbers() {
        assert_eq!(number("85:96: execution error: Not authorized to send Apple events to Microsoft Word. (-1743)\n"), Some(-1743));
        assert_eq!(number("execution error: Microsoft Word got an error: AppleEvent timed out. (-1712)"), Some(-1712));
        assert_eq!(number("no number here"), None);
        assert_eq!(number("(x)"), None);
    }

    // Word's rules for a bookmark name: 40 characters at most, letters, digits and _; hidden when it starts with _.
    #[test]
    fn bookmark_names() {
        let m = new_mark();
        assert!(m.starts_with("_Octet_") && m.len() <= 40, "{m}");
        assert!(m.chars().all(|c| c.is_ascii_alphanumeric() || c == '_'));
    }

    // Apple Events go to Word only, by its bundle id. The scripts are ASCII, so they do not depend on how osascript
    // reads its input.
    #[test]
    fn scripts_name_only_word() {
        for s in [EDIT, MARK, UPDATE, BACK, PICKED] {
            assert!(s.is_ascii(), "ASCII only");
            assert!(!s.contains("tell application \""), "by bundle id only");
            let apps: Vec<&str> = s.match_indices("application id \"").map(|(k, _)| &s[k + 16..k + 16 + s[k + 16..].find('"').unwrap()]).collect();
            assert!(apps.iter().all(|a| *a == WORD), "{apps:?}");
        }
    }

    // Only a double-click's second click with Word in front, and one a second at most.
    #[test]
    fn the_click_filter() {
        let (last, t) = (Cell::new(None), Instant::now());
        let at = |ms: u64| t + Duration::from_millis(ms);
        assert!(!wanted(1, Some(WORD), at(0), &last), "a single click");
        assert!(!wanted(2, Some("com.apple.Pages"), at(0), &last), "another program in front");
        assert!(!wanted(2, Some("com.microsoft.Word.beta"), at(0), &last), "the bundle id exactly");
        assert!(!wanted(2, None, at(0), &last), "no program in front");
        assert_eq!(last.get(), None, "a click not taken starts no quiet time");
        assert!(wanted(2, Some(WORD), at(0), &last));
        assert!(!wanted(3, Some(WORD), at(100), &last), "a triple-click's third");
        assert!(!wanted(2, Some(WORD), at(600), &last), "a burst");
        assert!(!wanted(2, Some(WORD), at(999), &last));
        assert!(wanted(2, Some(WORD), at(1000), &last), "a second later");
        assert!(!wanted(2, Some(WORD), at(1500), &last));
        assert!(wanted(2, Some(WORD), at(2000), &last));
    }

    // EDIT's answer: the kind, where the selection starts and the document's name. The start is MARK's argument, and
    // MARK makes no bookmark unless the selection still starts there.
    #[test]
    fn edit_answers() {
        assert_eq!(parts("picture\n120\nReport.docx"), Some(("picture", "120", "Report.docx")));
        assert_eq!(parts("new\n0\nA\nB.docx"), Some(("new", "0", "A\nB.docx")), "the name is the rest");
        assert_eq!(parts("picture\n120"), Some(("picture", "120", "")), "no name");
        for a in ["none", "busy", "picture", "picture\nReport.docx", "picture\n\nReport.docx", "picture\n12a\nR", "picture\n-1\nR", "picture\n1234567890\nR", "picture\n, missing value, \nR"] {
            assert_eq!(parts(a), None, "{a:?}");
        }
        assert_eq!(EDIT.matches("& linefeed & startAt & linefeed & n").count(), 2, "a picture and a cursor both give the start");
        assert!(MARK.contains("set startAt to item 3 of argv") && MARK.contains("if (startNow as text) is not startAt then return \"none\""));
    }

    // Update gives Word the two pictures Copy gives it, in Copy's order, then the transient mark: Office's own copy
    // and the PDF for a drawing, with or without a picture in it. On a private pasteboard, so the user's clipboard is
    // untouched: the types Word reads are those, in that order, with those bytes.
    #[test]
    fn update_gives_word_copys_pictures() {
        use objc2_foundation::NSString;
        const OFFICE: &str = "com.microsoft.Art--GVML-ClipFormat";
        const PDF: &str = crate::clipboard::PDF;
        let x = "<CDXML><page><fragment><n id=\"1\"/></fragment></page></CDXML>";
        for svg in [crate::vector::tests::PROLINE.to_string(), crate::vector::tests::picture_svg()] {
            let (packed, copy) = (picture(&svg, x).unwrap(), crate::clipboard::mac_picture(&svg, Some(x)).unwrap());
            let t = types(&packed).unwrap();
            assert_eq!(t.iter().map(|(n, _)| *n).collect::<Vec<_>>(), [OFFICE, PDF, TRANSIENT]);
            assert!(t[0].1 == &copy[0].1[..] && t[1].1 == &copy[1].1[..] && t[2].1.is_empty(), "Copy's bytes");
            assert_eq!(t[1].1, &crate::export::make_pdf(&svg, Some(x), None).unwrap()[..], "the PDF Update gave before");
            let pb = objc2_app_kit::NSPasteboard::pasteboardWithUniqueName();
            clip::write(&pb, &t).unwrap();
            let on: Vec<String> = pb.types().unwrap().iter().map(|s| s.to_string()).collect();
            assert_eq!(on.iter().map(String::as_str).filter(|n| [OFFICE, PDF, TRANSIENT].contains(n)).collect::<Vec<_>>(), [OFFICE, PDF, TRANSIENT], "{on:?}");
            for (name, bytes) in &t[..2] {
                assert!(pb.dataForType(&NSString::from_str(name)).unwrap().to_vec() == *bytes, "{name}");
            }
            // Edit Picture from Word reads the drawing from such a copy.
            assert!(clip::drawing(&pb).is_some_and(|d| d.contains("<fragment>")));
            pb.clearContents();
        }
        // The PDF alone when Octet can make no Office copy: one type, then the mark.
        let pdf = crate::export::make_pdf(crate::vector::tests::PROLINE, Some(x), None).unwrap();
        let alone = [&(PDF.len() as u64).to_le_bytes()[..], PDF.as_bytes(), &(pdf.len() as u64).to_le_bytes(), &pdf].concat();
        assert_eq!(types(&alone).unwrap(), [(PDF, &pdf[..]), (TRANSIENT, &[][..])]);
        // Bytes that are not word::picture's put nothing on the clipboard: a PDF as it is, a type cut short, a length
        // past the end.
        assert_eq!(types(&pdf), None);
        assert_eq!(types(&alone[..alone.len() - 1]), None);
        assert_eq!(types(&[&u64::MAX.to_le_bytes()[..], b"x"].concat()), None);
        assert!(picture("<svg", x).is_err(), "a picture Octet cannot make is Update's error, as before");
    }

    // Update in Word with Word itself, on this Mac. Word must be open with its cursor in text and nothing selected. A
    // new picture goes in at the cursor, then a second picture takes its place, as two Updates from an object window
    // do. Save the document and look in it: its one picture is Octet's EMF. It uses the real clipboard and puts the
    // user's back, so it runs only when asked: cargo test --bin octet update_in_word_live -- --ignored --nocapture
    #[test]
    #[ignore]
    fn update_in_word_live() {
        let cdxml = |id: u32| format!("<CDXML><page><fragment><n id=\"{id}\"/></fragment></page></CDXML>");
        let found = read(true).unwrap().expect("Word's cursor is in text, with nothing selected");
        assert!(!found.placed && found.oct.is_empty());
        let first = put(&found.mark, false, &picture(crate::vector::tests::PROLINE, &cdxml(1)).unwrap()).unwrap();
        let second = put(&found.mark, true, &picture(&crate::vector::tests::picture_svg(), &cdxml(2)).unwrap()).unwrap();
        eprintln!("Placed in {first}, then replaced in {second}.");
    }

    // The script pastes with Word's own Paste, which chooses the type, and names no type itself. It reads the pasted
    // picture as the first inline picture of its own document, and copies it to the user's document as formatted text.
    #[test]
    fn update_pastes_whatever_word_takes() {
        assert_eq!(UPDATE.matches("paste object (text object of t)").count(), 1);
        assert!(!UPDATE.contains("paste special") && !UPDATE.contains("data type") && !UPDATE.to_ascii_lowercase().contains("pdf"));
        assert!(UPDATE.contains("set p to inline shape 1 of t") && UPDATE.contains("set alternative text of p to alt"));
        assert!(UPDATE.contains("set formatted text of r to formatted text of (text object of bookmark b of t)"));
    }

    // UPDATE's answer: a closed document and a picture that is gone from an open one are not the same.
    #[test]
    fn update_answers() {
        assert_eq!(placed_in("gone"), Err(Fail::Gone));
        assert_eq!(placed_in("lost"), Err(Fail::Lost));
        assert_eq!(placed_in("busy"), Err(Fail::Busy));
        assert_eq!(placed_in("Report.docx"), Ok("Report.docx".to_string()));
        assert_eq!(UPDATE.matches("return \"lost\"").count(), 2, "no bookmark in the open document, and no picture at the bookmark");
        assert_eq!(UPDATE.matches("return \"gone\"").count(), 2, "Word not running, and no document of that name open");
    }

    // The document's name that Update gives Word: the newest for each bookmark, for 64 bookmarks at most.
    #[test]
    fn document_names() {
        remember("_Octet_a", "Document1");
        remember("_Octet_a", "Report.docx");
        assert_eq!(document("_Octet_a"), "Report.docx");
        assert_eq!(document("_Octet_none"), "");
        for k in 0..DOCS_MOST {
            remember(&format!("_Octet_{k}"), "Other.docx");
        }
        assert_eq!(document("_Octet_a"), "", "the oldest goes");
        assert_eq!(DOCS.lock().unwrap().len(), DOCS_MOST);
    }

    #[test]
    fn messages() {
        assert_eq!(message(&Fail::Gone, Some("Report.docx")), "Report.docx is closed. Save a copy to keep this drawing.");
        assert_eq!(message(&Fail::Lost, Some("Report.docx")), "Octet cannot find this picture in Report.docx. Save a copy to keep this drawing.");
        assert_eq!(message(&Fail::Failed, Some("Report.docx")), "Octet cannot update Report.docx. Try again.");
        assert_eq!(message(&Fail::Denied, None), "Octet Draw is not allowed to control Microsoft Word.");
    }
}
