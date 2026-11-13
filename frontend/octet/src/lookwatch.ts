// Development only (main.tsx): measures the controls as they are drawn and writes an error to the console, starting
// "look:", when controls that must match do not. ui.check.ts reads the stylesheet; this reads the result on screen, so
// a mismatch shows the first time anyone runs the app. The rules are in brand/BRAND.md (Controls).

// The height of each kind of control (tokens.json, size). ui.check.ts holds the stylesheet to the same list.
export const SIZE_OF: Record<string, string[]> = {
  "size-action": [".close-x, .segmented button.close-x", ".variant-action", ".name-forget", ".problem-hide", ".home-remove", ".key-remove"],
  "size-control-sm": [".actions-close", ".floating-size", ".key-add", ".library-keep", ".home-act", ".pill", ".problem-buttons button", ".name-options button"],
  "size-control": [".text-button", ".dialog-button", ".spectrum-button", ".prop-add", ".home-open", ".page-button", ".select-field", ".unit-field", ".segmented", ".list-find", ".settings-search, .library-search"],
  "size-row": [".action", ".chip", ".module", ".library-category", ".strip.list .variant"],
  "size-tool": [".tool", ".tray-button", ".export-button", ".feedback-link", ".actions-reopen"],
  "size-cell": [".variant", ".command"],
};
// These take their height from what is in them: the purposes wrap onto more lines, and a menu option in a list is a row.
const OWN_HEIGHT = ".segmented.purposes, .strip.list .variant, .variant.add";

const said = new Set<string>();
const say = (text: string) => { if (!said.has(text)) { said.add(text); console.error(`look: ${text}`); } };
const name = (el: Element) => el.getAttribute("aria-label") ?? (el.textContent?.trim().slice(0, 24) || el.className);

// offsetWidth and offsetHeight are the laid-out size: a press or an overlay coming in (a scale) does not change them.
export function measureLook(root: ParentNode = document) {
  // One width and one height for the segments of a segmented control. A tab with its X is one segment, and so is
  // the + at the tabs' end.
  for (const control of root.querySelectorAll<HTMLElement>(".segmented")) {
    const segments = [...control.querySelectorAll<HTMLElement>(":scope > button, :scope > [role=tablist] > *")].filter((s) => s.offsetWidth);
    const first = segments[0];
    if (first && segments.some((s) => s.offsetWidth !== first.offsetWidth || s.offsetHeight !== first.offsetHeight))
      say(`the segments of "${name(control)}" are not one size: ${segments.map((s) => `${s.offsetWidth}x${s.offsetHeight}`).join(", ")}`);
    // A segment is the control's height less its edge and its 2 px of room, top and bottom: 22 px in every control.
    const inner = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--size-control")) - 6;
    if (first && first.offsetHeight !== inner) say(`the segments of "${name(control)}" are ${first.offsetHeight}px high, not ${inner}px`);
  }
  // Each kind of control is as high as its size token.
  const tokens = getComputedStyle(document.documentElement);
  for (const [token, selectors] of Object.entries(SIZE_OF)) {
    const height = parseFloat(tokens.getPropertyValue(`--${token}`));
    for (const el of root.querySelectorAll<HTMLElement>(selectors.join(", "))) {
      if (el.offsetHeight && el.offsetHeight !== height && !el.matches(OWN_HEIGHT)) say(`"${name(el)}" (${el.className}) is ${el.offsetHeight}px high, not --${token} (${height}px)`);
    }
  }
}

// After each click and key, once the page has settled.
export function watchLook() {
  let timer = 0;
  const soon = () => { clearTimeout(timer); timer = window.setTimeout(() => measureLook(), 400); };
  addEventListener("pointerup", soon, true);
  addEventListener("keyup", soon, true);
  soon();
}
