# Octet's window, menus and clipboard on Windows, for scripts/drive/drive.mjs. Run with powershell.exe -STA (the
# clipboard needs it).
#
#   windows.ps1 clip-set              put the text on standard input (UTF-8) on the clipboard, as a long text (a
#                                     drawing's CDXML) is too long for a command line
#   windows.ps1 clip-set-data FORMAT BASE64
#                                     put bytes on the clipboard under a format's name
#   windows.ps1 clip-formats          the clipboard's formats, one a line
#   windows.ps1 clip-get FORMAT       a format's bytes in base64 (text as UTF-8)
#   windows.ps1 menu Edit Paste       click a menu in the menu bar, then an item in it, with the mouse; New* is the
#                                     first item whose name starts with New and that is not a submenu
#   windows.ps1 keys ^v               press keys (SendKeys) in Octet's window
#   windows.ps1 running               yes while Octet runs
#   windows.ps1 front                 the title of Octet's window in front, if one is
#   windows.ps1 menu-names            the menus in Octet's menu bar (Win32), one a line
#   windows.ps1 uia-menu              the items in Octet's menu bar as UI Automation shows them to a screen reader
#   windows.ps1 uia-open              open each menu through UI Automation, as a screen reader does: one line a
#                                     menu, "File opened (120 ms)" or "File did not open"
#
# The menu command clicks with the mouse, and finds the menu through Win32 (GetMenu). uia-menu and uia-open use native
# UI Automation (UIAutomationCore), as Narrator does.
param([Parameter(Mandatory)][string]$Command, [Parameter(ValueFromRemainingArguments)][string[]]$Rest)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

public static class Menus {
    [StructLayout(LayoutKind.Sequential)] struct RECT { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] public static extern IntPtr GetMenu(IntPtr hwnd);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hwnd);
    [DllImport("user32.dll")] static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] static extern IntPtr GetSubMenu(IntPtr menu, int pos);
    [DllImport("user32.dll")] static extern int GetMenuItemCount(IntPtr menu);
    [DllImport("user32.dll")] static extern uint GetMenuState(IntPtr menu, uint pos, uint flags);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetMenuString(IntPtr menu, uint pos, StringBuilder text, int max, uint flags);
    [DllImport("user32.dll")] static extern bool GetMenuItemRect(IntPtr hwnd, IntPtr menu, uint pos, out RECT rect);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr hwnd);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint pid);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr hwnd, StringBuilder text, int max);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern IntPtr FindWindowEx(IntPtr parent, IntPtr after, string cls, string name);
    [DllImport("user32.dll")] static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] static extern void mouse_event(uint flags, int dx, int dy, uint data, UIntPtr extra);
    const uint MF_BYPOSITION = 0x400, MF_POPUP = 0x10, MOUSEEVENTF_LEFTDOWN = 2, MOUSEEVENTF_LEFTUP = 4;

    // A menu's items by position: each one's name (without the shortcut after a tab) and whether it opens a submenu.
    static List<Tuple<string, bool>> Items(IntPtr menu) {
        var items = new List<Tuple<string, bool>>();
        for (uint i = 0; i < GetMenuItemCount(menu); i++) {
            var text = new StringBuilder(256);
            GetMenuString(menu, i, text, text.Capacity, MF_BYPOSITION);
            string name = text.ToString().Split('\t')[0].Replace("&&", "\u0001").Replace("&", "").Replace("\u0001", "&").Trim();
            items.Add(Tuple.Create(name, (GetMenuState(menu, i, MF_BYPOSITION) & MF_POPUP) != 0));
        }
        return items;
    }

    // The window in front if it is one of the process's with a menu bar (Home or a drawing), else none.
    public static IntPtr Front(uint pid) {
        IntPtr h = GetForegroundWindow();
        uint owner;
        GetWindowThreadProcessId(h, out owner);
        return owner == pid && GetMenu(h) != IntPtr.Zero ? h : IntPtr.Zero;
    }
    public static string Title(IntPtr window) {
        var text = new StringBuilder(512);
        GetWindowText(window, text, text.Capacity);
        return text.ToString();
    }

    // The names in the window's menu bar.
    public static string[] Bar(IntPtr window) { return Items(GetMenu(window)).Select(i => i.Item1).ToArray(); }

    static int Pick(List<Tuple<string, bool>> items, string want, bool leaf) {
        for (int i = 0; i < items.Count; i++) {
            bool named = want.EndsWith("*") ? items[i].Item1.StartsWith(want.TrimEnd('*')) : items[i].Item1 == want;
            if (named && !(leaf && items[i].Item2)) return i;
        }
        return -1;
    }

    static void ClickAt(RECT r) {
        SetCursorPos((r.Left + r.Right) / 2, (r.Top + r.Bottom) / 2);
        Thread.Sleep(100);
        mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, UIntPtr.Zero);
        mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, UIntPtr.Zero);
    }

    // A menu open in the process (a #32768 window).
    static bool Open(uint pid) {
        IntPtr h = IntPtr.Zero;
        while ((h = FindWindowEx(IntPtr.Zero, h, "#32768", null)) != IntPtr.Zero) {
            uint owner;
            GetWindowThreadProcessId(h, out owner);
            if (owner == pid && IsWindowVisible(h)) return true;
        }
        return false;
    }

    // Clicks a menu in the window's menu bar, then an item in it. Returns an error, or null.
    public static string Click(IntPtr window, uint pid, string menu, string item) {
        SetProcessDPIAware();
        IntPtr bar = GetMenu(window);
        var top = Items(bar);
        int k = Pick(top, menu, false);
        if (k < 0) return "no " + menu + " menu; the menu bar has: " + string.Join(", ", top.Select(i => i.Item1));
        IntPtr sub = GetSubMenu(bar, k);
        var items = Items(sub);
        int j = Pick(items, item, true);
        if (j < 0) return "no " + menu + " > " + item + "; the menu has: " + string.Join(", ", items.Select(i => i.Item1).Where(n => n != ""));
        SetForegroundWindow(window);
        RECT r;
        if (!GetMenuItemRect(window, bar, (uint)k, out r)) return "the " + menu + " menu is not in the menu bar on the screen";
        ClickAt(r);
        for (int i = 0; i < 30 && !Open(pid); i++) Thread.Sleep(100);
        if (!Open(pid)) return "the " + menu + " menu did not open";
        Thread.Sleep(200);
        if (!GetMenuItemRect(IntPtr.Zero, sub, (uint)j, out r)) return menu + " > " + item + " is not on the screen";
        ClickAt(r);
        for (int i = 0; i < 30 && Open(pid); i++) Thread.Sleep(100);
        return Open(pid) ? "the " + menu + " menu stayed open after " + item + " was clicked" : null;
    }
}
'@

Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Threading;

// Native UI Automation (UIAutomationCore), as Narrator reads a window. Only the calls used here are named; the other
// slots keep each interface's order. .NET's System.Windows.Automation is not used: it shows no window's title bar or
// menu bar, not even Notepad's.
[ComImport, Guid("ff48dba4-60ef-4201-aa87-54103eef594e")] class CUIAutomation { }

[ComImport, Guid("30cbe57d-d9d0-452a-ab13-7ac5ac4825ee"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IUIAutomation {
    void _0(); void _1(); void _2();
    IUIAutomationElement ElementFromHandle(IntPtr hwnd);
    void _4(); void _5(); void _6(); void _7(); void _8(); void _9(); void _10(); void _11(); void _12();
    IUIAutomationTreeWalker RawViewWalker();
}

[ComImport, Guid("4042c624-389c-4afc-a630-9df854a541fc"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IUIAutomationTreeWalker {
    void _0();
    IUIAutomationElement GetFirstChildElement(IUIAutomationElement element);
    void _2();
    IUIAutomationElement GetNextSiblingElement(IUIAutomationElement element);
}

[ComImport, Guid("d22108aa-8ac5-49a5-837b-37bbb3d7591e"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IUIAutomationElement {
    void _0(); void _1(); void _2(); void _3(); void _4(); void _5(); void _6(); void _7(); void _8(); void _9();
    void _10(); void _11(); void _12();
    [return: MarshalAs(UnmanagedType.IUnknown)] object GetCurrentPattern(int pattern);
    void _14(); void _15(); void _16(); void _17();
    int CurrentControlType();
    void _19();
    [return: MarshalAs(UnmanagedType.BStr)] string CurrentName();
}

[ComImport, Guid("619be086-1f4e-4ee4-bafa-210128738730"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IUIAutomationExpandCollapsePattern { void Expand(); void Collapse(); }

public static class Uia {
    const int MenuBarType = 50010, MenuItemType = 50011, ExpandCollapse = 10005;
    [StructLayout(LayoutKind.Sequential)] struct GUITHREADINFO { public int cbSize, flags; public IntPtr active, focus, capture, menuOwner, moveSize, caret; public int left, top, right, bottom; }
    [DllImport("user32.dll")] static extern bool GetGUIThreadInfo(uint thread, ref GUITHREADINFO info);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint pid);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern IntPtr FindWindowEx(IntPtr parent, IntPtr after, string cls, string name);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr hwnd);
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr hwnd);
    [DllImport("user32.dll")] static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);

    static List<IUIAutomationElement> Children(IUIAutomationTreeWalker walker, IUIAutomationElement parent) {
        var list = new List<IUIAutomationElement>();
        for (var c = walker.GetFirstChildElement(parent); c != null; c = walker.GetNextSiblingElement(c)) list.Add(c);
        return list;
    }

    // The items of the window's menu bar (not the title bar's System menu).
    static List<IUIAutomationElement> Items(IntPtr window) {
        var uia = (IUIAutomation)new CUIAutomation();
        var walker = uia.RawViewWalker();
        var items = new List<IUIAutomationElement>();
        foreach (var bar in Children(walker, uia.ElementFromHandle(window)))
            if (bar.CurrentControlType() == MenuBarType)
                foreach (var item in Children(walker, bar))
                    if (item.CurrentControlType() == MenuItemType) items.Add(item);
        return items;
    }

    // Each item's name, and whether it can open its menu.
    public static List<string> MenuBarItems(IntPtr window) {
        var names = new List<string>();
        foreach (var item in Items(window))
            names.Add(item.CurrentName() + (item.GetCurrentPattern(ExpandCollapse) is IUIAutomationExpandCollapsePattern ? "" : " (cannot open)"));
        return names;
    }

    // Whether a menu of the window's process is open, and whether the window's thread is in menu mode.
    static bool MenuOpen(IntPtr window) {
        uint pid, owner;
        GetWindowThreadProcessId(window, out pid);
        for (IntPtr h = FindWindowEx(IntPtr.Zero, IntPtr.Zero, "#32768", null); h != IntPtr.Zero; h = FindWindowEx(IntPtr.Zero, h, "#32768", null)) {
            GetWindowThreadProcessId(h, out owner);
            if (owner == pid && IsWindowVisible(h)) return true;
        }
        return false;
    }
    static bool InMenuMode(IntPtr window) {
        uint pid;
        var info = new GUITHREADINFO { cbSize = Marshal.SizeOf(typeof(GUITHREADINFO)) };
        return GetGUIThreadInfo(GetWindowThreadProcessId(window, out pid), ref info) && (info.flags & 4) != 0;
    }

    // Opens each menu of the menu bar as a screen reader does (UI Automation's Expand), then closes it with Escape.
    // One line a menu: "File opened (120 ms)", or "File did not open" and why.
    public static List<string> OpenEach(IntPtr window) {
        var lines = new List<string>();
        foreach (var item in Items(window)) {
            string name = item.CurrentName(), problem = null;
            SetForegroundWindow(window);
            Thread.Sleep(300);
            var clock = System.Diagnostics.Stopwatch.StartNew();
            try { ((IUIAutomationExpandCollapsePattern)item.GetCurrentPattern(ExpandCollapse)).Expand(); }
            catch (Exception e) { problem = e.Message.Trim(); }
            while (problem == null && !MenuOpen(window) && clock.ElapsedMilliseconds < 2000) Thread.Sleep(20);
            lines.Add(problem == null && MenuOpen(window) ? name + " opened (" + clock.ElapsedMilliseconds + " ms)" : name + " did not open" + (problem != null ? ": " + problem : ""));
            for (int i = 0; i < 4 && (MenuOpen(window) || InMenuMode(window)); i++) {
                keybd_event(0x1B, 0, 0, UIntPtr.Zero);
                keybd_event(0x1B, 0, 2, UIntPtr.Zero);
                Thread.Sleep(250);
            }
        }
        return lines;
    }
}
'@

function Octet-Process { Get-Process octet -ErrorAction SilentlyContinue | Select-Object -First 1 }

# Octet's window in front (Home or a drawing: menu commands go to the window in front, src-tauri/src/windows.rs), else
# its main window, once it has its menu bar.
function Octet-Window {
    for ($i = 0; $i -lt 40; $i++) {
        $p = Octet-Process
        if (-not $p) { throw 'Octet is not running' }
        $h = [Menus]::Front($p.Id)
        if ($h -eq [IntPtr]::Zero) { $h = $p.MainWindowHandle }
        if ($h -ne [IntPtr]::Zero -and [Menus]::GetMenu($h) -ne [IntPtr]::Zero) { return $h }
        Start-Sleep -Milliseconds 250
    }
    throw 'Octet has no window with a menu bar'
}

function Click-Menu([string[]]$path) {
    $window = Octet-Window
    $problem = [Menus]::Click($window, (Octet-Process).Id, $path[0], $path[-1])
    if ($problem) {
        [System.Windows.Forms.SendKeys]::SendWait('{ESC}{ESC}')
        throw $problem
    }
    Start-Sleep -Milliseconds 300
}

switch ($Command) {
    'clip-set' {
        $in = New-Object System.IO.MemoryStream
        [Console]::OpenStandardInput().CopyTo($in)
        [System.Windows.Forms.Clipboard]::SetText([Text.Encoding]::UTF8.GetString($in.ToArray()))
    }
    'clip-set-data' {
        $d = New-Object System.Windows.Forms.DataObject
        $d.SetData($Rest[0], $false, (New-Object System.IO.MemoryStream(, [Convert]::FromBase64String($Rest[1]))))
        [System.Windows.Forms.Clipboard]::SetDataObject($d, $true)
    }
    'clip-formats' { [System.Windows.Forms.Clipboard]::GetDataObject().GetFormats() }
    'clip-get' {
        $d = [System.Windows.Forms.Clipboard]::GetData($Rest[0])
        if ($d -is [System.IO.MemoryStream]) { [Convert]::ToBase64String($d.ToArray()) }
        elseif ($d -is [string]) { [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($d)) }
    }
    'menu' { Click-Menu $Rest }
    'keys' {
        $window = Octet-Window
        [void][Menus]::SetForegroundWindow($window)
        Start-Sleep -Milliseconds 300
        if ([Menus]::GetForegroundWindow() -ne $window) { throw "Octet's window is not in front, so it would not get the keys" }
        [System.Windows.Forms.SendKeys]::SendWait($Rest[0])
    }
    'running' { if (Octet-Process) { 'yes' } else { 'no' } }
    'front' { $p = Octet-Process; if ($p) { $h = [Menus]::Front($p.Id); if ($h -ne [IntPtr]::Zero) { [Menus]::Title($h) } } }
    'menu-names' { [Menus]::Bar((Octet-Window)) }
    'uia-menu' { [Uia]::MenuBarItems((Octet-Window)) }
    'uia-open' { [Uia]::OpenEach((Octet-Window)) }
    default { throw "unknown command $Command" }
}
