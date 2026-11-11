// Run: node src/notice.check.ts. Fails loudly if a notice shows a raw error, or goes too soon.
import assert from "node:assert/strict";
import { failure, fileName, noticeTime, reason } from "./notice.ts";

// Octet's own sentences go as they are.
assert.equal(reason(new Error("This drawing is damaged.")), "This drawing is damaged.");
assert.equal(reason("This file is larger than 64 MB. Octet cannot open it."), "This file is larger than 64 MB. Octet cannot open it.");
assert.equal(reason("Octet can only import text files (MOL, SDF, SMILES, CDXML)."), "Octet can only import text files (MOL, SDF, SMILES, CDXML).");
// System errors in words, on the Mac and Linux and on Windows.
assert.equal(reason("Permission denied (os error 13)"), "Octet does not have permission to use this file or folder.");
assert.equal(reason("Access is denied. (os error 5)"), "Octet does not have permission to use this file or folder.");
assert.equal(reason("No space left on device (os error 28)"), "The disk is full.");
assert.equal(reason("There is not enough space on the disk. (os error 112)"), "The disk is full.");
assert.equal(reason("Read-only file system (os error 30)"), "The disk is read-only.");
assert.equal(reason("No such file or directory (os error 2)"), "The file or folder is not there.");
assert.equal(reason("The process cannot access the file because it is being used by another process. (os error 32)"), "Another app is using the file.");
// Raw exceptions are not shown.
for (const raw of ["Indigo is not loaded yet", "stream did not contain valid UTF-8", new TypeError("Cannot read properties of undefined (reading 'x')"),
  "molfile loader: Error: unexpected end of input.", "Internal error.", undefined, ""]) assert.equal(reason(raw), "", String(raw));

// A failure says what did not happen, then why; the raw error is logged, never shown.
const logged: unknown[] = [], log = console.error;
console.error = (e: unknown) => logged.push(e);
assert.equal(failure("Octet cannot save this drawing.", "Permission denied (os error 13)"), "Octet cannot save this drawing. Octet does not have permission to use this file or folder.");
assert.equal(failure("Octet cannot print.", "WKWebView print failed: error -1"), "Octet cannot print.");
assert.equal(failure("Octet cannot open this file.", new Error("This drawing is damaged.")), "Octet cannot open this file. This drawing is damaged.");
assert.equal(failure("Octet cannot open this drawing.", "Octet cannot open this drawing from Home. Open it with File > Open."), "Octet cannot open this drawing from Home. Open it with File > Open.");
console.error = log;
assert.equal(logged.length, 4, "every raw error goes to the console");

// Long notices stay longer.
assert.equal(noticeTime(""), 4000);
assert.ok(noticeTime("Octet cannot read this structure. Paste a name, a SMILES string or a MOL file.") > 7500);

assert.equal(fileName("/Users/sam/Desktop/aspirin.png"), "aspirin.png");
assert.equal(fileName("C:\\Users\\sam\\aspirin.pdf"), "aspirin.pdf");
console.log("notice.check: ok");
