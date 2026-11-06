// Run: node src/jcamp.check.ts. Fails loudly if the JCAMP-DX reader misreads a form, or opens a file it should refuse.
// Every file here is written by the check itself: each compression form, a peak table, NTUPLES, a compound file,
// Bruker's processed data, and damaged and oversized files.
import assert from "node:assert/strict";
import { isJcamp, isSpectrum, MAX_POINTS, readBruker, readJcamp, readSpc, readSpcText, solventName, SPC } from "./jcamp.ts";

// --- Writing the forms ----------------------------------------------------------------------------------------------

const SQZ = "@ABCDEFGHI", SQZ_NEG = "abcdefghi", DIF = "%JKLMNOPQR", DIF_NEG = "jklmnopqr", DUP = "STUVWXYZs";
const sqz = (v: number) => { const s = String(Math.abs(v)); return (v < 0 ? SQZ_NEG[+s[0] - 1] : SQZ[+s[0]]) + s.slice(1); };
const dif = (v: number) => { const s = String(Math.abs(v)); return (v < 0 ? DIF_NEG[+s[0] - 1] : DIF[+s[0]]) + s.slice(1); };
const dup = (k: number) => { const s = String(k); return DUP[+s[0] - 1] + s.slice(1); };
// Whole-number Ys as (X++(Y..Y)) lines, `per` to a line, in one form. DIF and DUP lines start with an absolute value
// and, after the first line, repeat the last Y of the line before (the Y check).
function lines(ys: number[], form: "AFFN" | "PAC" | "SQZ" | "DIF" | "DUP", per = 10): string[] {
  const out: string[] = [];
  if (form === "AFFN" || form === "PAC" || form === "SQZ") {
    for (let i = 0; i < ys.length; i += per) {
      const part = ys.slice(i, i + per);
      out.push(form === "AFFN" ? `${i} ${part.join(" ")}` : form === "PAC" ? `${i}${part.map((v) => (v < 0 ? `${v}` : `+${v}`)).join("")}` : `${i}${part.map(sqz).join("")}`);
    }
    return out;
  }
  let i = 0;
  while (i < ys.length) {
    const start = out.length ? i - 1 : i, part = ys.slice(start, Math.min(ys.length, start + per + 1));
    let s = `${start}${sqz(part[0])}`;
    const diffs = part.slice(1).map((v, k) => v - part[k]);
    for (let k = 0; k < diffs.length;) {
      let run = 1;
      while (form === "DUP" && k + run < diffs.length && diffs[k + run] === diffs[k]) run++;
      s += dif(diffs[k]) + (run > 1 ? dup(run) : "");
      k += run;
    }
    out.push(s);
    i = start + part.length;
  }
  return out;
}
const head = (more = "") => `##TITLE= Check spectrum\n##JCAMP-DX= 5.01\n##DATA TYPE= NMR SPECTRUM\n##.OBSERVE FREQUENCY= 400.13\n##.OBSERVE NUCLEUS= ^1H\n##.SOLVENT NAME= CDCl3\n${more}`;
const file = (ys: number[], form: Parameters<typeof lines>[1], extra = "") =>
  `${head(extra)}##XUNITS= PPM\n##YUNITS= ARBITRARY UNITS\n##XFACTOR= 1\n##YFACTOR= 0.5\n##FIRSTX= 10\n##LASTX= 0\n##NPOINTS= ${ys.length}\n##XYDATA= (X++(Y..Y))\n${lines(ys, form).join("\n")}\n##END=\n`;

// Values with runs, steps both ways, zeros and negatives, so every form has something to compress.
const ys = Array.from({ length: 101 }, (_, i) => (i < 20 ? 100 : i < 30 ? 100 + 7 * (i - 20) : i < 50 ? 1234 - 37 * (i - 30) : i % 7 === 0 ? -42 : i * 3));

// Each form reads back to the same values, times YFACTOR, from 10 to 0 ppm.
for (const form of ["AFFN", "PAC", "SQZ", "DIF", "DUP"] as const) {
  const [s] = readJcamp(file(ys, form));
  assert.deepEqual([...s.y], ys.map((v) => v * 0.5), form);
  assert.equal(s.first, 10);
  assert.equal(s.last, 0);
  assert.equal(s.kind, "nmr");
  assert.equal(s.nucleus, "1H");
  assert.equal(s.mhz, 400.13);
  assert.equal(s.solvent, "CDCl₃");
  assert.equal(s.xUnit, "ppm");
}
// The DUP form is shorter than DIF, and DIF than SQZ, for these values.
assert.ok(lines(ys, "DUP").join("").length < lines(ys, "DIF").join("").length);

// The JCAMP-DX standard's own example lines (McDonald and Wilks 1988): the same ten values in four forms.
const tenAffn = "1 2 3 3 2 1 0 -1 -2 -3".split(" ").map(Number);
const sample = (data: string) => `##TITLE=x\n##DATATYPE=INFRARED SPECTRUM\n##XUNITS=1/CM\n##YUNITS=ABSORBANCE\n##FIRSTX=1\n##LASTX=10\n##NPOINTS=10\n##XYDATA=(X++(Y..Y))\n${data}\n##END=\n`;
for (const data of ["1 1 2 3 3 2 1 0 -1 -2 -3", "1+1+2+3+3+2+1+0-1-2-3", "1ABCCBA@abc", "1AJJ%jjjjjj", "1AJT%jX"]) assert.deepEqual([...readJcamp(sample(data))[0].y], tenAffn, data);
// An E with a sign after a digit is an exponent; otherwise it is SQZ for +5.
assert.deepEqual([...readJcamp(sample("1 1E+00 2 3 3 2 1 0 -1 -2 -3"))[0].y], tenAffn);
assert.deepEqual([...readJcamp(sample("1 E5 2 3 3 2 1 0 -1 -2 -3"))[0].y].slice(0, 2), [55, 2]);
// IR: its kind and units.
const ir = readJcamp(sample("1 1 2 3 3 2 1 0 -1 -2 -3"))[0];
assert.equal(ir.kind, "ir");
assert.equal(ir.xUnit, "cm⁻¹");
assert.equal(ir.yUnit, "A");

// Hz becomes ppm by the observe frequency; a shift reference (point 1 is 10.5 ppm) moves the axis.
const hz = readJcamp(file(ys, "DIF").replace("##XUNITS= PPM", "##XUNITS= HZ").replace("##FIRSTX= 10", "##FIRSTX= 4001.3").replace("##LASTX= 0", "##LASTX= 0"))[0];
assert.ok(Math.abs(hz.first - 10) < 1e-9 && hz.last === 0);
const moved = readJcamp(file(ys, "DIF", "##.SHIFT REFERENCE= (INTERNAL, CDCl3, 1, 10.5)\n"))[0];
assert.ok(Math.abs(moved.first - 10.5) < 1e-9 && Math.abs(moved.last - 0.5) < 1e-9);

// XYPOINTS and (XY..XY) data: x and y in pairs, unevenly spaced.
const pts = readJcamp(`##TITLE=uv\n##DATA TYPE=UV/VIS SPECTRUM\n##XUNITS=NANOMETERS\n##YUNITS=ABSORBANCE\n##XFACTOR=1\n##YFACTOR=0.001\n##NPOINTS=4\n##XYPOINTS=(XY..XY)\n200,100; 250,900 300,400;\n400,10\n##END=`)[0];
assert.equal(pts.kind, "uv");
assert.deepEqual([...pts.xs!], [200, 250, 300, 400]);
assert.deepEqual([...pts.y].map((v) => Math.round(v * 1000)), [100, 900, 400, 10]);
assert.equal(pts.xUnit, "nm");

// A peak table alone (a mass spectrum): sticks, with XYW and XYM forms read too.
const ms = readJcamp(`##TITLE=Ethyl acetate\n##JCAMP-DX=4.24\n##DATA TYPE=MASS SPECTRUM\n##XUNITS=M/Z\n##YUNITS=RELATIVE ABUNDANCE\n##NPOINTS=4\n##PEAK TABLE=(XY..XY)\n43,100 45,18\n61,15 88,8\n##END=`)[0];
assert.equal(ms.kind, "ms");
assert.equal(ms.sticks, true);
assert.deepEqual([...ms.xs!], [43, 45, 61, 88]);
assert.deepEqual([...ms.y], [100, 18, 15, 8]);
const xyw = readJcamp(`##TITLE=p\n##DATA TYPE=NMR PEAK TABLE\n##.OBSERVE FREQUENCY=100\n##.OBSERVE NUCLEUS=^13C\n##XUNITS=PPM\n##PEAK TABLE=(XYW..XYW)\n170.1,50,1\n60.4,80,1\n##END=`)[0];
assert.deepEqual([...xyw.xs!], [170.1, 60.4]);
assert.equal(xyw.nucleus, "13C");
// A peak table beside the data is kept as the file's peaks.
const both = readJcamp(file(ys, "SQZ").replace("##END=", "##PEAK TABLE=(XY..XY)\n5.0,10\n##END="))[0];
assert.deepEqual(both.peaks, [[5, 5]]);

// NTUPLES (a processed NMR spectrum as real and imaginary pages): the real page, in Hz turned to ppm.
const re = ys.slice(0, 50), im = re.map((v) => -v);
const nt = `##TITLE= nt\n##JCAMP-DX= 5.00\n##DATA TYPE= NMR SPECTRUM\n##.OBSERVE FREQUENCY= 100\n##.OBSERVE NUCLEUS= ^13C\n##NTUPLES= NMR SPECTRUM\n` +
  `##VAR_NAME= FREQUENCY, SPECTRUM/REAL, SPECTRUM/IMAG, PAGE NUMBER\n##SYMBOL= X, R, I, N\n##VAR_TYPE= INDEPENDENT, DEPENDENT, DEPENDENT, PAGE\n##VAR_FORM= AFFN, ASDF, ASDF, AFFN\n` +
  `##VAR_DIM= 50, 50, 50, 2\n##UNITS= HZ, ARBITRARY UNITS, ARBITRARY UNITS,\n##FIRST= 20000, 0, 0, 1\n##LAST= 0, 0, 0, 2\n##FACTOR= 1, 2, 2, 1\n` +
  `##PAGE= N=1\n##DATA TABLE= (X++(R..R)), XYDATA\n${lines(re, "DUP").join("\n")}\n##PAGE= N=2\n##DATA TABLE= (X++(I..I)), XYDATA\n${lines(im, "DUP").join("\n")}\n##END NTUPLES= NMR SPECTRUM\n##END=\n`;
const ntr = readJcamp(nt)[0];
assert.deepEqual([...ntr.y], re.map((v) => v * 2));
assert.equal(ntr.first, 200);
assert.equal(ntr.nucleus, "13C");

// A compound file: a link block holding two spectra; the link block's labels pass to the blocks inside.
const compound = `##TITLE= Both\n##JCAMP-DX= 5.01\n##DATA TYPE= LINK\n##BLOCKS= 2\n${sample("1 1 2 3 3 2 1 0 -1 -2 -3")}\n${file(ys, "SQZ")}##END=\n`;
assert.deepEqual(readJcamp(compound).map((s) => s.kind), ["ir", "nmr"]);
assert.ok(isJcamp(compound) && isJcamp(`$$ a comment\n##TITLE=x`) && !isJcamp("CCO\n") && !isJcamp("<CDXML>"));
assert.equal(solventName("<DMSO>"), "DMSO-d₆");
assert.equal(solventName("Chloroform-d"), "CDCl₃");

// Bruker's processed data: 32-bit integers times 2^NC_proc, from OFFSET ppm, SW_p Hz wide at SF MHz.
const si = 8, raw = new DataView(new ArrayBuffer(si * 4));
[0, 10, 1000, 10, 0, -5, 0, 0].forEach((v, i) => raw.setInt32(i * 4, v, true));
const procs = `##TITLE= Parameter file\n##$SI= ${si}\n##$OFFSET= 12\n##$SW_p= 4800\n##$SF= 400.13\n##$NC_proc= 1\n##$BYTORDP= 0\n##$DTYPP= 0\n##END=`;
const bruker = readBruker(procs, new Uint8Array(raw.buffer), "##$NUC1= <1H>\n##$SOLVENT= <CDCl3>", "ethyl acetate 1");
assert.deepEqual([...bruker.y], [0, 20, 2000, 20, 0, -10, 0, 0]);
assert.equal(bruker.first, 12);
assert.ok(Math.abs(bruker.last - (12 - (7 * 4800) / 400.13 / 8)) < 1e-12);
assert.equal(bruker.solvent, "CDCl₃");
assert.equal(bruker.title, "ethyl acetate 1");
// Big endian too; a 1r of the wrong size is refused.
const bigRaw = new DataView(new ArrayBuffer(si * 4));
[0, 10, 1000, 10, 0, -5, 0, 0].forEach((v, i) => bigRaw.setInt32(i * 4, v, false));
assert.deepEqual([...readBruker(procs.replace("BYTORDP= 0", "BYTORDP= 1"), new Uint8Array(bigRaw.buffer)).y], [0, 20, 2000, 20, 0, -10, 0, 0]);
assert.throws(() => readBruker(procs, new Uint8Array(12)), /damaged: 1r holds 3 points, not 8/);

// --- Refusals: each with a plain message, never a crash -----------------------------------------------------------
const refuses = (text: string, why: RegExp) => assert.throws(() => readJcamp(text), (e: Error) => why.test(e.message), why.source);
refuses("CCO\n", /not a JCAMP-DX spectrum/);
refuses("", /not a JCAMP-DX spectrum/);
refuses(sample("1 1 2 3 3 2 1 0 -1 -2 -3").replace("##FIRSTX=1\n", ""), /FIRSTX or LASTX is missing/);
refuses(sample("1 1 2 3 3 2 1 0 -1 -2 -3 4"), /declares 10 points and holds 11/);
refuses(sample("1 1 2 3 # 2 1 0 -1 -2 -3"), /"#" cannot be in a data line/);
refuses(sample("1 J1 2"), /start with a difference/);
refuses(sample("1 S3"), /nothing to repeat/);
refuses(`##TITLE=x\n##DATATYPE=NMR SPECTRUM\n##END=`, /holds no spectrum/);
// A huge declared size is refused before anything is read; a repeat that would make too many points stops at once.
refuses(sample("1 1").replace("NPOINTS=10", "NPOINTS=999999999"), /999,999,999 points/);
refuses(sample("1 1 Zs99999999").replace("##NPOINTS=10\n", ""), new RegExp(`up to ${MAX_POINTS.toLocaleString("en-GB")} points`));
// Blocks nested deeper than a compound file's, and too many blocks.
refuses("##TITLE=a\n".repeat(4) + "##END=\n".repeat(4), /nested too deep/);
refuses(Array.from({ length: 65 }, () => sample("1 1 2 3 3 2 1 0 -1 -2 -3")).join("\n"), /more than 64 blocks/);
// A raw FID, and a 2D spectrum.
refuses(nt.replace("##DATA TYPE= NMR SPECTRUM", "##DATA TYPE= NMR FID"), /raw FID/);
refuses(nt.replace("##UNITS= HZ", "##UNITS= SECONDS"), /raw FID/);
refuses(file(ys, "SQZ").replace("##DATA TYPE= NMR SPECTRUM", "##DATA TYPE= nD NMR SPECTRUM\n##NUM DIM= 2"), /1D spectra only/);
// NMR in Hz with no frequency; a value too large to be a number.
refuses(file(ys, "AFFN").replace("##.OBSERVE FREQUENCY= 400.13\n", "").replace("##XUNITS= PPM", "##XUNITS= HZ"), /no observe frequency/);
refuses(sample("1 1e400 2 3 3 2 1 0 -1 -2 -3".replace("1e400", "1E+400")), /is not a number/);
// Random bytes, and every prefix of a sound file, are refused or read; none throws anything but a plain Error.
let seed = 7;
const rand = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
const sound = file(ys, "DUP");
for (let k = 0; k < 300; k++) {
  const cut = sound.slice(0, Math.floor(rand() * sound.length)), noise = Array.from({ length: 200 }, () => String.fromCharCode(32 + Math.floor(rand() * 95))).join("");
  for (const t of [cut, `##TITLE=x\n##XYDATA=(X++(Y..Y))\n${noise}`, sound.replace(/[A-Za-z%@]/, () => noise[0])]) {
    try { readJcamp(t); } catch (e) { assert.ok(e instanceof Error && e.message.length > 10 && !/undefined|TypeError|Cannot read/.test(e.message), (e as Error).message); }
  }
}

// --- Galactic SPC ---------------------------------------------------------------------------------------------------

// An SPC file by hand, as Galactic's format document lays it out: the 512-byte header (flags, version 4B or 4C,
// experiment, exponent, points, first and last X, subfiles, X and Y units, a comment), the X values when the flags say
// so, then each subfile's 32-byte header (its exponent and, in an XYXY file, its points) and Y values. exp -128 (0x80)
// is floats; otherwise whole numbers of 32 bits, or 16 with TSPREC (flag 1).
type Spc = { le?: boolean; flags?: number; exper?: number; exp?: number; xtype?: number; ytype?: number; first?: number; last?: number; ys: number[][]; xs?: number[][]; comment?: string; version?: number };
function spcFile(o: Spc): Uint8Array {
  const le = o.le ?? true, flags = o.flags ?? 0, exp = o.exp ?? -128, size = exp === -128 || !(flags & 1) ? 4 : 2, xy = !!(flags & 0x40);
  const head = new DataView(new ArrayBuffer(512));
  head.setUint8(0, flags); head.setUint8(1, o.version ?? (le ? 0x4b : 0x4c)); head.setUint8(2, o.exper ?? 0); head.setInt8(3, exp);
  head.setUint32(4, xy ? 0 : o.ys[0].length, le); head.setFloat64(8, o.first ?? 0, le); head.setFloat64(16, o.last ?? 0, le); head.setUint32(24, o.ys.length, le);
  head.setUint8(28, o.xtype ?? 0); head.setUint8(29, o.ytype ?? 0);
  [...(o.comment ?? "")].forEach((c, i) => head.setUint8(88 + i, c.charCodeAt(0)));
  const chunks = [new Uint8Array(head.buffer)];
  const f32 = (vs: number[]) => { const d = new DataView(new ArrayBuffer(4 * vs.length)); vs.forEach((v, i) => d.setFloat32(4 * i, v, le)); return new Uint8Array(d.buffer); };
  if (flags & 0x80 && !xy) chunks.push(f32(o.xs![0]));
  o.ys.forEach((ys, k) => {
    const sub = new DataView(new ArrayBuffer(32));
    sub.setInt8(1, exp);
    sub.setUint32(16, xy ? ys.length : 0, le);
    chunks.push(new Uint8Array(sub.buffer));
    if (xy) chunks.push(f32(o.xs![k]));
    if (exp === -128) chunks.push(f32(ys));
    else {
      const d = new DataView(new ArrayBuffer(size * ys.length)), scale = 2 ** (exp - 8 * size);
      ys.forEach((v, i) => (size === 2 ? d.setInt16(2 * i, Math.round(v / scale), le) : d.setInt32(4 * i, Math.round(v / scale), le)));
      chunks.push(new Uint8Array(d.buffer));
    }
  });
  const out = new Uint8Array(chunks.reduce((n, c) => n + c.length, 0));
  chunks.reduce((at, c) => (out.set(c, at), at + c.length), 0);
  return out;
}
// An FT-IR spectrum in %T, 4000 to 400 cm⁻¹ in steps of 1, with three bands.
const irY = Array.from({ length: 3601 }, (_, i) => { const x = 4000 - i; return 100 - [[1740, 80], [1240, 60], [2980, 20]].reduce((s, [p, h]) => s + (h * 100) / ((x - p) ** 2 + 100), 0); });
const ftir = (more: Partial<Spc> = {}) => spcFile({ exper: 4, xtype: 1, ytype: 128, first: 4000, last: 400, ys: [irY], comment: "Ethyl acetate, film", ...more });
{
  // Floats, little endian: the trace, its units, its kind and the comment as its title.
  const [s] = readSpc(ftir());
  assert.deepEqual([s.title, s.kind, s.xUnit, s.yUnit, s.first, s.last, s.y.length, s.xs], ["Ethyl acetate, film", "ir", "cm⁻¹", "%T", 4000, 400, 3601, undefined]);
  assert.ok(s.y.every((v, i) => Math.abs(v - irY[i]) < 1e-4));
  // Big endian (4C) with 32-bit whole numbers, and 16-bit ones (TSPREC): the same trace, to their precision.
  for (const [more, tol] of [[{ le: false, exp: 8 }, 1e-6], [{ exp: 8, flags: 1 }, 0.004]] as [Partial<Spc>, number][]) {
    const [t] = readSpc(ftir(more));
    assert.ok(t.y.every((v, i) => Math.abs(v - irY[i]) < tol), JSON.stringify(more));
  }
  // The X values in the file (TXVALS): a UV-Vis spectrum on uneven wavelengths, read where they are.
  const nm = [200, 210, 225, 250, 300, 400], [uv] = readSpc(spcFile({ flags: 0x80, exper: 7, xtype: 3, ytype: 2, ys: [[0.1, 0.9, 0.4, 0.2, 0.6, 0.05]], xs: [nm] }));
  assert.deepEqual([uv.kind, uv.xUnit, uv.yUnit, [...uv.xs!], uv.first, uv.last], ["uv", "nm", "A", nm, 200, 400]);
  // A mass spectrum with its own X values in each subfile (XYXY, several subfiles): the first, as sticks.
  const [ms] = readSpc(spcFile({ flags: 0x04 | 0x40 | 0x80, exper: 9, xtype: 9, ys: [[100, 18, 8], [5, 5]], xs: [[43, 61, 88], [10, 20]] }));
  assert.deepEqual([ms.kind, ms.xUnit, ms.sticks, [...ms.xs!], [...ms.y]], ["ms", "m/z", true, [43, 61, 88], [100, 18, 8]]);
  // Several subfiles on one X axis: the first.
  const [first] = readSpc(spcFile({ flags: 0x04, exper: 7, xtype: 3, first: 200, last: 300, ys: [[1, 2, 3], [4, 5, 6]] }));
  assert.deepEqual([...first.y], [1, 2, 3]);
  // NMR in ppm takes its nucleus from its width.
  assert.equal(readSpc(spcFile({ exper: 10, xtype: 10, first: 12, last: -1, ys: [[0, 1, 0, 2]] }))[0].nucleus, "1H");
  // As the app hands it over (src-tauri/src/spectrum.rs): its name, its bytes in base64.
  const env = `${SPC}${JSON.stringify({ name: "film.spc", data: Buffer.from(ftir({ comment: "" })).toString("base64") })}`;
  assert.ok(isSpectrum(env));
  assert.equal(readSpcText(env)[0].title, "film.spc");
  // Refused with a plain message: not SPC, the old format, cut short, too many points, an interferogram, a FID, NMR in
  // Hz, a value that is not a number, and a damaged envelope.
  const no = (b: Uint8Array | string, why: RegExp) => assert.throws(() => (typeof b === "string" ? readSpcText(b) : readSpc(b)), why);
  no(new TextEncoder().encode("##TITLE=x"), /not an SPC spectrum/);
  no(ftir({ version: 0x4d }), /old format/);
  no(ftir().slice(0, 300), /header is cut short/);
  no(ftir().slice(0, 600), /cut short/);
  const huge = ftir();
  new DataView(huge.buffer).setUint32(4, MAX_POINTS + 1, true);
  no(huge, /2,097,153 points/);
  no(ftir({ ytype: 1 }), /interferogram/);
  no(spcFile({ exper: 10, xtype: 4, ys: [[1, 2]] }), /raw FID/);
  no(spcFile({ exper: 10, xtype: 6, ys: [[1, 2]] }), /no shift scale in ppm/);
  no(spcFile({ ys: [[1, NaN, 2]] }), /not a number/);
  no(`${SPC}{"data": 5}`, /cannot read this SPC file/);
  // Random bytes after a sound header, and every prefix of a sound file: refused or read, never anything but an Error.
  const good = ftir({ exp: 8, flags: 1 });
  for (let k = 0; k < 300; k++) {
    const cut = good.slice(0, Math.floor(rand() * good.length)), noisy = good.slice();
    for (let j = 0; j < 8; j++) noisy[Math.floor(rand() * 600)] = Math.floor(rand() * 256);
    for (const b of [cut, noisy]) {
      try { readSpc(b); } catch (e) { assert.ok(e instanceof Error && e.message.length > 10 && !/undefined|TypeError|Cannot read|RangeError|offset/.test(e.message), (e as Error).message); }
    }
  }
}
console.log("jcamp.check: ok");
