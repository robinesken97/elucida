// Run: node src/hardmolecules.check.ts. A benchmark of difficult structures for Name to Structure (and a pasted SMILES,
// PubChem's answer, a nickname: all go through parseStructure). Each structure is drawn as Name to Structure draws it
// and measured: Octet's own warnings (check.ts) by type, with Show Stereochemistry off and on; whether it reads as the
// same stereoisomer as its SMILES (standard InChI); abs flags; the longest and shortest bond; atoms on atoms, labels on
// bonds and labels on labels; crossing bonds; labels whose ink, as drawn, a bond crosses or another label's touches; and
// the time it takes. It prints a table and the failures by cause.
// The target (no warning that is not true chemistry, the same InChI, no abs, no atom on an atom, no label on a bond or a
// label, no bond through a label's ink and no two labels' ink touching, under BOUND ms) is asserted in full with
// BENCH_STRICT=1. npm test asserts it too, but for the time (which depends on the machine).
// Each named structure's SMILES is PubChem's (4 November 2026) and must give PubChem's InChIKey, so a wrong SMILES fails
// here; hexaprismane (not in PubChem) and the two annulenes (OPSIN's SMILES) are checked by their formula. The
// dictionary's structures are its own.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";

// chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const { parseStructure, ready, smilesWeight, stereoFacts, toInchi, toInchiAux } = await import("./chem.ts");
const { problems } = await import("./check.ts");
const { render } = await import("./render.ts");
const { arialInk } = await import("./cdxml.ts");
const { DRUGS } = await import("./drugs.ts");
type Mol = ReturnType<typeof parseStructure>;
// A second Indigo, for a SMILES's own InChIKey.
const indigo = await (await import(new URL("../node_modules/indigo-ketcher/indigo-ketcher-norender.js", import.meta.url).href)).default();
const keyOf = (smiles: string) => { const o = new indigo.MapStringString(); try { return indigo.convert(smiles, "inchi-key", o).trim() as string; } catch { return smiles; } finally { o.delete(); } };
await ready;

const STRICT = process.env.BENCH_STRICT === "1";
// Name to Structure draws a name once typing pauses, and keeps it. 400 ms is the longest a response can take and still
// feel immediate (Doherty, 1982); Indigo's layout alone of the largest structures here takes about a tenth of it.
const BOUND = 400;
// The dictionary's sample: its structures with three or more stereocentres or a bridged or caged ring system, at most
// this many (BENCH_SAMPLE), evenly spaced through the table.
const SAMPLE = Number(process.env.BENCH_SAMPLE ?? 300);

// Name, PubChem's isomeric SMILES, and PubChem's InChIKey (or the formula).
const HARD: [string, string, string][] = [
  ["aconitine", "CCN1C[C@@]2([C@@H](C[C@@H]([C@@]34[C@@H]2[C@H]([C@@H](C31)[C@@]5([C@@H]6[C@H]4C[C@@]([C@@H]6OC(=O)C7=CC=CC=C7)([C@H]([C@@H]5O)OC)O)OC(=O)C)OC)OC)O)COC", "XFSBVAOIAHNAPC-XTHSEXKGSA-N"],
  ["paclitaxel", "CC1=C2[C@H](C(=O)[C@@]3([C@H](C[C@@H]4[C@]([C@H]3[C@@H]([C@@](C2(C)C)(C[C@@H]1OC(=O)[C@@H]([C@H](C5=CC=CC=C5)NC(=O)C6=CC=CC=C6)O)O)OC(=O)C7=CC=CC=C7)(CO4)OC(=O)C)O)C)OC(=O)C", "RCINICONZNJXQF-MZXODVADSA-N"],
  ["docetaxel", "CC1=C2[C@H](C(=O)[C@@]3([C@H](C[C@@H]4[C@]([C@H]3[C@@H]([C@@](C2(C)C)(C[C@@H]1OC(=O)[C@@H]([C@H](C5=CC=CC=C5)NC(=O)OC(C)(C)C)O)O)OC(=O)C6=CC=CC=C6)(CO4)OC(=O)C)O)C)O", "ZDZOTLJHXYCWBA-VCVYQWHSSA-N"],
  ["strychnine", "C1CN2CC3=CCO[C@H]4CC(=O)N5[C@H]6[C@H]4[C@H]3C[C@H]2[C@@]61C7=CC=CC=C75", "QMGVPVSNSZLJIA-FVWCLLPLSA-N"],
  ["brucine", "COC1=C(C=C2C(=C1)[C@]34CCN5[C@H]3C[C@@H]6[C@@H]7[C@@H]4N2C(=O)C[C@@H]7OCC=C6C5)OC", "RRKTZKIUPZVBMF-IBTVXLQLSA-N"],
  ["vinblastine", "CC[C@@]1(C[C@H]2C[C@@](C3=C(CCN(C2)C1)C4=CC=CC=C4N3)(C5=C(C=C6C(=C5)[C@]78CCN9[C@H]7[C@@](C=CC9)([C@H]([C@@]([C@@H]8N6C)(C(=O)OC)O)OC(=O)C)CC)OC)C(=O)OC)O", "JXLYSJRDGCGARV-CFWMRBGOSA-N"],
  ["vincristine", "CC[C@@]1(C[C@@H]2C[C@@](C3=C(CCN(C2)C1)C4=CC=CC=C4N3)(C5=C(C=C6C(=C5)[C@]78CCN9[C@H]7[C@@](C=CC9)([C@H]([C@@]([C@@H]8N6C=O)(C(=O)OC)O)OC(=O)C)CC)OC)C(=O)OC)O", "OGWKCGZFUXNPDA-XQKSVPLYSA-N"],
  ["reserpine", "CO[C@H]1[C@@H](C[C@@H]2CN3CCC4=C([C@H]3C[C@@H]2[C@@H]1C(=O)OC)NC5=C4C=CC(=C5)OC)OC(=O)C6=CC(=C(C(=C6)OC)OC)OC", "QEVHRUUCFGRFIF-MDEJGZGSSA-N"],
  ["quinine", "COC1=CC2=C(C=CN=C2C=C1)[C@H]([C@@H]3C[C@@H]4CCN3C[C@@H]4C=C)O", "LOUPRKONTZGTKE-WZBLMQSHSA-N"],
  ["quinidine", "COC1=CC2=C(C=CN=C2C=C1)[C@@H]([C@H]3C[C@@H]4CCN3C[C@@H]4C=C)O", "LOUPRKONTZGTKE-LHHVKLHASA-N"],
  ["morphine", "CN1CC[C@]23[C@@H]4[C@H]1CC5=C2C(=C(C=C5)O)O[C@H]3[C@H](C=C4)O", "BQJCRHHNABKAKU-KBQPJGBKSA-N"],
  ["codeine", "CN1CC[C@]23[C@@H]4[C@H]1CC5=C2C(=C(C=C5)OC)O[C@H]3[C@H](C=C4)O", "OROGSEYTTFOCAN-DNJOTXNNSA-N"],
  ["thebaine", "CN1CC[C@]23[C@@H]4C(=CC=C2[C@H]1CC5=C3C(=C(C=C5)OC)O4)OC", "FQXXSQDCDRQNQE-VMDGZTHMSA-N"],
  ["tetrodotoxin", "C([C@@]1([C@H]2[C@@H]3[C@H](N=C(N[C@@]34[C@@H]([C@@H]1O[C@]([C@H]4O)(O2)O)O)N)O)O)O", "CFMYXEVWODSLAX-QOZOJKKESA-N"],
  ["saxitoxin", "C1CN2C(=N[C@H]([C@H]3[C@]2(C1(O)O)NC(=N3)N)COC(=O)N)N", "RPQXVSUAYFXFJA-HGRQIUPRSA-N"],
  ["ryanodine", "C[C@H]1CC[C@@]2([C@@]3(C[C@]4([C@@]5([C@]([C@H]([C@@]3([C@]5([C@]2([C@@H]1O)O4)O)O)OC(=O)C6=CC=CN6)(C(C)C)O)C)O)C)O", "JJSYXNQGLHBRRK-SFEDZAPPSA-N"],
  ["batrachotoxin", "CC1=CNC(=C1C(=O)O[C@@H](C)C2=CC[C@@]34[C@@]2(C[C@H]([C@@]56C3=CC[C@H]7[C@@]5(CC[C@](C7)(O6)O)C)O)CN(CCO4)C)C", "ISNYUQWBWALXEY-OMIQOYQYSA-N"],
  ["ginkgolide A", "C[C@@H]1C(=O)O[C@@H]2[C@]1([C@@]34C(=O)O[C@H]5[C@]3(C2)[C@@]6([C@@H](C5)C(C)(C)C)[C@H](C(=O)O[C@H]6O4)O)O", "FPUXKXIZEIDQKW-VKMVSBOZSA-N"],
  ["ginkgolide B", "C[C@@H]1C(=O)O[C@@H]2[C@]1([C@@]34C(=O)O[C@H]5[C@]3([C@@H]2O)[C@@]6([C@@H](C5)C(C)(C)C)[C@H](C(=O)O[C@H]6O4)O)O", "SQOJOAFXDQDRGF-ZMVGXLHTSA-N"],
  ["bilobalide", "CC(C)(C)[C@@]1(C[C@H]2[C@@]3([C@]14[C@H](C(=O)O[C@H]4OC3=O)O)CC(=O)O2)O", "MOLPUWBMSBJXER-YDGSQGCISA-N"],
  ["azadirachtin", "C/C=C(\\C)/C(=O)O[C@H]1C[C@H]([C@]2(CO[C@@H]3[C@@H]2[C@]14CO[C@@]([C@H]4[C@]([C@@H]3O)(C)[C@@]56[C@@H]7C[C@H]([C@@]5(O6)C)[C@]8(C=CO[C@H]8O7)O)(C(=O)OC)O)C(=O)OC)OC(=O)C", "FTNJWQUOZFUQQJ-NDAWSKJSSA-N"],
  ["artemisinin", "C[C@@H]1CC[C@H]2[C@H](C(=O)O[C@H]3[C@@]24[C@H]1CC[C@](O3)(OO4)C)C", "BLUAFEHZUWYNDE-NNWCWBAJSA-N"],
  ["bryostatin 1", "CCC/C=C/C=C/C(=O)O[C@H]1/C(=C/C(=O)OC)/C[C@H]2C[C@@H](OC(=O)C[C@@H](C[C@@H]3C[C@@H](C([C@@](O3)(C[C@@H]4C/C(=C/C(=O)OC)/C[C@@H](O4)/C=C/C([C@@]1(O2)O)(C)C)O)(C)C)OC(=O)C)O)[C@@H](C)O", "MJQUEDHRCUIRLF-TVIXENOKSA-N"],
  ["erythromycin", "CC[C@@H]1[C@@]([C@@H]([C@H](C(=O)[C@@H](C[C@@]([C@@H]([C@H]([C@@H]([C@H](C(=O)O1)C)O[C@H]2C[C@@]([C@H]([C@@H](O2)C)O)(C)OC)C)O[C@H]3[C@@H]([C@H](C[C@H](O3)C)N(C)C)O)(C)O)C)C)O)(C)O", "ULGZDMOVFRHVEP-RWJQBGPGSA-N"],
  ["sirolimus", "C[C@@H]1CC[C@H]2C[C@@H](/C(=C/C=C/C=C/[C@H](C[C@H](C(=O)[C@@H]([C@@H](/C(=C/[C@H](C(=O)C[C@H](OC(=O)[C@@H]3CCCCN3C(=O)C(=O)[C@@]1(O2)O)[C@H](C)C[C@@H]4CC[C@H]([C@@H](C4)OC)O)C)/C)O)OC)C)C)/C)OC", "QFJCIRLUMZQUOT-HPLJOQBZSA-N"],
  ["cyclosporin A", "CC[C@H]1C(=O)N(CC(=O)N([C@H](C(=O)N[C@H](C(=O)N([C@H](C(=O)N[C@H](C(=O)N[C@@H](C(=O)N([C@H](C(=O)N([C@H](C(=O)N([C@H](C(=O)N([C@H](C(=O)N1)[C@@H]([C@H](C)C/C=C/C)O)C)C(C)C)C)CC(C)C)C)CC(C)C)C)C)C)CC(C)C)C)C(C)C)CC(C)C)C)C", "PMATZTZNYRCHOR-CGLBZJNRSA-N"],
  ["vancomycin", "C[C@H]1[C@H]([C@@](C[C@@H](O1)O[C@@H]2[C@H]([C@@H]([C@H](O[C@H]2OC3=C4C=C5C=C3OC6=C(C=C(C=C6)[C@H]([C@H](C(=O)N[C@H](C(=O)N[C@H]5C(=O)N[C@@H]7C8=CC(=C(C=C8)O)C9=C(C=C(C=C9O)O)[C@H](NC(=O)[C@H]([C@@H](C1=CC(=C(O4)C=C1)Cl)O)NC7=O)C(=O)O)CC(=O)N)NC(=O)[C@@H](CC(C)C)NC)O)Cl)CO)O)O)(C)N)O", "MYPYJXKWCTUITO-LYRMYLQWSA-N"],
  ["amphotericin B", "C[C@H]1/C=C/C=C/C=C/C=C/C=C/C=C/C=C/[C@@H](C[C@H]2[C@@H]([C@H](C[C@](O2)(C[C@H](C[C@H]([C@@H](CC[C@H](C[C@H](CC(=O)O[C@H]([C@@H]([C@@H]1O)C)C)O)O)O)O)O)O)O)C(=O)O)O[C@H]3[C@H]([C@H]([C@@H]([C@H](O3)C)O)N)O", "APKFDSVGJQXUKY-INPOYWNPSA-N"],
  ["halichondrin B", "C[C@@H]1C[C@@H]2CC[C@H]3C(=C)C[C@@H](O3)CC[C@]45C[C@@H]6[C@H](O4)[C@H]7[C@@H](O6)[C@@H](O5)[C@@H]8[C@@H](O7)CC[C@@H](O8)CC(=O)O[C@@H]9[C@H]([C@H]3[C@H](C[C@@H]4[C@H](O3)C[C@@]3(O4)C[C@H]4[C@@H](O3)[C@H](C[C@]3(O4)C[C@@H]([C@H]4[C@@H](O3)C[C@H](O4)[C@H](C[C@H](CO)O)O)C)C)O[C@H]9C[C@H](C1=C)O2)C", "FXNFULJVOQMBCW-VZBLNRDYSA-N"],
  ["brevetoxin B", "C[C@@H]1C[C@H]2[C@@H](C[C@]3([C@H](O2)C[C@H]4[C@H](O3)C(=CC(=O)O4)C)C)O[C@@H]5[C@@H]1O[C@H]6C[C@@H]7[C@](C[C@@H]8[C@@](O7)(C/C=C\\[C@@H]9[C@@H](O8)C[C@@H]1[C@@H](O9)C[C@@H]2[C@@](O1)([C@H](C[C@H](O2)CC(=C)C=O)O)C)C)(O[C@@]6(CC5)C)C", "LYTCVQQGCSNFJU-FGRVLNGBSA-N"],
  ["ouabain", "C[C@H]1[C@@H]([C@H]([C@H]([C@@H](O1)O[C@H]2C[C@H]([C@@]3([C@@H]4[C@@H](CC[C@@]3(C2)O)[C@]5(CC[C@@H]([C@]5(C[C@H]4O)C)C6=CC(=O)OC6)O)CO)O)O)O)O", "LPMXVESGRSUGHW-HBYQJFLCSA-N"],
  ["digoxin", "C[C@@H]1[C@H]([C@H](C[C@@H](O1)O[C@@H]2[C@H](O[C@H](C[C@@H]2O)O[C@@H]3[C@H](O[C@H](C[C@@H]3O)O[C@H]4CC[C@]5([C@@H](C4)CC[C@@H]6[C@@H]5C[C@H]([C@]7([C@@]6(CC[C@@H]7C8=CC(=O)OC8)O)C)O)C)C)C)O)O", "LTMHDMANZUZIPE-PUGKRICDSA-N"],
  ["cholesterol", "C[C@H](CCCC(C)C)[C@H]1CC[C@@H]2[C@@]1(CC[C@H]3[C@H]2CC=C4[C@@]3(CC[C@@H](C4)O)C)C", "HVYWMOMLDIMFJA-DPAQBDIFSA-N"],
  ["hydrocortisone", "C[C@]12CCC(=O)C=C1CC[C@@H]3[C@@H]2[C@H](C[C@]4([C@H]3CC[C@@]4(C(=O)CO)O)C)O", "JYGXADMDTFJGBT-VWUMJDOOSA-N"],
  ["dexamethasone", "C[C@@H]1C[C@H]2[C@@H]3CCC4=CC(=O)C=C[C@@]4([C@]3([C@H](C[C@@]2([C@]1(C(=O)CO)O)C)O)F)C", "UREBDLICKHMUKA-CXSFZGCWSA-N"],
  ["estradiol", "C[C@]12CC[C@H]3[C@H]([C@@H]1CC[C@@H]2O)CCC4=C3C=CC(=C4)O", "VOXZDWNPVJITMN-ZBRFXRBCSA-N"],
  ["ivermectin B1a", "CC[C@H](C)[C@@H]1[C@H](CC[C@@]2(O1)C[C@@H]3C[C@H](O2)C/C=C(/[C@H]([C@H](/C=C/C=C/4\\CO[C@H]5[C@@]4([C@@H](C=C([C@H]5O)C)C(=O)O3)O)C)O[C@H]6C[C@@H]([C@H]([C@@H](O6)C)O[C@H]7C[C@@H]([C@H]([C@@H](O7)C)O)OC)OC)\\C)C", "AZSNMRSAGSSBNP-XPNPUAGNSA-N"],
  ["avermectin B1a", "CC[C@H](C)[C@@H]1[C@H](C=C[C@@]2(O1)C[C@@H]3C[C@H](O2)C/C=C(/[C@H]([C@H](/C=C/C=C/4\\CO[C@H]5[C@@]4([C@@H](C=C([C@H]5O)C)C(=O)O3)O)C)O[C@H]6C[C@@H]([C@H]([C@@H](O6)C)O[C@H]7C[C@@H]([C@H]([C@@H](O7)C)O)OC)OC)\\C)C", "RRZXIRBKKLTSOM-XPNPUAGNSA-N"],
  ["tacrolimus", "C[C@@H]1C[C@@H]([C@@H]2[C@H](C[C@H]([C@@](O2)(C(=O)C(=O)N3CCCC[C@H]3C(=O)O[C@@H]([C@@H]([C@H](CC(=O)[C@@H](/C=C(/C1)\\C)CC=C)O)C)/C(=C/[C@@H]4CC[C@H]([C@@H](C4)OC)O)/C)O)C)OC)OC", "QJJXYPPXXYFBGM-LFZNUXCKSA-N"],
  ["lovastatin", "CC[C@H](C)C(=O)O[C@H]1C[C@H](C=C2[C@H]1[C@H]([C@H](C=C2)C)CC[C@@H]3C[C@H](CC(=O)O3)O)C", "PCZOHLXUXFIOCF-BXMDZJJMSA-N"],
  ["penicillin G", "CC1([C@@H](N2[C@H](S1)[C@@H](C2=O)NC(=O)CC3=CC=CC=C3)C(=O)O)C", "JGSARLDLIJGVTE-MBNYWOFBSA-N"],
  ["cefalexin", "CC1=C(N2[C@@H]([C@@H](C2=O)NC(=O)[C@@H](C3=CC=CC=C3)N)SC1)C(=O)O", "ZAIPMKNFIOOWCQ-UEKVPHQBSA-N"],
  ["cocaine", "CN1[C@H]2CC[C@@H]1[C@H]([C@H](C2)OC(=O)C3=CC=CC=C3)C(=O)OC", "ZPUCINDJVBIVPJ-LJISPDSOSA-N"],
  ["scopolamine", "CN1[C@@H]2CC(C[C@H]1[C@H]3[C@@H]2O3)OC(=O)[C@H](CO)C4=CC=CC=C4", "STECJAGHUSJQJN-USLFZFAMSA-N"],
  ["atropine", "CN1[C@@H]2CC[C@H]1CC(C2)OC(=O)C(CO)C3=CC=CC=C3", "RKUNBYITZUJHSG-PJPHBNEVSA-N"],
  ["camphor", "C[C@@]12CC[C@@H](C1(C)C)CC2=O", "DSSYKIVIOFKYAU-XCBNKYQSSA-N"],
  ["adamantane", "C1C2CC3CC1CC(C2)C3", "ORILYTVJVMAKLC-UHFFFAOYSA-N"],
  ["cubane", "C12C3C4C1C5C2C3C45", "TXWRERCHRDBNLG-UHFFFAOYSA-N"],
  ["dodecahedrane", "C12C3C4C5C1C6C7C2C8C3C9C4C1C5C6C2C7C8C9C12", "OOHPORRAEMMMCX-UHFFFAOYSA-N"],
  ["twistane", "C1CC2CC3C1CC2CC3", "AEVSQVUUXPSWPL-UHFFFAOYSA-N"],
  ["triquinacene", "C1=CC2C=CC3C2C1C=C3", "HKRMLKXSBBQRIM-UHFFFAOYSA-N"],
  ["[2.2]paracyclophane", "C1CC2=CC=C(CCC3=CC=C1C=C3)C=C2", "OOLUVSIJOMLOCB-UHFFFAOYSA-N"],
  ["[6]helicene", "C1=CC=C2C(=C1)C=CC3=C2C4=C(C=C3)C=CC5=C4C6=CC=CC=C6C=C5", "UOYPNWSDSPYOSN-UHFFFAOYSA-N"],
  ["C60", "C12=C3C4=C5C6=C1C7=C8C9=C1C%10=C%11C(=C29)C3=C2C3=C4C4=C5C5=C9C6=C7C6=C7C8=C1C1=C8C%10=C%10C%11=C2C2=C3C3=C4C4=C5C5=C%11C%12=C(C6=C95)C7=C1C1=C%12C5=C%11C4=C3C3=C5C(=C81)C%10=C23", "XMWRBQBLMFGWIX-UHFFFAOYSA-N"],
  ["hexaprismane", "C%101C2C3C4C5C%10C%11C5C4C3C2C1%11", "C12H12"],
  // OPSIN's SMILES for (1Z,3E,5Z,7E,9Z,11E)-cyclododecahexaene and (1Z,3E,5E,7Z,9E,11E,13Z,15E,17E)-[18]annulene.
  ["[12]annulene", "C\\1=C/C=C/C=C\\C=C\\C=C/C=C1", "C12H12"],
  ["[18]annulene", "C\\1=C/C=C/C=C/C=C\\C=C\\C=C\\C=C/C=C/C=C1", "C18H18"],
];

// The atoms of a SMILES as written, in order (Indigo keeps the order, and adds the H atoms it draws at the end).
const ATOM = /\[[^\]]*\]|Br|Cl|[BCNOPSFIbcnops*]|%\d\d|\d|[().]/g;
const tokens = (smiles: string) => [...smiles.split(/\s/)[0].matchAll(ATOM)].map(([t]) => t).filter((t) => !/^[%\d().]/.test(t));
// The atoms of a SMILES and their neighbours (no layout), for choosing structures.
function graph(smiles: string): number[][] {
  const adj: number[][] = [], open = new Map<string, number>(), stack: number[] = [];
  let prev = -1;
  for (const [t] of smiles.split(/\s/)[0].matchAll(ATOM)) {
    if (t === "(") stack.push(prev);
    else if (t === ")") prev = stack.pop() ?? -1;
    else if (t === ".") prev = -1;
    else if (/^[%\d]/.test(t)) {
      const j = open.get(t);
      if (j === undefined) open.set(t, prev);
      else { open.delete(t); adj[prev].push(j); adj[j].push(prev); }
    } else {
      const i = adj.push([]) - 1;
      if (prev >= 0) { adj[i].push(prev); adj[prev].push(i); }
      prev = i;
    }
  }
  return adj;
}
// The shortest ring through each ring bond. A ring system is bridged when two of these rings share three or more atoms
// (norbornane, adamantane), and caged when there are more of them than independent rings (cubane's six faces).
function bridged(adj: number[][]): boolean {
  const rings = new Map<string, number[]>();
  adj.forEach((ns, u) => ns.forEach((v) => {
    if (u > v) return;
    const from = new Map([[u, -1]]), next = [u];
    for (let k = 0; k < next.length && !from.has(v); k++)
      for (const w of adj[next[k]]) if (!from.has(w) && !(next[k] === u && w === v)) { from.set(w, next[k]); next.push(w); }
    if (!from.has(v)) return;
    const ring = [];
    for (let x = v; x !== -1; x = from.get(x)!) ring.push(x);
    rings.set([...ring].sort((a, b) => a - b).join(), ring);
  }));
  const list = [...rings.values()], bonds = adj.reduce((n, ns) => n + ns.length, 0) / 2;
  const parts = new Set<number>(), seen = new Set<number>();
  adj.forEach((_, i) => { if (seen.has(i)) return; parts.add(i); const s = [i]; seen.add(i); while (s.length) for (const w of adj[s.pop()!]) if (!seen.has(w)) { seen.add(w); s.push(w); } });
  return list.length > bonds - adj.length + parts.size || list.some((r, k) => list.slice(k + 1).some((q) => q.filter((x) => r.includes(x)).length >= 3));
}
const centresIn = (smiles: string) => smiles.match(/\[[^\]]*@[^\]]*\]/g)?.length ?? 0;
const hard = (smiles: string) => centresIn(smiles) >= 3 || bridged(graph(smiles));

// The structures: the named ones, then drugs.ts's hard ones, then the dictionary's sample. Each structure
// once, by its InChIKey.
const seen = new Set<string>(), list: { name: string; smiles: string; from: string }[] = [];
const add = (name: string, smiles: string, from: string) => {
  const key = keyOf(smiles);
  if (!seen.has(key)) { seen.add(key); list.push({ name, smiles, from }); }
};
for (const [name, smiles, ref] of HARD) {
  // Each SMILES is the structure its name means.
  if (/^[A-Z]{14}-/.test(ref)) assert.equal(keyOf(smiles), ref, `${name}: PubChem's InChIKey`);
  else assert.equal(smilesWeight(smiles)?.formula, ref, `${name}: its formula`);
  add(name, smiles, "named");
}
for (const [name, smiles] of Object.entries(DRUGS)) if (!smiles.startsWith("=") && hard(smiles)) add(name, smiles, "drugs.ts");
const table = new URL("../data/names/dictionary.tsv.gz", import.meta.url);
if (existsSync(table)) {
  const rows = gunzipSync(readFileSync(table)).toString("utf8").split("\n").map((l) => l.split("\t")).filter(([s]) => s && s.length <= 4000 && hard(s));
  for (let k = 0; k < Math.min(SAMPLE, rows.length); k++) {
    const [s, names, , , read] = rows[Math.floor((k * rows.length) / Math.min(SAMPLE, rows.length))];
    add((read?.split("|")[0] || names?.split("|")[0].replace(/^!/, "") || s.slice(0, 30)).slice(0, 40), s, "dictionary");
  }
}

// The distance from point r to the segment from p to q.
const gap = (r: number[], p: number[], q: number[]) => {
  const dx = q[0] - p[0], dy = q[1] - p[1], f = Math.max(0, Math.min(1, ((r[0] - p[0]) * dx + (r[1] - p[1]) * dy) / (dx * dx + dy * dy || 1)));
  return Math.hypot(p[0] + f * dx - r[0], p[1] + f * dy - r[1]);
};
// ACS Document 1996 in px, and Arial's advances and ink for each glyph (cdxml.ts), as Name to Structure's repair
// measures them.
const pt = 4 / 3, ACS = { bond: 14.4 * pt, line: 0.6 * pt, bold: 2 * pt, spacing: 0.18 * 14.4 * pt, hash: 2.5 * pt, margin: 1.69 * pt, size: 10 * pt };
const arial = arialInk(ACS.size);
// Does the segment from a to b cross the box [x0, y0, x1, y1]?
const crosses = (a: number[], b: number[], [x0, y0, x1, y1]: number[]) => {
  let t0 = 0, t1 = 1;
  const dx = b[0] - a[0], dy = b[1] - a[1];
  for (const [p, q] of [[-dx, a[0] - x0], [dx, x1 - a[0]], [-dy, a[1] - y0], [dy, y1 - a[1]]]) {
    if (!p) { if (q < 0) return false; continue; }
    const r = q / p;
    if (p < 0) { if (r > t1) return false; t0 = Math.max(t0, r); } else { if (r < t0) return false; t1 = Math.min(t1, r); }
  }
  return true;
};
const side = (p: number[], q: number[], r: number[]) => (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]);
// Problems that are true chemistry: those Indigo's own drawing of the SMILES also has at the same atom (a valence error
// in the input), and stereocentres the SMILES leaves unset.
const CHEMISTRY = new Set(["valence", "isotopes", "parens"]);
type Row = { name: string; from: string; atoms: number; centres: number; ms: number; warnings: Record<string, number>; inchi: boolean; abs: number;
  longest: number; shortest: number; onAtom: number; onBond: number; onLabel: number; crossings: number; inkOnBond: number; inkOnLabel: number; error?: string };
const rows: Row[] = [];
// Indigo's first layout and InChI cost more than later ones.
parseStructure("C[C@H](N)C(=O)O");
for (const { name, smiles, from } of list) {
  const row: Row = { name, from, atoms: 0, centres: centresIn(smiles), ms: 0, warnings: {}, inchi: false, abs: 0, longest: 0, shortest: 0, onAtom: 0, onBond: 0, onLabel: 0, crossings: 0, inkOnBond: 0, inkOnLabel: 0 };
  rows.push(row);
  let m: Mol;
  const t = performance.now();
  try { m = parseStructure(smiles); } catch (e) { row.error = e instanceof Error ? e.message : String(e); continue; } finally { row.ms = Math.round(performance.now() - t); }
  const raw = parseStructure(smiles, false), n = raw.atoms.length;
  row.atoms = n;
  // As the editor checks it (enhanced stereo warnings on), then with Show Stereochemistry on.
  const ref = problems(raw, stereoFacts(raw, true)).filter((p) => CHEMISTRY.has(p.type)).map((p) => `${p.type} ${p.atom}`);
  // A stereocentre the SMILES leaves unset: its atom has no @ in the SMILES, and it is a stereocentre: a wedge and a
  // hash at it give two InChIs, alone or, for an atom that is not a bridgehead, with a wedge at each other unset atom
  // (endosulfan's S is a stereocentre only once its ring's centres are set). InChI does not know a cage sets its
  // bridgeheads (adamantane's), so a bridgehead counts only on its own, or where turning every bridgehead's wedge into
  // a hash at once gives another InChI (a tropane's: they place the bridge, and so set its C3).
  const cip = (x: Mol): Mol => ({ ...x, atoms: x.atoms.map((a) => ({ ...a, cip: true as const })) }), shown = cip(m), written = tokens(smiles);
  const adj = graph(smiles), linked = (a: number, c: number, not: number[]) => {
    const seen = new Set([a, ...not]), next = [a];
    for (let x = next.pop(); x !== undefined; x = next.pop()) for (const y of adj[x]) if (!seen.has(y)) { if (y === c) return true; seen.add(y); next.push(y); }
    return false;
  };
  // Three of its neighbours in rings, each two of them joined with the third left out.
  const bridgehead = (i: number) => {
    const r = adj[i].filter((j) => adj[i].some((k) => k !== j && linked(k, j, [i])));
    return r.length >= 3 && r.every((b) => { const [a, c] = r.filter((x) => x !== b); return linked(a, c, [i, b]); });
  };
  const open = [...stereoFacts(cip(raw)).centres].filter((i) => i < n && !written[i]?.includes("@"));
  const heads = open.filter(bridgehead);
  // The InChI of drawing x (Indigo's or Octet's) with a wedge at each of these atoms, a hash at each of the flipped ones:
  // the first's on its k-th single bond, each other's on its first. InChI gives a three-bonded N no configuration, so an
  // N here is read as a C.
  const as = (these: number[], flip: number[], k = 0, x = raw) => {
    const bonds = [...x.bonds], used = new Set<number>();
    for (const [at, c] of these.entries()) {
      const j = bonds.flatMap((x, q) => (x.type === 1 && x.atoms.includes(c) && !x.stereo && !used.has(q) ? [q] : []))[at ? 0 : k];
      if (j === undefined) continue;
      used.add(j);
      bonds[j] = { ...bonds[j], atoms: [c, bonds[j].atoms[0] === c ? bonds[j].atoms[1] : bonds[j].atoms[0]], stereo: flip.includes(c) ? 6 : 1 };
    }
    return toInchi({ ...x, atoms: x.atoms.map((a, i) => (a.label === "N" && !a.charge && these.includes(i) ? { ...a, label: "C" } : a)), bonds });
  };
  // Does a wedge or a hash at atom i give two InChIs, with these other atoms wedged? On any of its single bonds, in
  // Indigo's drawing or Octet's: InChI reads a wedge drawn between two bonds in line as neither.
  const turns = (i: number, others: number[] = []) => [raw, m].some((x) => x.bonds.filter((b) => b.type === 1 && b.atoms.includes(i)).some((_, k) => as([i, ...others], [], k, x) !== as([i, ...others], [i], k, x)));
  const together = heads.length > 0 && as(open, []) !== as(open, heads);
  const unset = (i: number) => open.includes(i) && (turns(i) || (!heads.includes(i) && turns(i, open.filter((c) => c !== i))) || together);
  const count = (list: ReturnType<typeof problems>, tag = "") => {
    for (const p of list) {
      if (ref.includes(`${p.type} ${p.atom}`) || (p.type === "unspecified" && unset(p.atom!))) continue;
      row.warnings[p.type + tag] = (row.warnings[p.type + tag] ?? 0) + 1;
    }
  };
  count(problems(m, stereoFacts(m, true)));
  count(problems(shown, stereoFacts(shown, true)).filter((p) => p.type === "unspecified" || p.type === "ambiguous"), "*");
  // A SMILES with no stereo marks leaves its double bonds open, and a drawing sets them: those are left out. So is a
  // double bond any SMILES leaves open that the drawing cannot: in a ring of fewer than 8 atoms (it can only be Z) or
  // on a ring of bonds alternately single and double (a porphyrin's, which InChI still gives an E or Z).
  const own = toInchi(smiles), drawn = toInchi(m);
  const order = (/\/N:([^/]*)/.exec(toInchiAux(m)?.split("\n")[1] ?? "")?.[1] ?? "").split(";").map((c) => c.split(","));
  const kind = new Map(m.bonds.map((x) => [[...x.atoms].sort((p, q) => p - q).join(), x.type])), near = (i: number) => m.bonds.flatMap((x) => (x.atoms.includes(i) ? [x.atoms[0] === i ? x.atoms[1] : x.atoms[0]] : []));
  // Breadth first from j to i, without the bond i-j: the ring's size, or with bonds alternately single and double
  // round the ring (InChI's double bond can be a single bond of the drawing's Kekulé form). An atom with a lone pair in
  // the ring (a pyrrole's N, a porphyrin's N-) can stand in for a double bond, as in an aromatic ring.
  const type = (x: number, y: number) => kind.get([x, y].sort((p, q) => p - q).join());
  const donor = (x: number) => (m.atoms[x].charge ?? 0) < 0 || (/^(N|O|S)$/.test(m.atoms[x].label) && near(x).every((y) => type(x, y) === 1));
  // via: the atoms the ring may pass through.
  const back = (i: number, j: number, alternate: boolean, via = (_: number) => true) => {
    const first = 3 - (type(i, j) ?? 1), seen = new Map([[`${j},${first}`, 0]]), next: [number, number][] = [[j, first]];
    for (let k = 0; k < next.length; k++) {
      const [x, want] = next[k], d = seen.get(`${x},${want}`)!;
      // Each step: the bond's type, and the type the next bond must have.
      const steps = alternate ? [[want, 3 - want], ...(want === 2 && donor(x) ? [[1, 2]] : [])] : [[0, 1]];
      for (const y of near(x)) for (const [bond, then] of steps) {
        if (y !== i && !via(y)) continue;
        if ((x === j && y === i) || (alternate && type(x, y) !== bond)) continue;
        if (y === i) { if (!alternate || bond === first) return d + 2; continue; }
        const key = `${y},${then}`;
        if (!seen.has(key)) { seen.set(key, d + 1); next.push([y, then]); }
      }
    }
    return Infinity;
  };
  const forced = (k: number, e: string) => {
    const [i, j] = e.replace(/[-+?]$/, "").split("-").map((x) => Number(order[k]?.[Number(x) - 1]) - 1);
    // Or on a ring of atoms that each have a double bond or a lone pair, with an end in a ring of fewer than 8 atoms (a
    // porphyrin's: its pyrroles hold it flat).
    const flat = (x: number) => near(x).some((y) => type(x, y) === 2) || donor(x), small = (x: number, not: number) => near(x).some((y) => y !== not && back(x, y, false) < 8);
    return i >= 0 && j >= 0 && (back(i, j, false) < 8 || back(i, j, true) < Infinity || (back(i, j, false, flat) < Infinity && (small(i, j) || small(j, i))));
  };
  const perPart = (x?: string) => (/\/b([^/]*)/.exec(x ?? "")?.[1] ?? "").split(";").map((c) => c.split(",").filter(Boolean));
  const set = perPart(own).map((c) => c.filter((e) => !e.endsWith("?")));
  const only = drawn?.replace(/\/b[^/]*/, "") === own?.replace(/\/b[^/]*/, "") && set.every((c, k) => c.every((e) => perPart(drawn)[k]?.includes(e)));
  row.inchi = drawn === own || (!!only && (!/[@/\\]/.test(smiles) || perPart(drawn).every((c, k) => c.every((e) => set[k]?.includes(e) || forced(k, e)))));
  row.abs = m.atoms.filter((a) => a.enhanced).length;
  // Bond lengths, leaving out the bonds to the H atoms drawn for wedges (drawn short on purpose).
  const xy = m.atoms.map((a) => a.location), lengths = m.bonds.filter((b) => b.atoms.every((i) => i < n)).map((b) => Math.hypot(xy[b.atoms[1]][0] - xy[b.atoms[0]][0], xy[b.atoms[1]][1] - xy[b.atoms[0]][1]));
  row.longest = Math.max(...lengths, 0);
  row.shortest = Math.min(...lengths, 1);
  // A label is an atom that is not a plain carbon; it covers about 0.3 of a bond length round its atom.
  const labelled = (i: number) => !!m.atoms[i].text || m.atoms[i].label !== "C";
  const bonded = new Set(m.bonds.map((b) => b.atoms.join()));
  const joined = (i: number, j: number) => bonded.has(`${i},${j}`) || bonded.has(`${j},${i}`);
  for (let i = 0; i < xy.length; i++) {
    for (let j = i + 1; j < xy.length; j++) {
      if (joined(i, j)) continue;
      const d = Math.hypot(xy[j][0] - xy[i][0], xy[j][1] - xy[i][1]);
      if (d < 0.35) row.onAtom++;
      else if (labelled(i) && labelled(j) && d < 0.6) row.onLabel++;
    }
    if (labelled(i) && m.bonds.some((b) => !b.atoms.includes(i) && gap(xy[i], xy[b.atoms[0]], xy[b.atoms[1]]) < 0.3)) row.onBond++;
  }
  m.bonds.forEach((b, k) => {
    const [p, q] = b.atoms.map((i) => xy[i]);
    for (const c of m.bonds.slice(k + 1)) {
      if (c.atoms.some((i) => b.atoms.includes(i))) continue;
      const [r, s] = c.atoms.map((i) => xy[i]);
      if (side(p, q, r) * side(p, q, s) < 0 && side(r, s, p) * side(r, s, q) < 0) row.crossings++;
    }
  });
  // As drawn, each label's ink (its H atoms and charge too, as in OH or NH2) in Arial at ACS sizes, a bond length a bond
  // as the editor draws it: crossed by a bond it is not part of, or touching another label's. The counts above take a
  // label as a point and miss these. Ink within half a px of a bond's middle line (a line is 0.8 px wide) or of another
  // label's ink touches it.
  const d = render(m, ACS, arial, ACS.bond), box = d.label.map((b) => b && [b[0] - 0.5, b[1] - 0.5, b[2] + 0.5, b[3] + 0.5]), k = d.scale;
  const px = (i: number) => [xy[i][0] * k, -xy[i][1] * k];
  box.forEach((b, i) => {
    if (!b) return;
    if (m.bonds.some((x) => !x.atoms.includes(i) && crosses(px(x.atoms[0]), px(x.atoms[1]), b))) row.inkOnBond++;
    for (const c of box.slice(i + 1)) if (c && b[0] < c[2] && c[0] < b[2] && b[1] < c[3] && c[1] < b[3]) row.inkOnLabel++;
  });
}

// What each structure fails, by cause: the target's causes, then the layout's.
const causes = (r: Row): string[] => r.error ? [`not drawn: ${r.error}`] : [
  ...Object.keys(r.warnings).map((w) => (w.endsWith("*") ? `warning ${w.slice(0, -1)} (Show Stereochemistry on)` : `warning ${w}`)),
  ...(r.inchi ? [] : ["InChI differs from the SMILES"]), ...(r.abs ? ["abs flags"] : []), ...(r.ms > BOUND ? [`over ${BOUND} ms`] : []),
  ...(r.onAtom ? ["atom on atom"] : []), ...(r.onBond ? ["label on a bond"] : []), ...(r.onLabel ? ["label on a label"] : []),
  ...(r.longest > 1.3 || r.shortest < 0.75 ? ["layout: bond length outside 0.75 to 1.3"] : []), ...(r.crossings ? ["layout: crossing bonds"] : []),
  ...(r.inkOnBond ? ["label ink crossed by a bond"] : []), ...(r.inkOnLabel ? ["label ink touching a label's"] : []),
];
const target = (c: string) => !c.startsWith("layout:");
const pad = (s: string | number, w: number) => String(s).slice(0, w).padEnd(w);
console.log(["structure".padEnd(28), "from".padEnd(10), "atoms", "@ ", "   ms", "InChI", "abs", "bonds      ", "on-atom", "on-bond", "on-label", "cross", "ink", "warnings"].join(" "));
for (const r of rows)
  console.log([pad(r.name, 28), pad(r.from, 10), String(r.atoms).padStart(5), String(r.centres).padStart(2), String(r.ms).padStart(5), pad(r.error ? "-" : r.inchi ? "same" : "DIFF", 5), String(r.abs).padStart(3),
    pad(`${r.shortest.toFixed(2)}-${r.longest.toFixed(2)}`, 11), String(r.onAtom).padStart(7), String(r.onBond).padStart(7), String(r.onLabel).padStart(8), String(r.crossings).padStart(5), pad(`${r.inkOnBond}/${r.inkOnLabel}`, 5),
    r.error ? `not drawn: ${r.error}` : Object.entries(r.warnings).map(([k, v]) => `${k} ${v}`).join(", ")].join(" "));
const byCause = new Map<string, string[]>();
for (const r of rows) for (const c of causes(r)) byCause.set(c, [...(byCause.get(c) ?? []), r.name]);
console.log("\nFailures by cause (* in a warning: with Show Stereochemistry on):");
for (const [c, names] of [...byCause].sort((p, q) => q[1].length - p[1].length)) console.log(`  ${c}: ${names.length} (${names.slice(0, 12).join(", ")}${names.length > 12 ? ", …" : ""})`);
const ms = rows.filter((r) => !r.error).map((r) => r.ms).sort((a, b) => a - b), at = (f: number) => ms[Math.min(ms.length - 1, Math.floor(f * ms.length))];
const failing = rows.filter((r) => causes(r).some(target));
console.log(`\nhardmolecules.check: ${rows.length} structures, ${rows.length - failing.length} meet the target, ${failing.length} do not; ` +
  `time median ${at(0.5)} ms, 90th percentile ${at(0.9)} ms, slowest ${ms[ms.length - 1]} ms (${rows.find((r) => r.ms === ms[ms.length - 1])?.name})`);
const unmet = (r: Row) => causes(r).filter((c) => target(c) && (STRICT || !c.startsWith("over ")));
// Known to fail, until fixed: an annulene's ring is drawn as a regular polygon, so each double bond in it is drawn Z,
// though its name or SMILES sets some E.
const KNOWN = new Set(["[12]annulene", "[18]annulene"]);
console.log(`Known failures: ${rows.filter((r) => KNOWN.has(r.name)).map((r) => `${r.name}: ${unmet(r).join("; ") || "now meets the target"}`).join(", ")}`);
assert.deepEqual(rows.filter((r) => !KNOWN.has(r.name) && unmet(r).length).map((r) => `${r.name}: ${unmet(r).join("; ")}`), [], "the target");
