// Run: node src/namer-complex.check.ts. Names for coordination compounds (complexes.ts), by additive nomenclature
// (IUPAC 2005 Red Book IR-9, IR-10). Each structure is drawn from SMILES as Octet draws it (a bracket atom with
// hydrogens on a metal, [NH3], as the label NH3), and must get exactly the name given here; complexes.ts gives a name
// only when its own check reads it back as the drawing. Then names one term away from right must fail that check,
// structures Octet cannot name yet must get no name, and a large complex must be named quickly.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import type { Mol } from "./render.ts";

const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("namer-complex.check: skipped (no OPSIN build)"); process.exit(0); }
// chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
const gl = globalThis as Record<string, unknown>;
gl.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
gl.getComputedStyle = () => ({ getPropertyValue: () => "10" });
gl.window = globalThis;
gl.self = { location: { origin: "file://" } };
gl.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const chem = await import("./chem.ts");
await chem.ready;
const pack = readFileSync(new URL("opsin-data.bin", dir)), files = new Map<string, Int8Array>();
for (let p = 0; ; ) {
  const n = pack.readUInt16BE(p); p += 2;
  if (!n) break;
  const name = pack.toString("latin1", p, p + n); p += n;
  const size = pack.readInt32BE(p); p += 4;
  files.set(name, new Int8Array(pack.buffer, pack.byteOffset + p, size)); p += size;
}
gl.opsinResource = (name: string) => files.get(name) ?? null;
const opsin = await import(new URL("opsin.js", dir).href);
opsin.init();
const { attachOpsin, nameToAtoms, nameToSmiles } = await import("./names.ts");
attachOpsin(opsin, readFileSync(new URL("names.txt", dir), "utf8"));
const { complexName, complexNameReads } = await import("./complexes.ts");
// As the app names: OPSIN through names.ts, InChI and CIP labels by Indigo through chem.ts.
const api = { read: nameToSmiles, atoms: nameToAtoms, inchi: chem.toInchi, aux: chem.toInchiAux, cip: chem.cipOf };

// A structure drawn from SMILES, labels expanded as Structure to Name expands them. A bracket atom with hydrogens bonded
// to a metal is drawn as its label (NH3, OH2), as Sam draws ammine and aqua ligands.
const METALS = /^\[(?:Li|Na|K|Mg|Ca|Ti|V|Cr|Mn|Fe|Co|Ni|Cu|Zn|Zr|Mo|Ru|Rh|Pd|Ag|W|Re|Os|Ir|Pt|Au)\b/;
// metalText: the metals' label as drawn, Os(II).
function drawn(smiles: string, metalText?: string): Mol {
  return chem.expandLabels(labelled(smiles, metalText));
}
function labelled(smiles: string, metalText?: string): Mol {
  const m = chem.parseStructure(smiles), tokens = [...smiles.matchAll(/\[[^\]]+\]|Cl|Br|[BCNOPSFI]|[bcnops]/g)].map((t) => t[0]);
  // The atoms come in the SMILES's order, then any H drawn to carry a stereocentre's wedge (chem.ts placeWedges).
  assert.equal(tokens.length, m.atoms.filter((a, i) => i < tokens.length || a.label !== "H").length, `atoms of ${smiles}`);
  const metal = new Set(tokens.flatMap((t, i) => (METALS.test(t) ? [i] : [])));
  const atoms = m.atoms.map((a, i) => {
    const h = /^\[([A-Z][a-z]?)H(\d*)/.exec(tokens[i]);
    const onMetal = m.bonds.some((b) => b.atoms.includes(i) && metal.has(b.atoms[0] === i ? b.atoms[1] : b.atoms[0]));
    return h && onMetal ? { ...a, text: `${h[1]}H${h[2]}` } : metalText && metal.has(i) ? { ...a, text: metalText } : a;
  });
  return { ...m, atoms };
}
const nameOf = (smiles: string) => complexName(drawn(smiles), api);

// Sam's complexes (his ChemDraw drawings, as SMILES written here). They are drawn with no charges, the metal and every
// ligand neutral, so nothing in the drawing fixes the oxidation number and the names give none (IR-9.2.2.4 makes it
// optional). Drawn with the 2+ charge, the names end (2+); with the metal labelled Os(II), osmium(II).
const SAM: [string, string, string][] = [
  // Os(II) bis(terpyridine) photocatalysts. Three or more identical rings in a chain are a ring assembly (P-28.2.1):
  // 2,2':6',2''-terpyridine, the rings primed in turn, each N its ring's 1; κ3N1,N1',N1'' cites all three (IR-9.2.4.2).
  ["Os(tpy)2", "C12=N([Os]345(N6C(C7N3=C(C3C=CC=CN=34)C=CC=7)=CC=CC=6)N3=C1C=CC=C3C1N5=CC=CC=1)C=CC=C2", "bis(2,2':6',2''-terpyridine-κ3N1,N1',N1'')osmium"],
  ["Os(MeOPh-tpy)2", "C12=N([Os]345(N6C(C7N3=C(C3C=CC=CN=34)C=C(C3C=CC(OC)=CC=3)C=7)=CC=CC=6)N3=C1C=C(C1C=CC(OC)=CC=1)C=C3C1N5=CC=CC=1)C=CC=C2",
    "bis[4'-(4-methoxyphenyl)-2,2':6',2''-terpyridine-κ3N1,N1',N1'']osmium"],
  ["Os(MeOPh-tpy)2, drawn the other way", "C1C=C2C3C=C(C4C=CC(OC)=CC=4)C=C4C5C=CC=C[N]=5[Os]56([N]7C(C8C=CC=C[N]=85)=CC(C5C=CC(OC)=CC=5)=CC=7C5=CC=CC=[N]56)([N]2=CC=1)[N]=34",
    "bis[4'-(4-methoxyphenyl)-2,2':6',2''-terpyridine-κ3N1,N1',N1'']osmium"],
  // The pyrimidinyl ligand: pyrimidine is the senior ring (P-44.2.1.2), so the namer's name has it as parent and the
  // other rings as substituents. Each donor N is cited after the part of the name that holds it (IR-9.2.4.2).
  ["Os(pym-py-pym)2", "C12=N([Os]345(N6C(C7N3=C(C3N=CC=CN=34)C=C(C3C=CC(OC)=CC=3)C=7)=NC=CC=6)N3=C1C=C(C1C=CC(OC)=CC=1)C=C3C1N5=CC=CN=1)C=CC=N2",
    "bis{2-[4-(4-methoxyphenyl)-6-(pyrimidin-2-yl-κN1)pyridin-2-yl-κN1]pyrimidine-κN1}osmium"],
  ["Os(pym-py-pym)2, drawn the other way", "[Os]1234([N]5C(=NC=CC=5)C5=[N]1C(=CC(C1C=CC(OC)=CC=1)=C5)C1=[N]2C=CC=N1)[N]1C(=NC=CC=1)C1=[N]3C(=CC(C2C=CC(OC)=CC=2)=C1)C1=[N]4C=CC=N1",
    "bis{2-[4-(4-methoxyphenyl)-6-(pyrimidin-2-yl-κN1)pyridin-2-yl-κN1]pyrimidine-κN1}osmium"],
  ["Ru(bpy)3", "C12C3=CC=CC=N3[Ru]34(N5=CC=CC=C5C5N3=CC=CC=5)(N=1C=CC=C2)N1=C(C2C=CC=CN=24)C=CC=C1", "tris(2,2'-bipyridine-κ2N1,N1')ruthenium"],
  // Sam's file labels this Os "Os(II)" (tested below); drawn as Os, the name gives no oxidation number. Phenanthroline's
  // N atoms are 1 and 10 (fused ring numbering, P-25.3).
  ["Os(phen)3", "[Os]123(N4=CC=CC5=CC=C6C=CC=N1C6=C54)(N1=CC=CC4=CC=C5C=CC=N2C5=C41)N1=CC=CC2=CC=C4C=CC=N3C4=C21", "tris(1,10-phenanthroline-κ2N1,N10)osmium"],
  // Jacobsen's catalyst. The salen dianion as the namer names it, with its (R,R) cyclohexane. Its C=N bonds are in the
  // chelate rings, so their E or Z is the chelate's and is not cited. All of its N and O atoms bond to Mn: κ2N,N',κ2O,O'
  // leaves no doubt (IR-9.2.4.2: primes in simple cases). Mn(III): two phenolate O and chloride, three negative charges.
  ["Jacobsen's catalyst", "[C@H]12[N]3[Mn]4(Cl)([N]([C@@H]1CCCC2)=CC1=CC(C(C)(C)C)=CC(C(C)(C)C)=C1O4)OC1=C(C=3)C=C(C(C)(C)C)C=C1C(C)(C)C",
    "chlorido(2,4-di-tert-butyl-6-({[(1R,2R)-2-{[(3,5-di-tert-butyl-2-oxidophenyl)methylidene]amino}cyclohexyl]imino}methyl)phenolato-κ2N,N',κ2O,O')manganese(III)"],
];
const ESP = "[Rh]%10%11%12%13%14.[Rh]%10%15%16%17%18.O%11C(=O%15)C(C)(C)Cc1cccc(c1)CC(C)(C)C(O%16)=O%12.O%13C(=O%17)C(C)(C)Cc1cccc(c1)CC(C)(C)C(O%18)=O%14";
const OTHERS: [string, string, string][] = [
  // A complex ion takes its charge number (IR-9.2.2.4); its counter-ions follow, their number given by the charges.
  ["[Ru(bpy)3]2+", "C12C3=CC=CC=N3[Ru+2]34(N5=CC=CC=C5C5N3=CC=CC=5)(N=1C=CC=C2)N1=C(C2C=CC=CN=24)C=CC=C1", "tris(2,2'-bipyridine-κ2N1,N1')ruthenium(2+)"],
  ["[Ru(bpy)3](PF6)2", "C12C3=CC=CC=N3[Ru+2]34(N5=CC=CC=C5C5N3=CC=CC=5)(N=1C=CC=C2)N1=C(C2C=CC=CN=24)C=CC=C1.F[P-](F)(F)(F)(F)F.F[P-](F)(F)(F)(F)F",
    "tris(2,2'-bipyridine-κ2N1,N1')ruthenium(2+) hexafluorophosphate"],
  // An anion's central atom takes -ate (IR-9.2.2, Table X: ferrate); cations come first (IR-5.4).
  ["K3[Fe(CN)6]", "[K+].[K+].[K+].N#C[Fe-3](C#N)(C#N)(C#N)(C#N)C#N", "potassium hexacyanidoferrate(3-)"],
  ["K4[Fe(CN)6]", "[K+].[K+].[K+].[K+].N#C[Fe-4](C#N)(C#N)(C#N)(C#N)C#N", "potassium hexacyanidoferrate(4-)"],
  ["K2[PtCl4]", "[K+].[K+].Cl[Pt-2](Cl)(Cl)Cl", "potassium tetrachloridoplatinate(2-)"],
  // No elision in tetraammine, hexaammine (IR-9.2.2.2). A d8 metal with four donor atoms drawn as a cross is square
  // planar: [Ma2b2] takes cis or trans (IR-9.3.3.3) as drawn.
  ["cisplatin", "[NH3][Pt]([NH3])(Cl)Cl", "cis-diamminedichloridoplatinum(II)"],
  ["transplatin", "[NH3][Pt](Cl)(Cl)[NH3]", "trans-diamminedichloridoplatinum(II)"],
  ["[Co(NH3)6]Cl3", "[NH3][Co+3]([NH3])([NH3])([NH3])([NH3])[NH3].[Cl-].[Cl-].[Cl-]", "hexaamminecobalt(3+) chloride"],
  ["Wilkinson's catalyst", "Cl[Rh](P(c1ccccc1)(c1ccccc1)c1ccccc1)(P(c1ccccc1)(c1ccccc1)c1ccccc1)P(c1ccccc1)(c1ccccc1)c1ccccc1", "chloridotris(triphenylphosphane)rhodium(I)"],
  ["Pd(PPh3)4", "C1=CC=C(C=C1)P(C1=CC=CC=C1)(C1=CC=CC=C1)[Pd](P(C1=CC=CC=C1)(C1=CC=CC=C1)C1=CC=CC=C1)(P(C1=CC=CC=C1)(C1=CC=CC=C1)C1=CC=CC=C1)P(C1=CC=CC=C1)(C1=CC=CC=C1)C1=CC=CC=C1",
    "tetrakis(triphenylphosphane)palladium"],
  ["[Cu(en)2]2+", "C1C[NH2][Cu+2]2([NH2]1)[NH2]CC[NH2]2", "bis(ethane-1,2-diamine-κ2N,N')copper(2+)"],
  ["PtCl2(py)2", "Cl[Pt](Cl)(N1=CC=CC=C1)N1=CC=CC=C1", "dichloridobis(pyridine)platinum(II)"],
  // N-bonded nitrite (IR-9.2.4.2: nitrito-κN), drawn N+ and O-.
  ["[Co(NH3)5(NO2)]Cl2", "[O-][N+](=O)[Co+2]([NH3])([NH3])([NH3])([NH3])[NH3].[Cl-].[Cl-]", "pentaammine(nitrito-κN)cobalt(2+) chloride"],
  // A monodentate carboxylate needs no κ (IR-9.2.4.1). Acetato is a simple name: di, and no enclosing marks; the
  // triphenylphosphane has a multiplying prefix of its own, so bis() (IR-9.2.2.2).
  ["Pd(OAc)2(PPh3)2", "CC(=O)O[Pd](OC(C)=O)(P(c1ccccc1)(c1ccccc1)c1ccccc1)P(c1ccccc1)(c1ccccc1)c1ccccc1", "trans-diacetatobis(triphenylphosphane)palladium(II)"],
  // [Ma2bc]: the polyhedral symbol and configuration index (IR-9.3.3.3). Cl is priority 1, P 2, O 3; O trans to Cl.
  ["Pd(OAc)Cl(PPh3)2", "CC(=O)O[Pd](Cl)(P(c1ccccc1)(c1ccccc1)c1ccccc1)P(c1ccccc1)(c1ccccc1)c1ccccc1", "(SP-4-3)-acetatochloridobis(triphenylphosphane)palladium(II)"],
  // Octanoato begins as octa does, so it is enclosed and counted with bis.
  ["Pd(O2CC7H15)2(PPh3)2", "CCCCCCCC(=O)O[Pd](OC(=O)CCCCCCC)(P(c1ccccc1)(c1ccccc1)c1ccccc1)P(c1ccccc1)(c1ccccc1)c1ccccc1", "trans-bis(octanoato)bis(triphenylphosphane)palladium(II)"],
  // Carboplatin: one O of each carboxylate group, O and O'' with the O atoms numbered along the name (O, O' those of
  // the first group; as the Red Book numbers edta's, IR-9.2.5.2 Example 5).
  ["carboplatin", "[NH3][Pt]1(OC(=O)C2(CCC2)C(=O)O1)[NH3]", "diammine(cyclobutane-1,1-dicarboxylato-κ2O,O'')platinum(II)"],
  // acac drawn as its enolate: 4-oxopent-2-en-2-olate, both O atoms donors.
  ["Fe(acac)3", "CC1=CC(C)=O[Fe]23(O1)(OC(C)=CC(C)=O2)OC(C)=CC(C)=O3", "tris(4-oxopent-2-en-2-olato-κ2O,O')iron(III)"],
  ["Cu(acac)2", "CC1=CC(C)=O[Cu]2(O1)OC(C)=CC(C)=O2", "bis(4-oxopent-2-en-2-olato-κ2O,O')copper(II)"],
  // edta, hexadentate: each N and one O of each carboxylate group bonds to Co. The namer's name for the ligand, each
  // donor cited after its part (IR-9.2.4.2, as the Red Book's second name for Example 8).
  ["Na[Co(edta)]", "[Na+].[Co-]%11%12%13%14%15[N](CC(=O)O%11)(CC(=O)O%12)CC[N]%15(CC(=O)O%13)CC(=O)O%14",
    "sodium [({2-[bis(carboxylatomethyl-κO)amino-κN]ethyl}(carboxylatomethyl-κO)amino-κN)acetato-κO]cobaltate(1-)"],
  // Organometallic: carbon ligands as substituent prefixes (IR-10.2.2), carbenes as -ylidene (IR-10.2.4), and no
  // oxidation number (IR-10.2.1.4). Benzylidene (P-29.6.1) and the NHC's name, under b (bis), come before chlorido.
  ["Grubbs II", "Cl[Ru](Cl)(=CC1=CC=CC=C1)(=C1N(C2=C(C)C=C(C)C=C2C)CCN1C1=C(C)C=C(C)C=C1C)P(C1CCCCC1)(C1CCCCC1)C1CCCCC1",
    "(benzylidene)[1,3-bis(2,4,6-trimethylphenyl)imidazolidin-2-ylidene]dichlorido(tricyclohexylphosphane)ruthenium"],
  ["Vaska's complex", "Cl[Ir](=C=O)(P(c1ccccc1)(c1ccccc1)c1ccccc1)P(c1ccccc1)(c1ccccc1)c1ccccc1", "(SP-4-3)-carbonylchloridobis(triphenylphosphane)iridium"],
  // Rh2(OAc)4: four bridging acetates, each O to one Rh (IR-9.2.5.4 Example 6), and the Rh-Rh bond (IR-9.2.5.3).
  ["Rh2(OAc)4", "[Rh]%10%13%14(OC(C)=O%11)OC(C)=O%12.[Rh]%10%11%12(OC(C)=O%13)OC(C)=O%14", "tetrakis(μ-acetato-κO:κO')dirhodium(Rh—Rh)"],
  // A carbene on one Rh: the Rh atoms are no longer alike, so each κ names its Rh, the carbene's Rh (more donor atoms)
  // 1 (IR-9.2.5.5).
  ["Rh2(OAc)4 carbene", "[Rh]%10%13%14(=C(C(=O)OC)c1ccccc1)(OC(C)=O%11)OC(C)=O%12.[Rh]%10%11%12(OC(C)=O%13)OC(C)=O%14",
    "tetrakis(μ-acetato-1κO:2κO')(2-methoxy-2-oxo-1-phenylethylidene-1κC)dirhodium(Rh—Rh)"],
  // Rh2(esp)2: esp named as two identical units on a benzene ring (multiplicative name, P-15.3), each carboxylate O to
  // one Rh: the κ in the multiplied unit applies to each unit (IR-9.2.4.2). Its primes are OPSIN's O and O' of the unit.
  ["Rh2(esp)2", ESP, "bis[μ-3,3'-(1,3-phenylene)bis(2,2-dimethylpropanoato-κO:κO')]dirhodium(Rh—Rh)"],
  ["Rh2(esp)2 carbene", ESP.replace("[Rh]%10%11%12%13%14", "[Rh]%10%11%12%13%14=C(C(=O)OC)c1ccccc1"),
    "(2-methoxy-2-oxo-1-phenylethylidene-1κC)bis[μ-3,3'-(1,3-phenylene)bis(2,2-dimethylpropanoato-1κO:2κO')]dirhodium(Rh—Rh)"],
  ["Mn2(CO)10", "O=C=[Mn](=C=O)(=C=O)(=C=O)(=C=O)[Mn](=C=O)(=C=O)(=C=O)(=C=O)=C=O", "bis(pentacarbonylmanganese)(Mn—Mn)"],
];
for (const [label, smiles, want] of [...SAM, ...OTHERS]) assert.equal(nameOf(smiles), want, label);
console.log(`namer-complex.check: ${SAM.length} of Sam's complexes and ${OTHERS.length} others named as IR-9 names them`);

// Structure to Name as the editor runs it (Editor.tsx nameFor): the namer's name read back by OPSIN first, then
// Octet's own names, then a complex's name.
const { checkedName, setComplexNamer, setNamer } = await import("./naming.ts");
const { iupacName } = await import("./namer.ts");
setNamer(iupacName);
setComplexNamer((m) => complexName(m, api));
const inchiOf = (s: Mol | string) => { try { return chem.toInchi(typeof s === "string" ? chem.parseStructure(s) : s); } catch { return undefined; } };
const editorName = (smiles: string) => { const d = drawn(smiles); return checkedName(d, d, nameToSmiles, inchiOf, chem.cipOf); };
assert.equal(editorName(OTHERS[1][1]), OTHERS[1][2]);
assert.equal(editorName("O=C=[Fe](=C=O)(=C=O)(=C=O)=C=O"), "pentacarbonyliron"); // the namer's, read back by OPSIN
assert.equal(editorName("CCO"), "ethanol");

// Names one term away from right: the check must turn each down.
const wrong: [string, string[]][] = [
  ["C12C3=CC=CC=N3[Ru+2]34(N5=CC=CC=C5C5N3=CC=CC=5)(N=1C=CC=C2)N1=C(C2C=CC=CN=24)C=CC=C1", [
    "tris(2,2'-bipyridine-κ2N1,N1')ruthenium(3+)", "bis(2,2'-bipyridine-κ2N1,N1')ruthenium(2+)", "tris(2,2'-bipyridine-κN1)ruthenium(2+)",
    "tris(2,2'-bipyridine-κ2N1,N1')osmium(2+)", "tris(4,4'-bipyridine-κ2N1,N1')ruthenium(2+)", "tris(2,2'-bipyridine-κ2N1,N1')ruthenium(II)",
    "tris(2,2'-bipyridine-κ2N1,N3')ruthenium(2+)", "tris(2,2'-bipyridine)ruthenium(2+)", "tris(2,2'-bipyridine-κ2N1,N1')ruthenate(2+)",
    "tris(2,2'-bipyridine-κ2N1,N1')ruthenium",
  ]],
  ["Cl[Rh](P(c1ccccc1)(c1ccccc1)c1ccccc1)(P(c1ccccc1)(c1ccccc1)c1ccccc1)P(c1ccccc1)(c1ccccc1)c1ccccc1", [
    "chloridotris(triphenylphosphane)rhodium(III)", "chloridobis(triphenylphosphane)rhodium(I)", "bromidotris(triphenylphosphane)rhodium(I)",
    "dichloridotris(triphenylphosphane)rhodium(I)", "chloridotris(triphenylphosphane)dirhodium(I)",
  ]],
  ["[K+].[K+].[K+].N#C[Fe-3](C#N)(C#N)(C#N)(C#N)C#N", [
    "potassium hexacyanidoferrate(4-)", "sodium hexacyanidoferrate(3-)", "potassium pentacyanidoferrate(3-)", "potassium hexacyanidoiron(3-)",
    "hexacyanidoferrate(3-) potassium",
  ]],
  ["CC1=CC(C)=O[Fe]23(O1)(OC(C)=CC(C)=O2)OC(C)=CC(C)=O3", ["tris(4-oxopent-2-en-2-olato-κO)iron(III)", "tris(4-oxopent-2-en-2-olato-κ2O,O')iron(II)"]],
  ["[Rh]%10%13%14(OC(C)=O%11)OC(C)=O%12.[Rh]%10%11%12(OC(C)=O%13)OC(C)=O%14", [
    "tetrakis(μ-acetato-κO:κO')dirhodium", "tetrakis(μ-acetato-κ2O,O')dirhodium(Rh—Rh)", "tetrakis(acetato-κO)dirhodium(Rh—Rh)",
    "tris(μ-acetato-κO:κO')dirhodium(Rh—Rh)",
  ]],
  ["[Rh]%10%13%14(=C(C(=O)OC)c1ccccc1)(OC(C)=O%11)OC(C)=O%12.[Rh]%10%11%12(OC(C)=O%13)OC(C)=O%14", [
    // The carbene's Rh is 1 by the numbering rule, so -2κC is turned down although it reads as the same structure.
    "tetrakis(μ-acetato-1κO:2κO')(2-methoxy-2-oxo-1-phenylethylidene-2κC)dirhodium(Rh—Rh)",
    "tetrakis(μ-acetato-κO:κO')(2-methoxy-2-oxo-1-phenylethylidene)dirhodium(Rh—Rh)",
  ]],
  ["C12=N([Os]345(N6C(C7N3=C(C3C=CC=CN=34)C=CC=7)=CC=CC=6)N3=C1C=CC=C3C1N5=CC=CC=1)C=CC=C2", [
    // No charge on the metal or a ligand and no label: no oxidation number is right, 0 or II.
    "bis(2,2':6',2''-terpyridine-κ2N1,N1')osmium", "bis(2,2':6',2''-terpyridine-κ3N1,N1',N1'')osmium(II)",
    "bis(2,2':6',2''-terpyridine-κ3N1,N1',N1'')osmium(0)",
  ]],
  ["C12=N([Os]345(N6C(C7N3=C(C3N=CC=CN=34)C=C(C3C=CC(OC)=CC=3)C=7)=NC=CC=6)N3=C1C=C(C1C=CC(OC)=CC=1)C=C3C1N5=CC=CN=1)C=CC=N2", [
    "bis{2-[4-(4-methoxyphenyl)-6-(pyrimidin-2-yl)pyridin-2-yl-κN1]pyrimidine-κN1}osmium",
    "bis{2-[4-(4-methoxyphenyl)-6-(pyrimidin-2-yl-κN1)pyridin-2-yl]pyrimidine-κN1}osmium",
    "bis{2-[4-(4-methoxyphenyl-κO)-6-(pyrimidin-2-yl-κN1)pyridin-2-yl]pyrimidine-κN1}osmium",
  ]],
  ["CC(=O)O[Pd](OC(C)=O)(P(c1ccccc1)(c1ccccc1)c1ccccc1)P(c1ccccc1)(c1ccccc1)c1ccccc1", [
    "triacetatobis(triphenylphosphane)palladium(II)", "diacetatobis(triphenylphosphane)palladium(0)", "dibenzoatobis(triphenylphosphane)palladium(II)",
    "diacetatotris(triphenylphosphane)palladium(II)", "acetatobis(triphenylphosphane)palladium(II)",
  ]],
  ["[NH3][Pt]1(OC(=O)C2(CCC2)C(=O)O1)[NH3]", ["diammine(cyclobutane-1,1-dicarboxylato-κ2O,O')platinum(II)", "diammine(cyclobutane-1,1-dicarboxylato-κO)platinum(II)"]],
  [ESP, ["bis[μ-3,3'-(1,3-phenylene)bis(2,2-dimethylpropanoato-κ2O,O')]dirhodium(Rh—Rh)", "bis[μ-3,3'-(1,3-phenylene)bis(2,2-dimethylpropanoato-κO)]dirhodium(Rh—Rh)"]],
  ["[Na+].[Co-]%11%12%13%14%15[N](CC(=O)O%11)(CC(=O)O%12)CC[N]%15(CC(=O)O%13)CC(=O)O%14", [
    "sodium [({2-[bis(carboxylatomethyl-κO)amino-κN]ethyl}(carboxylatomethyl)amino-κN)acetato-κO]cobaltate(1-)",
    "sodium [({2-[bis(carboxylatomethyl-κO)amino]ethyl}(carboxylatomethyl-κO)amino-κN)acetato-κO]cobaltate(1-)",
    "sodium [({2-[bis(carboxylatomethyl-κO)amino-κN]ethyl}(carboxylatomethyl-κO)amino-κN)acetato-κO]cobaltate(2-)",
  ]],
];
let turned = 0;
for (const [smiles, names] of wrong) {
  const m = drawn(smiles);
  for (const name of names) { assert.equal(complexNameReads(name, m, api), false, name); turned++; }
}
// And the right names read back as right.
for (const [, smiles, want] of [...SAM, ...OTHERS]) assert.ok(complexNameReads(want, drawn(smiles), api), want);
console.log(`namer-complex.check: ${turned} names one term away from right turned down`);

// Unlike metals, and three or more (IR-9.2.5.5 to IR-9.2.5.7): the central atoms in the order of Table VI and numbered
// by IR-9.2.5.6's rules, every ligand citing its metals, the central structural unit and the metal-metal bonds. The
// first, second and fourth are the Red Book's own examples.
const CO = "=C=O", co = (n: number) => `(${CO})`.repeat(n);
// Rh6(CO)16: an octahedron of Rh atoms (1 at the top, 2 to 5 round the middle, 6 at the bottom), two carbonyls on
// each, and four carbonyls each on a face, on alternate faces.
const rh6 = (() => {
  const edges = [[1, 2], [1, 3], [1, 4], [1, 5], [2, 3], [3, 4], [4, 5], [5, 2], [6, 2], [6, 3], [6, 4], [6, 5]], faces = [[1, 2, 3], [1, 4, 5], [6, 3, 4], [6, 5, 2]];
  let n = 10;
  const rings: string[][] = [[], [], [], [], [], [], []], caps: string[] = [];
  for (const [a, b] of edges) { rings[a].push(`%${n}`); rings[b].push(`%${n++}`); }
  for (const f of faces) { const ids = f.map(() => `%${n++}`); f.forEach((x, k) => rings[x].push(ids[k])); caps.push(`C${ids.join("")}=O`); }
  return [...[1, 2, 3, 4, 5, 6].map((x) => `[Rh]${rings[x].join("")}${co(2)}`), ...caps].join(".");
})();
const POLY: [string, string, string][] = [
  ["[(OC)5ReCo(CO)4]", `[Re]${co(5)}[Co]${co(4)}`, "nonacarbonyl-1κ5C,2κ4C-rheniumcobalt(Re—Co)"],
  ["[(OC)5ReMn(CO)5]", `[Mn]${co(5)}[Re]${co(5)}`, "decacarbonyl-1κ5C,2κ5C-rheniummanganese(Re—Mn)"],
  ["[(Ph3P)AuCo(CO)4]", `[Au](P(c1ccccc1)(c1ccccc1)c1ccccc1)[Co]${co(4)}`, "tetracarbonyl-1κ4C-(triphenylphosphane-2κP)cobaltgold(Co—Au)"],
  ["Ru3(CO)12", `[Ru]1${co(4)}[Ru]${co(4)}[Ru]1${co(4)}`, "dodecacarbonyl-1κ4C,2κ4C,3κ4C-triangulo-triruthenium(3 Ru—Ru)"],
  ["Os3(CO)12", `[Os]1${co(4)}[Os]${co(4)}[Os]1${co(4)}`, "dodecacarbonyl-1κ4C,2κ4C,3κ4C-triangulo-triosmium(3 Os—Os)"],
  // Fe3(CO)12: two carbonyls bridge Fe1 and Fe2, which have more donor atoms than Fe3 (rule b).
  ["Fe3(CO)12", `[Fe]1%10%12${co(3)}C(=O)[Fe]%11%12${co(3)}C1=O.[Fe]%10%11${co(4)}`, "di-μ-carbonyl-1:2κ4C-decacarbonyl-1κ3C,2κ3C,3κ4C-triangulo-triiron(3 Fe—Fe)"],
  ["Rh6(CO)16", rh6, "tetra-μ3-carbonyl-1:2:3κ3C;1:4:5κ3C;2:5:6κ3C;3:4:6κ3C-dodecacarbonyl-1κ2C,2κ2C,3κ2C,4κ2C,5κ2C,6κ2C-octahedro-hexarhodium(12 Rh—Rh)"],
  // A chain of three: no central structural unit, so each bond by its atoms' locants. The end atoms have more donor
  // atoms (rule b), so they are 1 and 2.
  ["[Os3(CO)12Cl2], a chain", `Cl[Os]${co(4)}[Os]${co(4)}[Os]${co(4)}Cl`, "dodecacarbonyl-1κ4C,2κ4C,3κ4C-dichlorido-1κCl,2κCl-triosmium(Os1—Os3)(Os2—Os3)"],
];
for (const [label, smiles, want] of POLY) {
  assert.equal(nameOf(smiles), want, label);
  assert.equal(editorName(smiles), want, `${label}, Structure to Name`);
}
const poly = (label: string) => drawn(POLY.find((x) => x[0] === label)![1]);
const wrongPoly: [string, string[]][] = [
  // Numbered against Table VI (Co first) reads as the same structure, but is not the rule's numbering.
  ["[(OC)5ReCo(CO)4]", ["nonacarbonyl-1κ4C,2κ5C-cobaltrhenium(Co—Re)", "nonacarbonyl-1κ5C,2κ4C-rheniumcobalt", "nonacarbonyl-1κ4C,2κ5C-rheniumcobalt(Re—Co)",
    "octacarbonyl-1κ4C,2κ4C-rheniumcobalt(Re—Co)", "nonacarbonyl-1κ5C,2κ4C-dirhenium(Re—Re)", "nonacarbonyl-1κ5C,2κ4C-rheniumcobalt(Re—Co)(1+)"]],
  ["Fe3(CO)12", ["di-μ-carbonyl-1:2κ4C-decacarbonyl-1κ4C,2κ3C,3κ3C-triangulo-triiron(3 Fe—Fe)", "di-μ-carbonyl-1:3κ4C-decacarbonyl-1κ3C,2κ3C,3κ4C-triangulo-triiron(3 Fe—Fe)",
    "di-μ-carbonyl-1:2κ4C-decacarbonyl-1κ3C,2κ3C,3κ4C-triiron(3 Fe—Fe)", "di-μ-carbonyl-1:2κ4C-decacarbonyl-1κ3C,2κ3C,3κ4C-triangulo-triiron(2 Fe—Fe)",
    "dodecacarbonyl-1κ4C,2κ4C,3κ4C-triangulo-triiron(3 Fe—Fe)", "di-μ-carbonyl-1:2κ4C-decacarbonyl-1κ3C,2κ3C,3κ4C-triangulo-triruthenium(3 Ru—Ru)"]],
  ["Rh6(CO)16", ["tetra-μ3-carbonyl-1:2:3κ3C;1:3:4κ3C;2:5:6κ3C;3:4:6κ3C-dodecacarbonyl-1κ2C,2κ2C,3κ2C,4κ2C,5κ2C,6κ2C-octahedro-hexarhodium(12 Rh—Rh)",
    "tetra-μ3-carbonyl-1:2:3κ3C;1:4:5κ3C;2:5:6κ3C;3:4:6κ3C-dodecacarbonyl-1κ2C,2κ2C,3κ2C,4κ2C,5κ2C,6κ2C-hexarhodium(12 Rh—Rh)"]],
  ["[Os3(CO)12Cl2], a chain", ["dodecacarbonyl-1κ4C,2κ4C,3κ4C-dichlorido-1κCl,3κCl-triosmium(Os1—Os2)(Os2—Os3)", "dodecacarbonyl-1κ4C,2κ4C,3κ4C-dichlorido-1κCl,2κCl-triosmium(2 Os—Os)",
    "dodecacarbonyl-1κ4C,2κ4C,3κ4C-dichlorido-1κCl,2κCl-triangulo-triosmium(3 Os—Os)"]],
];
let turnedPoly = 0;
for (const [label, names] of wrongPoly) for (const name of names) { assert.equal(complexNameReads(name, poly(label), api), false, name); turnedPoly++; }
console.log(`namer-complex.check: ${POLY.length} complexes of unlike metals or three or more named, ${turnedPoly} names one term away turned down`);

// η ligands drawn with a bond to each bonded atom (IR-10.2.5.1), their hydrogens as drawn: η and the number of atoms
// before the part of the name that holds them. The part, read alone, must have those atoms joined as drawn.
const ETA: [string, string, string][] = [
  ["Zeise's salt", "[K+].[CH2]1=[CH2][Pt-]1(Cl)(Cl)Cl", "potassium trichlorido(η2-ethene)platinate(1-)"],
  ["(η6-C6H6)Cr(CO)3", "[Cr]%11%12%13%14%15%16(=C=O)(=C=O)=C=O.[CH]%11=1[CH]%12=[CH]%13[CH]%14=[CH]%15[CH]%16=1", "(η6-benzene)tricarbonylchromium"],
  ["Cr(η6-C6H6)2", "[Cr]%11%12%13%14%15%16%21%22%23%24%25%26.[CH]%11=1[CH]%12=[CH]%13[CH]%14=[CH]%15[CH]%16=1.[CH]%21=1[CH]%22=[CH]%23[CH]%24=[CH]%25[CH]%26=1", "bis(η6-benzene)chromium"],
  ["(η6-toluene)Cr(CO)3", "[Cr]%11%12%13%14%15%16(=C=O)(=C=O)=C=O.C[C]%11=1[CH]%12=[CH]%13[CH]%14=[CH]%15[CH]%16=1", "tricarbonyl(methyl-η6-benzene)chromium"],
  ["[CpMn(CO)3]-, the ring drawn as an anion", "[Mn]%11%12%13%14%15(=C=O)(=C=O)=C=O.[CH-]1%11[CH]%12=[CH]%13[CH]%14=[CH]1%15", "tricarbonyl(η5-cyclopenta-2,4-dien-1-ido)manganate(1-)"],
  // Bonded through two separate runs of atoms: the locants of the bonded atoms before η (IR-10.2.5.1, Example 31:
  // [(1,2,5,6-η)-cycloocta-1,5-diene]). η4 would say four contiguous atoms. The ring's double bonds are drawn cis, so
  // its name cites Z as cycloocta-1,5-diene's own name does.
  ["Ni(cod)2", "[Ni]%11%12%13%14%21%22%23%24.[CH]1%11=[CH]%12CC[CH]%13=[CH]%14CC1.[CH]1%21=[CH]%22CC[CH]%23=[CH]%24CC1", "bis[(1,2,5,6-η)-(1Z,5Z)-cycloocta-1,5-diene]nickel"],
  ["[Rh(cod)Cl]2", "[Rh]%11%12%13%14%31%32.[Rh]%21%22%23%24%33%34.[CH]1%11=[CH]%12CC[CH]%13=[CH]%14CC1.[CH]1%21=[CH]%22CC[CH]%23=[CH]%24CC1.Cl%31%33.Cl%32%34",
    "di-μ-chlorido-bis{[(1,2,5,6-η)-(1Z,5Z)-cycloocta-1,5-diene]rhodium}"],
  ["PtCl2(cod)", "Cl[Pt]%11%12%13%14Cl.[CH]1%11=[CH]%12CC[CH]%13=[CH]%14CC1", "dichlorido[(1,2,5,6-η)-(1Z,5Z)-cycloocta-1,5-diene]platinum"],
  // Bonded through all its unsaturated atoms: η alone, after the name's stereodescriptors (Example 19: (E)-η2-but-2-enal).
  ["(η4-cyclohexa-1,3-diene)Fe(CO)3", "[Fe]%11%12%13%14(=C=O)(=C=O)=C=O.[CH]1%11=[CH]%12[CH]%13=[CH]%14CC1", "tricarbonyl(η4-cyclohexa-1,3-diene)iron"],
  ["K[PtCl3(but-2-ene)]", "[K+].[Pt-]%11%12(Cl)(Cl)Cl.C[CH]%11=[CH]%12C", "potassium [(2Z)-η2-but-2-ene]trichloridoplatinate(1-)"],
  ["(η3-allyl)PdCl(PPh3), the allyl drawn as an anion", "Cl[Pd+]%11%12%13P(c1ccccc1)(c1ccccc1)c1ccccc1.[CH2-]%11[CH]%12=[CH2]%13", "chlorido(η3-prop-2-en-1-ido)(triphenylphosphane)palladium"],
  // Not bonded through all of them (the C=O is not): locants, a run of more than two as a range (Example 14).
  ["(hexa-3,5-dienal)Fe(CO)3", "[Fe]%11%12%13%14(=C=O)(=C=O)=C=O.O=CC[CH]%11=[CH]%12[CH]%13=[CH2]%14", "tricarbonyl[(3–6-η)-(3E)-hexa-3,5-dienal]iron"],
];
for (const [label, smiles, want] of ETA) { assert.equal(nameOf(smiles), want, label); assert.equal(editorName(smiles), want, `${label}, Structure to Name`); }
const wrongEta: [number, string[]][] = [
  [0, ["potassium trichlorido(ethene)platinate(1-)", "potassium trichlorido(η1-ethene)platinate(1-)", "potassium trichlorido(η2-ethyne)platinate(1-)"]],
  [1, ["(η5-benzene)tricarbonylchromium", "(benzene)tricarbonylchromium", "(η6-cyclohexane)tricarbonylchromium"]],
  [3, ["tricarbonyl(η6-methylbenzene)chromium", "tricarbonyl(η7-methylbenzene)chromium", "tricarbonyl(methyl-η5-benzene)chromium"]],
  [5, ["bis(η4-cycloocta-1,5-diene)nickel", "bis[(1Z,5Z)-η4-cycloocta-1,5-diene]nickel", "bis[(1,2,3,4-η)-(1Z,5Z)-cycloocta-1,5-diene]nickel",
    "bis[(1,2,5,6-η)-(1Z,5E)-cycloocta-1,5-diene]nickel", "bis[(1,2,5,6-η)-(1Z,5Z)-cycloocta-1,5-diene]palladium", "[(1,2,5,6-η)-(1Z,5Z)-cycloocta-1,5-diene]nickel"]],
  [6, ["di-μ-chlorido-bis{[(1,2,5,6-η)-(1Z,5Z)-cycloocta-1,5-diene]iridium}", "di-μ-chlorido-bis{[(1,2,6-η)-(1Z,5Z)-cycloocta-1,5-diene]rhodium}"]],
  [8, ["tricarbonyl[(1–4-η)-cyclohexa-1,3-diene]iron", "tricarbonyl(η6-cyclohexa-1,3-diene)iron", "tricarbonyl(η3-cyclohexa-1,3-diene)iron"]],
  [11, ["tricarbonyl[(3E)-η4-hexa-3,5-dienal]iron", "tricarbonyl[(3,4,5,6-η)-(3E)-hexa-3,5-dienal]iron", "tricarbonyl[(2–5-η)-(3E)-hexa-3,5-dienal]iron",
    "tricarbonyl[(3–6-η)-(3Z)-hexa-3,5-dienal]iron"]],
];
let turnedEta = 0;
for (const [k, names] of wrongEta) for (const name of names) { assert.equal(complexNameReads(name, drawn(ETA[k][1]), api), false, name); turnedEta++; }
console.log(`namer-complex.check: ${ETA.length} complexes of η ligands named, ${turnedEta} names one term away turned down`);

// No name for these: an η ligand drawn with too few hydrogens (each C has one: not ethene), two complexes in one
// drawing, a complex with a solvent molecule.
const none: [string, string][] = [
  ["η2 ethene", "C1=C[Pt]1(Cl)(Cl)Cl"],
  ["[Pt(NH3)4][PtCl4]", "[NH3][Pt+2]([NH3])([NH3])[NH3].Cl[Pt-2](Cl)(Cl)Cl"],
  ["with solvent", "[NH3][Pt](Cl)(Cl)[NH3].CS(C)=O"],
];
for (const [label, smiles] of none) assert.equal(nameOf(smiles), undefined, label);
console.log(`namer-complex.check: ${none.length} structures with no name, as expected`);

// A metal labelled with its oxidation number, as Sam labels his Os: Os(II) is osmium with oxidation number II
// (labels.ts). The atom stays Os, with no charge, so the formula is what is drawn. A label the drawing contradicts
// (Pt(IV) on cisplatin, whose chlorides fix II) gives no name.
const phen = drawn(SAM.find((x) => x[0] === "Os(phen)3")![1], "Os(II)"), os = phen.atoms.find((a) => a.label === "Os")!;
assert.ok(!os.charge && os.ox === 2, "Os(II) is Os with no charge");
assert.equal(complexName(phen, api), "tris(1,10-phenanthroline-κ2N1,N10)osmium(II)", "Os(II) label");
assert.equal(complexNameReads("tris(1,10-phenanthroline-κ2N1,N10)osmium(III)", phen, api), false, "Os(II) label, III");
assert.equal(complexName(drawn("[NH3][Pt]([NH3])(Cl)Cl", "Pt(II)"), api), "cis-diamminedichloridoplatinum(II)", "Pt(II) label");
assert.equal(complexName(drawn("[NH3][Pt]([NH3])(Cl)Cl", "Pt(IV)"), api), undefined, "Pt(IV) label");
// The same with the number raised, as Text > Superscript sets it (issue 44): Os with II raised is Os(II).
{
  const m = labelled(SAM.find((x) => x[0] === "Os(phen)3")![1], "OsII"), k = m.atoms.findIndex((a) => a.text === "OsII");
  m.atoms[k] = { ...m.atoms[k], runs: [{ text: "Os" }, { text: "II", script: "super" }] };
  assert.equal(complexName(chem.expandLabels(m), api), "tris(1,10-phenanthroline-κ2N1,N10)osmium(II)", "Os with II raised");
}
console.log("namer-complex.check: metals labelled with an oxidation number named with it");

// Configuration at the metal (IR-9.3): the donor atoms placed by hand round the metal, in the order of the metal's
// bonds. A spot is a direction in the plane, with a wedge (1) or hash (6) from the metal. An octahedron is drawn as
// chemists draw one: two bonds up and down, the four others in perspective, the front pair wedged, the back pair hashed.
const UP: Spot = [0, 1], DOWN: Spot = [0, -1], LF: Spot = [-0.87, -0.3, 1], RF: Spot = [0.87, -0.3, 1], LB: Spot = [-0.87, 0.3, 6], RB: Spot = [0.87, 0.3, 6];
const N_: Spot = [0, 1], S_: Spot = [0, -1], W_: Spot = [-1, 0], E_: Spot = [1, 0];
type Spot = [number, number, (1 | 6)?];
function placed(smiles: string, spots: Spot[]): Mol {
  const m = labelled(smiles), x = m.atoms.findIndex((a) => METALS.test(`[${a.label}]`)), at = m.atoms[x].location;
  const bonds = m.bonds.map((b) => ({ ...b })), atoms = m.atoms.map((a) => ({ ...a }));
  // The metal's bonds by the atom they go to, in the SMILES's order of atoms.
  const other = (b: { atoms: number[] }) => (b.atoms[0] === x ? b.atoms[1] : b.atoms[0]);
  const mine = bonds.filter((b) => b.atoms.includes(x)).sort((p, q) => other(p) - other(q));
  assert.equal(mine.length, spots.length, `bonds of ${smiles}`);
  mine.forEach((b, k) => {
    const d = b.atoms[0] === x ? b.atoms[1] : b.atoms[0], [dx, dy, wedge] = spots[k];
    atoms[d] = { ...atoms[d], location: [at[0] + 1.2 * dx, at[1] + 1.2 * dy, 0] };
    b.atoms = [x, d];
    if (wedge) b.stereo = wedge; else delete b.stereo;
  });
  return chem.expandLabels({ ...m, atoms, bonds });
}
const NH3 = "[NH3]", EN = "[NH2]CC[NH2]";
// A direction at an angle (degrees, anticlockwise from the right), on a wedge (1) or hash (6).
const hex = (deg: number, wedge?: 1 | 6): Spot => [Math.cos((deg * Math.PI) / 180), Math.sin((deg * Math.PI) / 180), ...(wedge ? [wedge] : [])] as Spot;
const EN3 = "[Co+3]%11%12%13%14%15%16.[NH2]%11CC[NH2]%12.[NH2]%13CC[NH2]%14.[NH2]%15CC[NH2]%16";
const BPY3 = "[Ru+2]%11%12%13%14%15%16.C1=CC=[N]%11C(=C1)C1=[N]%12C=CC=C1.C1=CC=[N]%13C(=C1)C1=[N]%14C=CC=C1.C1=CC=[N]%15C(=C1)C1=[N]%16C=CC=C1";
const PH3P = "P(c1ccccc1)(c1ccccc1)c1ccccc1", TBP = "P(c1ccccc1)(C(C)(C)C)C(C)(C)C";
const ZN4 = `[Zn](Br)(Cl)(${PH3P})N1=CC=CC=C1`, FE5 = `[Fe](${PH3P})(${PH3P})(=C=O)(=C=O)=C=O`, PD5 = `Br[Pd](Br)(${TBP})(${TBP})${TBP}`;
const configs: [string, Mol, string][] = [
  // Square planar [Ma2b2], [Ma2bc] (SP-4).
  ["cisplatin by hand", placed(`[Pt](${NH3})(${NH3})(Cl)Cl`, [N_, E_, S_, W_]), "cis-diamminedichloridoplatinum(II)"],
  ["transplatin by hand", placed(`[Pt](${NH3})(Cl)(${NH3})Cl`, [N_, E_, S_, W_]), "trans-diamminedichloridoplatinum(II)"],
  // Octahedral [Ma2b4] (cis, trans, also with chelates), [Ma3b3] (fac, mer).
  ["cis-[CoCl2(NH3)4]+", placed(`[Co+](Cl)(Cl)(${NH3})(${NH3})(${NH3})${NH3}`, [UP, LF, DOWN, RF, LB, RB]), "cis-tetraamminedichloridocobalt(1+)"],
  ["trans-[CoCl2(NH3)4]+", placed(`[Co+](Cl)(Cl)(${NH3})(${NH3})(${NH3})${NH3}`, [UP, DOWN, LF, RF, LB, RB]), "trans-tetraamminedichloridocobalt(1+)"],
  ["cis-[CoCl2(en)2]+", placed("[Co+]1%10%11(Cl)(Cl)[NH2]CC[NH2]1.[NH2]%10CC[NH2]%11", [LB, RB, UP, LF, DOWN, RF]), "cis-dichloridobis(ethane-1,2-diamine-κ2N,N')cobalt(1+)"],
  ["trans-[CoCl2(en)2]+", placed("[Co+]1%10%11(Cl)(Cl)[NH2]CC[NH2]1.[NH2]%10CC[NH2]%11", [UP, DOWN, LF, LB, RF, RB]), "trans-dichloridobis(ethane-1,2-diamine-κ2N,N')cobalt(1+)"],
  ["mer-[CoCl3(NH3)3]", placed(`[Co](Cl)(Cl)(Cl)(${NH3})(${NH3})${NH3}`, [UP, DOWN, LF, RB, RF, LB]), "mer-triamminetrichloridocobalt(III)"],
  ["fac-[CoCl3(NH3)3]", placed(`[Co](Cl)(Cl)(Cl)(${NH3})(${NH3})${NH3}`, [UP, LF, RF, DOWN, RB, LB]), "fac-triamminetrichloridocobalt(III)"],
  // The configuration index (IR-9.3.3.4, Example 4 with PPh3 for AsPh3): P is priority 1, the nitrosyl N 2 (O beyond
  // it), the acetonitrile N 3, C 4. CO is trans to P; in the plane NO is trans to MeCN.
  ["[Cr(CO)2(MeCN)2(NO)(PPh3)]+", placed("[Cr+](P(c1ccccc1)(c1ccccc1)c1ccccc1)(=C=O)(=C=O)(N=O)(N#CC)N#CC", [UP, DOWN, RB, RF, LF, LB]),
    "(OC-6-43)-bis(acetonitrile)dicarbonylnitrosyl(triphenylphosphane)chromium(1+)"],
  // Δ and Λ (the skew-lines convention, IR-9.3.4.11): the octahedron seen down its threefold axis, as the Red Book draws
  // its delta and lambda examples, the near triangle on wedges and the far one on hashes. In Δ each chelate runs from a
  // near donor to the far donor 60° clockwise of it; in Λ, anticlockwise. Turned in the plane, the same; mirrored, the
  // other.
  ["Δ-[Co(en)3]3+", placed(EN3, [hex(90, 1), hex(30, 6), hex(210, 1), hex(150, 6), hex(330, 1), hex(270, 6)]), "Δ-tris(ethane-1,2-diamine-κ2N,N')cobalt(3+)"],
  ["Λ-[Co(en)3]3+", placed(EN3, [hex(90, 1), hex(150, 6), hex(210, 1), hex(270, 6), hex(330, 1), hex(30, 6)]), "Λ-tris(ethane-1,2-diamine-κ2N,N')cobalt(3+)"],
  ["Δ-[Co(en)3]3+, turned", placed(EN3, [hex(130, 1), hex(70, 6), hex(250, 1), hex(190, 6), hex(10, 1), hex(310, 6)]), "Δ-tris(ethane-1,2-diamine-κ2N,N')cobalt(3+)"],
  ["Δ-[Co(en)3]3+, mirrored", placed(EN3, [hex(90, 1), hex(150, 6), hex(330, 1), hex(30, 6), hex(210, 1), hex(270, 6)].map(([x, y, w]) => [-x, y, w] as Spot)), "Δ-tris(ethane-1,2-diamine-κ2N,N')cobalt(3+)"],
  ["Λ-[Ru(bpy)3]2+", placed(BPY3, [hex(90, 1), hex(150, 6), hex(210, 1), hex(270, 6), hex(330, 1), hex(30, 6)]), "Λ-tris(2,2'-bipyridine-κ2N1,N1')ruthenium(2+)"],
  ["Δ-[Ru(bpy)2(phen)]2+", placed("[Ru+2]%11%12%13%14%15%16.C1=CC=[N]%11C(=C1)C1=[N]%12C=CC=C1.C1=CC=[N]%13C(=C1)C1=[N]%14C=CC=C1.C1=CC2=CC=C3C=CC=[N]%16C3=C2[N]%15=C1",
    [hex(90, 1), hex(30, 6), hex(210, 1), hex(150, 6), hex(270, 6), hex(330, 1)]), "Δ-bis(2,2'-bipyridine-κ2N1,N1')(1,10-phenanthroline-κ2N1,N10)ruthenium(2+)"],
  // R or S at a tetrahedral metal with four unlike donors (IR-9.3.4.2): Br > Cl > P > N. Br and Cl in the plane, P on
  // a hash and the pyridine N on a wedge: Br → Cl → P turns anticlockwise as drawn, with N towards the viewer: R.
  ["(T-4-R)-[ZnBrCl(py)(PPh3)]", placed(ZN4, [hex(210), hex(330), hex(60, 6), hex(120, 1)]), "(T-4-R)-bromidochlorido(pyridine)(triphenylphosphane)zinc(II)"],
  ["(T-4-S)-[ZnBrCl(py)(PPh3)]", placed(ZN4, [hex(210), hex(330), hex(60, 1), hex(120, 6)]), "(T-4-S)-bromidochlorido(pyridine)(triphenylphosphane)zinc(II)"],
  // A trigonal bipyramid (IR-9.3.3.6): the priority numbers of the axial donors, lower first. P is 1, C 2 (the Red
  // Book's Example 1 has both PPh3 axial).
  ["Fe(CO)3(PPh3)2, both P axial", placed(FE5, [UP, DOWN, W_, RF, RB]), "(TBPY-5-11)-tricarbonylbis(triphenylphosphane)iron"],
  ["Fe(CO)3(PPh3)2, one P axial", placed(FE5, [UP, W_, DOWN, RF, RB]), "(TBPY-5-12)-tricarbonylbis(triphenylphosphane)iron"],
  ["Fe(CO)3(PPh3)2, both P equatorial", placed(FE5, [W_, RF, UP, DOWN, RB]), "(TBPY-5-22)-tricarbonylbis(triphenylphosphane)iron"],
  // A square pyramid (IR-9.3.3.5): the apex's priority number, then the one trans to the most preferred basal donor.
  // The Red Book's Example 2: Br (1) at the apex, the other Br trans to P (2).
  ["[PdBr2(PPhtBu2)3]", placed(PD5, [UP, LF, RB, RF, LB]), "(SPY-5-12)-dibromidotris[di-tert-butyl(phenyl)phosphane]palladium(II)"],
  ["[PdBr2(PPhtBu2)3], P at the apex", placed(PD5, [LF, RB, UP, RF, LB]), "(SPY-5-21)-dibromidotris[di-tert-butyl(phenyl)phosphane]palladium(II)"],
];
for (const [label, m, want] of configs) {
  assert.equal(complexName(m, api), want, label);
  // Each other descriptor, and none, is turned down.
  const bare = want.replace(/^(?:cis-|trans-|fac-|mer-|Δ-|Λ-|\([A-Z]+-\d-(?:\d+|[RS])\)-)/, "");
  for (const other of ["", "cis-", "trans-", "fac-", "mer-", "Δ-", "Λ-", "(SP-4-1)-", "(SP-4-2)-", "(OC-6-12)-", "(OC-6-34)-", "(T-4-R)-", "(T-4-S)-", "(TBPY-5-11)-", "(TBPY-5-12)-", "(SPY-5-12)-", "(SPY-5-21)-"].map((d) => d + bare).filter((n) => n !== want)) assert.equal(complexNameReads(other, m, api), false, other);
}
// No configuration where the drawing fixes none: a square with a wedge in it, a metal that is not square planar with
// four, an octahedron drawn flat, and a chelate that fixes cis by itself.
const flatCo = placed(`[Co+](Cl)(Cl)(${NH3})(${NH3})(${NH3})${NH3}`, [[0, 1], [0, -1], [0.87, 0.5], [-0.87, 0.5], [0.87, -0.5], [-0.87, -0.5]]);
assert.equal(complexName(flatCo, api), "tetraamminedichloridocobalt(1+)", "flat octahedron");
assert.equal(complexName(placed(`[Pt](${NH3})(${NH3})(Cl)Cl`, [N_, [1, 0, 1], S_, W_]), api), "diamminedichloridoplatinum(II)", "wedge in a square");
assert.equal(complexName(placed(`[Zn](${NH3})(${NH3})(Cl)Cl`, [N_, E_, S_, W_]), api), "diamminedichloridozinc(II)", "zinc");
assert.equal(complexName(placed("[Pt]1(Cl)(Cl)[NH2]CC[NH2]1", [N_, E_, S_, W_]), api), "dichlorido(ethane-1,2-diamine-κ2N,N')platinum(II)", "chelate");
// No Δ or Λ for chelates whose two donor atoms are unlike (glycinate: fac and mer isomers too, not given), nor for a
// tris(bidentate) complex drawn flat.
const gly = complexName(placed("[Co]%11%12%13%14%15%16.[NH2]%11CC(=O)O%12.[NH2]%13CC(=O)O%14.[NH2]%15CC(=O)O%16", [hex(90, 1), hex(30, 6), hex(210, 1), hex(150, 6), hex(330, 1), hex(270, 6)]), api);
assert.ok(gly && !/^[ΔΛ(]/.test(gly), `glycinate: ${gly}`);
assert.equal(complexName(placed(EN3, [0, 60, 120, 180, 240, 300].map((d) => hex(d))), api), "tris(ethane-1,2-diamine-κ2N,N')cobalt(3+)", "flat tris(en)");
// No polyhedron where five donors are drawn as neither a bipyramid nor a pyramid, nor four as a flattened tetrahedron.
assert.equal(complexName(placed(FE5, [UP, DOWN, W_, E_, RB]), api), "tricarbonylbis(triphenylphosphane)iron", "five, no polyhedron");
assert.equal(complexName(placed(ZN4, [hex(180), hex(0), hex(90, 6), hex(270, 1)]), api), "bromidochlorido(pyridine)(triphenylphosphane)zinc(II)", "four in a cross with wedges");
console.log(`namer-complex.check: ${configs.length} configurations at the metal named as drawn, the others turned down`);

// Porphyrins, and main-group central atoms in chelates (IR-7.1, IR-9). The ligand as the Red Book names it (IR-9 Table
// VII: tpp, 5,10,15,20-tetraphenylporphyrin-21,23-diido), its four N atoms cited by OPSIN's locants. Each name must
// also be the one Structure to Name gives, so the namer has no name of its own for these structures. The porphyrins
// are drawn as Sam draws them: the two imine N atoms with four bonds and no charge.
const porphyrin = (r: string) => `C12=CC=C(N1%11)C(${r})=C1C=CC(=N1%12)C(${r})=C1C=CC(N1%13)=C(${r})C=1C=CC(N1%14)=C2${r}`;
const TPP = porphyrin("c3ccccc3"), TPP_ = "5,10,15,20-tetraphenylporphyrin-21,23-diido-κ4N21,N22,N23,N24";
const OEP = "C12=C(CC)C(CC)=C(N1%11)C=C1C(CC)=C(CC)C(=N1%12)C=C1C(CC)=C(CC)C(N1%13)=CC=1C(CC)=C(CC)C(N1%14)=C2";
const STYRYL = "C12=CC=C(N1%11)C(/C=C/c3ccccc3)=C1C=CC(=N1%12)C=C1C=CC(N1%13)=CC=1C=CC(N1%14)=C2";
const PC = "C12=C3C=CC=CC3=C(N1%11)N=C1C3=CC=CC=C3C(=N1%12)N=C1C3=CC=CC=C3C(N1%13)=NC=1C3=CC=CC=C3C(N1%14)=N2";
const PC_ = "phthalocyanine-29,31-diido-κ4N29,N30,N31,N32", COR_ = "corrole-21,22,23-triido-κ4N21,N22,N23,N24";
const corrole = (r: string) => `C%21%22=CC=C(N%22%11)C(${r})=C%23C=CC(N%23%12)=C(${r})C%24=CC=C(N%24%13)C(${r})=C%25C=CC%21=N%25%14`;
const PH = "c9ccccc9", F5 = "c9c(F)c(F)c(F)c(F)c9F";
const MACRO: [string, string, string][] = [
  // Sam's two P(V) porphyrins (his ChemDraw drawings, as SMILES written here). A complex ion: its charge number.
  ["[P(TPP)(OMe)2]+", `CO[P+]%11%12%13%14OC.${TPP}`, `dimethanolato(${TPP_})phosphorus(1+)`],
  ["[P(TMeOPP)(OMe)2]+", `CO[P+]%11%12%13%14OC.${porphyrin("c3ccc(OC)cc3")}`,
    "dimethanolato[5,10,15,20-tetrakis(4-methoxyphenyl)porphyrin-21,23-diido-κ4N21,N22,N23,N24]phosphorus(1+)"],
  ["[P(TPP)(OMe)2]+, drawn P- and N+", `CO[P-]%11%12%13%14OC.${TPP.replace("=N1%12", "=[N+]1%12").replace("C(N1%14)", "C([N+]1%14)")}`, `dimethanolato(${TPP_})phosphorus(1+)`],
  ["[P(TPP)(OH)2]+", `O[P+]%11%12%13%14O.${TPP}`, `dihydroxido(${TPP_})phosphorus(1+)`],
  ["[Sn(TPP)Cl2]", `Cl[Sn]%11%12%13%14Cl.${TPP}`, `dichlorido(${TPP_})tin(IV)`],
  ["[Zn(TPP)]", `[Zn]%11%12%13%14.${TPP}`, `(${TPP_})zinc(II)`],
  ["[Fe(TPP)Cl]", `Cl[Fe]%11%12%13%14.${TPP}`, `chlorido(${TPP_})iron(III)`],
  ["[Co(TPP)]", `[Co]%11%12%13%14.${TPP}`, `(${TPP_})cobalt(II)`],
  ["[Mg(OEP)]", `[Mg]%11%12%13%14.${OEP}`, "(2,3,7,8,12,13,17,18-octaethylporphyrin-21,23-diido-κ4N21,N22,N23,N24)magnesium(II)"],
  // The chelate fixes the porphyrin's E and Z, so its name cites none; the styryl group's (E) still counts.
  ["Zn styrylporphyrin", `[Zn]%11%12%13%14.${STYRYL}`, "{5-[(1E)-2-phenylethenyl]porphyrin-21,23-diido-κ4N21,N22,N23,N24}zinc(II)"],
  // Phthalocyanines (the Red Book's pc, phthalocyanine-29,31-diido) and corroles (corrole-21,22,23-triido), with the
  // locants of the IUPAC tetrapyrrole figures (TP-1.6 Fig. 4, TP-5.3 Fig. 11) that Octet adds to OPSIN.
  ["Si(Pc)(OH)2", `O[Si]%11%12%13%14O.${PC}`, `dihydroxido(${PC_})silicon(IV)`],
  ["[Al(Pc)Cl]", `Cl[Al]%11%12%13%14.${PC}`, `chlorido(${PC_})aluminium(III)`],
  ["[Ge(Pc)Cl2]", `Cl[Ge]%11%12%13%14Cl.${PC}`, `dichlorido(${PC_})germanium(IV)`],
  ["[Zn(Pc)]", `[Zn]%11%12%13%14.${PC}`, `(${PC_})zinc(II)`],
  ["[Cu(Pc)]", `[Cu]%11%12%13%14.${PC}`, `(${PC_})copper(II)`],
  ["[Ga(tpfc)]", `[Ga]%11%12%13%14.${corrole(F5)}`, `[5,10,15-tris(pentafluorophenyl)${COR_}]gallium(III)`],
  ["[Ga(tpfc)(py)]", `[Ga]%11%12%13%14%15.${corrole(F5)}.C1=CC=N%15C=C1`, `(pyridine)[5,10,15-tris(pentafluorophenyl)${COR_}]gallium(III)`],
  ["[Mn(tpc)]", `[Mn]%11%12%13%14.${corrole(PH)}`, `(5,10,15-triphenyl${COR_})manganese(III)`],
  ["[Co(tpc)(PPh3)]", `[Co]%11%12%13%14%15.${corrole(PH)}.P%15(c1ccccc1)(c1ccccc1)c1ccccc1`, `(5,10,15-triphenyl${COR_})(triphenylphosphane)cobalt(III)`],
  ["[Fe(tpc)Cl]", `Cl[Fe]%11%12%13%14.${corrole(PH)}`, `chlorido(5,10,15-triphenyl${COR_})iron(IV)`],
  ["[Cu(tpc)]", `[Cu]%11%12%13%14.${corrole(PH)}`, `(5,10,15-triphenyl${COR_})copper(III)`],
  // Other main-group chelates: a BODIPY dye (drawn either way), Al(acac)3 and a spiro borate.
  ["BODIPY", "F[B-]1(F)N2C=CC=C2C=C2C=CC=[N+]12", "difluorido{2-[(2H-pyrrol-2-ylidene)methyl]-1H-pyrrol-1-ido-κ2N,N'}boron(III)"],
  ["BODIPY, drawn with no charges", "FB1(F)N2C=CC=C2C=C2C=CC=N12", "difluorido{2-[(2H-pyrrol-2-ylidene)methyl]-1H-pyrrol-1-ido-κ2N,N'}boron(III)"],
  ["Al(acac)3", "CC1=CC(C)=O[Al]23(O1)(OC(C)=CC(C)=O2)OC(C)=CC(C)=O3", "tris(4-oxopent-2-en-2-olato-κ2O,O')aluminium(III)"],
  ["[B(cat)2]-", "[B-]12(Oc3ccccc3O1)Oc1ccccc1O2", "bis(benzene-1,2-diolato-κ2O,O')borate(1-)"],
];
for (const [label, smiles, want] of MACRO) {
  assert.equal(nameOf(smiles), want, label);
  assert.equal(editorName(smiles), want, `${label}, Structure to Name`);
  assert.ok(complexNameReads(want, drawn(smiles), api), want);
}
// With a bond to carbon a main-group atom is not a central atom: the namer names these.
assert.equal(editorName("CC1(C)OB(c2ccccc2)OC1(C)C"), "4,4,5,5-tetramethyl-2-phenyl-1,3,2-dioxaborolane");
assert.equal(nameOf("CC1(C)OB(c2ccccc2)OC1(C)C"), undefined);
assert.equal(nameOf("CC(C)(C)[Si](C)(C)OC1=CC=CC=C1"), undefined);
// Names one term away from right.
const macro = (label: string) => MACRO.find((x) => x[0] === label)![1], P_OME = macro("[P(TPP)(OMe)2]+"), ZN = macro("[Zn(TPP)]");
const wrongMacro: [string, string[]][] = [
  [P_OME, [
    `dimethanolato(${TPP_})phosphorus(2+)`, `dimethanolato(${TPP_})phosphorus`, `trimethanolato(${TPP_})phosphorus(1+)`,
    `methanolato(${TPP_})phosphorus(1+)`, `diethanolato(${TPP_})phosphorus(1+)`, `dihydroxido(${TPP_})phosphorus(1+)`,
    `dimethanolato(${TPP_})arsenic(1+)`, `dimethanolato(${TPP_})phosphate(1+)`, `dimethanolato(${TPP_})diphosphorus(1+)`,
    "dimethanolato(5,10,15,20-tetraphenylporphyrin-21,23-diido-κ3N21,N22,N23)phosphorus(1+)",
    "dimethanolato(5,10,15,20-tetraphenylporphyrin-21,23-diido-κ4N21,N22,N23,N25)phosphorus(1+)",
    "dimethanolato(5,10,15,20-tetraphenylporphyrin-21,23-diido)phosphorus(1+)",
    "dimethanolato(5,10,15,20-tetraphenylporphyrin-κ4N21,N22,N23,N24)phosphorus(1+)",
    "dimethanolato(5,10,15-triphenylporphyrin-21,23-diido-κ4N21,N22,N23,N24)phosphorus(1+)",
    "dimethanolato(2,7,12,17-tetraphenylporphyrin-21,23-diido-κ4N21,N22,N23,N24)phosphorus(1+)",
    "dimethanolato[5,10,15,20-tetrakis(4-methoxyphenyl)porphyrin-21,23-diido-κ4N21,N22,N23,N24]phosphorus(1+)",
  ]],
  [ZN, [`(${TPP_})zinc(III)`, `(${TPP_})zinc(2+)`, `(${TPP_})copper(II)`, `bis(${TPP_})zinc(II)`, `chlorido(${TPP_})zinc(II)`]],
  [macro("[Sn(TPP)Cl2]"), [`dichlorido(${TPP_})tin(II)`, `trichlorido(${TPP_})tin(IV)`, `dibromido(${TPP_})tin(IV)`]],
  [`[Zn]%11%12%13%14.${STYRYL}`, [
    "{5-[(1Z)-2-phenylethenyl]porphyrin-21,23-diido-κ4N21,N22,N23,N24}zinc(II)", "[5-(2-phenylethenyl)porphyrin-21,23-diido-κ4N21,N22,N23,N24]zinc(II)",
  ]],
  [macro("BODIPY"), [
    "difluorido{2-[(2H-pyrrol-2-ylidene)methyl]-1H-pyrrol-1-ido-κ2N,N'}boron(II)", "dichlorido{2-[(2H-pyrrol-2-ylidene)methyl]-1H-pyrrol-1-ido-κ2N,N'}boron(III)",
    "difluorido{2-[(2H-pyrrol-2-ylidene)methyl]-1H-pyrrol-1-ido-κN}boron(III)", "difluorido{2-[(2H-pyrrol-2-ylidene)methyl]-1H-pyrrol-1-ido-κ2N,N'}aluminium(III)",
  ]],
  // The κ term cites the four interior N atoms by the figures' locants: the meso N atoms (6, 13, 20, 27), an N atom with
  // no such locant, or three of four are refused, as are a neutral ligand, a dianion of corrole and the wrong ring.
  [macro("Si(Pc)(OH)2"), [
    `dihydroxido(${PC_})silicon(III)`, `dihydroxido(${PC_})germanium(IV)`, `hydroxido(${PC_})silicon(IV)`, `dichlorido(${PC_})silicon(IV)`,
    "dihydroxido(phthalocyanine-29,31-diido-κ4N6,N13,N20,N27)silicon(IV)", "dihydroxido(phthalocyanine-29,31-diido-κ4N29,N30,N31,N33)silicon(IV)",
    "dihydroxido(phthalocyanine-29,31-diido-κ3N29,N30,N31)silicon(IV)", "dihydroxido(phthalocyanine-κ4N29,N30,N31,N32)silicon(IV)",
    "dihydroxido(phthalocyanine-29,31-diido)silicon(IV)", "dihydroxido(porphyrin-21,23-diido-κ4N21,N22,N23,N24)silicon(IV)",
    "dihydroxido(2-methylphthalocyanine-29,31-diido-κ4N29,N30,N31,N32)silicon(IV)",
  ]],
  [macro("[Ga(tpfc)]"), [
    `[5,10,15-tris(pentafluorophenyl)${COR_}]gallium(II)`, `[5,10,15-tris(pentafluorophenyl)${COR_}]aluminium(III)`, `(5,10,15-triphenyl${COR_})gallium(III)`,
    `[2,10,15-tris(pentafluorophenyl)${COR_}]gallium(III)`, `[5,10,20-tris(pentafluorophenyl)${COR_}]gallium(III)`,
    "[5,10,15-tris(pentafluorophenyl)corrole-21,22-diido-κ4N21,N22,N23,N24]gallium(III)",
    "[5,10,15-tris(pentafluorophenyl)corrole-21,22,23-triido-κ4N21,N22,N23,N25]gallium(III)",
    "[5,10,15-tris(pentafluorophenyl)corrole-21,22,23-triido-κ3N21,N22,N23]gallium(III)",
    "[5,10,15,20-tetrakis(pentafluorophenyl)porphyrin-21,23-diido-κ4N21,N22,N23,N24]gallium(III)",
  ]],
  [macro("[Mn(tpc)]"), [`(5,10,15-triphenyl${COR_})manganese(II)`, `(5,10,15-triphenyl${COR_})manganese(IV)`, `chlorido(5,10,15-triphenyl${COR_})manganese(III)`]],
];
let turnedMacro = 0;
for (const [smiles, names] of wrongMacro) {
  const m = drawn(smiles);
  for (const name of names) { assert.equal(complexNameReads(name, m, api), false, name); turnedMacro++; }
}
// No name: ligands that neither IUPAC's recommendations nor OPSIN name (subphthalocyanine, naphthalocyanine), an
// N-confused porphyrin (C21 bonded to the metal: a carbon donor with N donors is not named); charges that give the
// central atom an oxidation number its group does not allow (P(VI), P(IV)) or leave an N atom with no usual valence;
// and a porphyrin with a ring bond missing, which is not a porphyrin.
const NC = PC.replace("C3C=CC=CC3", "C3C=C4C=CC=CC4=CC3").replaceAll("C3=CC=CC=C3", "C3=CC4=CC=CC=C4C=C3");
const noMacro: [string, string][] = [
  ["subphthalocyanine BCl", "Cl[B]%11%12%13.N%41=C1c2ccccc2C(N1%11)=NC1=C2C=CC=CC2=C(N1%12)N=C1c2ccccc2C%41=N1%13"],
  ["[Zn(Nc)]", `[Zn]%11%12%13%14.${NC}`],
  ["[Ni(NCTPP)]", `[Ni]%11%12%13%14.C12NC=C(C=1%11)C(${PH})=C1C=CC(=N1%12)C(${PH})=C1C=CC(N1%13)=C(${PH})C=1C=CC(N1%14)=C2${PH}`],
  ["[P(TPP)(OMe)2]2+", `CO[P+2]%11%12%13%14OC.${TPP}`],
  ["P(TPP)(OMe)2, no charge", `CO[P]%11%12%13%14OC.${TPP}`],
  ["N- with four bonds", `CO[P+]%11%12%13%14OC.${TPP.replace("=N1%12", "=[N-]1%12")}`],
  ["ring bond missing", `CO[P+]%11%12%13%14OC.${TPP.replace("C12=", "C1=").replace(/=C2c3ccccc3$/, "=Cc3ccccc3")}`],
];
for (const [label, smiles] of noMacro) assert.equal(editorName(smiles), undefined, label);
// The E and Z of an ordinary large ring still count: (Z)- and (E)-cyclooctene, and a 13-membered lactone, drawn with
// their double bond cis or trans (Indigo lays out every large ring cis, so these are drawn here).
function ringOf(labels: string[], trans: boolean, oxo?: number): Mol {
  const n = labels.length, c = [0.7, 0.8], p: number[][] = [[0, 0], [1.4, 0], [2.1, trans ? -1.2 : 1.2]];
  p[n - 1] = [-0.7, 1.2];
  const [a, r] = [Math.atan2(p[2][1] - c[1], p[2][0] - c[0]), Math.hypot(p[2][0] - c[0], p[2][1] - c[1])];
  const [b, s] = [Math.atan2(p[n - 1][1] - c[1], p[n - 1][0] - c[0]), Math.hypot(p[n - 1][0] - c[0], p[n - 1][1] - c[1])];
  const sweep = (b - a + 4 * Math.PI) % (2 * Math.PI);
  for (let k = 3; k < n - 1; k++) { const t = (k - 2) / (n - 3); p[k] = [c[0] + (r + (s - r) * t) * Math.cos(a + sweep * t), c[1] + (r + (s - r) * t) * Math.sin(a + sweep * t)]; }
  const atoms: Mol["atoms"] = labels.map((label, i) => ({ label, location: [p[i][0], p[i][1], 0] }));
  const bonds: Mol["bonds"] = labels.map((_, i) => ({ type: i ? 1 : 2, atoms: [i, (i + 1) % n] as [number, number] }));
  if (oxo !== undefined) { atoms.push({ label: "O", location: [2 * p[oxo][0] - c[0], 2 * p[oxo][1] - c[1], 0] }); bonds.push({ type: 2, atoms: [oxo, n] }); }
  return { atoms, bonds };
}
for (const [label, labels, oxo] of [["cyclooctene", [..."CCCCCCCC"], undefined], ["1-oxacyclotridec-4-en-2-one", [..."CCCCCCCCCCOCC"], 11]] as const) {
  const [z, e] = [false, true].map((trans) => ringOf([...labels], trans, oxo));
  assert.notEqual(inchiOf(z), inchiOf(e), label);
  const [nz, ne] = [z, e].map((m) => checkedName(m, m, nameToSmiles, inchiOf, chem.cipOf));
  assert.ok(nz?.includes("Z") && nz !== ne, `${label}: ${nz}, ${ne}`);
  assert.equal(complexName(z, api), undefined, label);
}
console.log(`namer-complex.check: ${MACRO.length} porphyrins and main-group chelates named, ${turnedMacro} names one term away turned down, ${noMacro.length} with no name`);

// Speed: a complex of about 100 atoms, named with every check in under 50 ms once OPSIN and Indigo are warm (Ru
// with three 4,4'-dialkyl-2,2'-bipyridines; each new to the namer, so nothing is kept from an earlier name).
const bpy = (a: number, b: number, r: string) => `C1(${r})=CC=[N]%${a}C(=C1)C1=[N]%${b}C=CC(${r})=C1`;
const ru = (n: number) => `[Ru+2]%10%11%12%13%14%15.${bpy(10, 11, "C".repeat(n))}.${bpy(12, 13, "C".repeat(n))}.${bpy(14, 15, "C".repeat(n))}`;
nameOf(ru(4));
const times = [9, 10, 11].map((n) => {
  const m = drawn(ru(n)), t = performance.now(), name = complexName(m, api), dt = performance.now() - t;
  assert.ok(name?.startsWith(`tris(4,4'-di`), name);
  return { atoms: m.atoms.filter((a) => a.label !== "H").length, dt };
});
const best = Math.min(...times.map((x) => x.dt));
assert.ok(best < 50, `a complex of ${times[2].atoms} atoms took ${best.toFixed(1)} ms`);
console.log(`namer-complex.check: a complex of ${times[2].atoms} atoms named in ${best.toFixed(1)} ms`);

// η ligands drawn through a multi-centre point (Structure > Add Multi-Centre Attachment, the j keys, or a bond from a
// metal to the middle of a ring, issue 26) read as a bond to each ring atom, so they take the same names.
{
  const { addGroupAt, bondTo, dragBond } = await import("./edit.ts");
  const carbonyls = (m: Mol) => [30, 90, 150].reduce((x, t) => {
    const d: [number, number] = [Math.cos((t * Math.PI) / 180), Math.sin((t * Math.PI) / 180)];
    x = bondTo(bondTo(x, 0, d, { type: 2 }), x.atoms.length, [2 * d[0], 2 * d[1]], { type: 2 });
    return { ...x, atoms: x.atoms.map((a, i) => (i === x.atoms.length - 1 ? { ...a, label: "O" } : a)) };
  }, m);
  const chromium: Mol = { atoms: [{ label: "Cr", location: [0, 0, 0] }], bonds: [] };
  // The Ring tool's benzene below the metal, and a bond from Cr to its middle.
  const ring: Mol = { atoms: [...chromium.atoms, ...[0, 1, 2, 3, 4, 5].map((k): Mol["atoms"][number] => ({ label: "C", location: [Math.cos((k * Math.PI) / 3), -2 + Math.sin((k * Math.PI) / 3), 0] }))],
    bonds: [0, 1, 2, 3, 4, 5].map((k) => ({ type: k % 2 ? 1 : 2, atoms: [1 + k, 1 + ((k + 1) % 6)] as [number, number] })) };
  const drawnByBond = carbonyls(dragBond(ring, 0, [0, -2]));
  assert.ok(drawnByBond.atoms.some((a) => a.centre), "the bond made a multi-centre point");
  assert.equal(complexName(chem.expandLabels(drawnByBond), api), "(η6-benzene)tricarbonylchromium");
  // Shift+J's delocalised ring, drawn in perspective with wedges.
  assert.equal(complexName(chem.expandLabels(carbonyls(addGroupAt(chromium, 0, "phenylLigand")[0])), api), "(η6-benzene)tricarbonylchromium");
}
console.log("namer-complex.check: η ligands through a multi-centre point named");
