// Run: node src/names.check.ts. Name to structure: Octet's own name tables (common.ts, drugs.ts), salts, adducts and
// mixtures, the test for SMILES by its look, and 200 common drug and reagent names against their standard InChIKeys
// (reference keys from PubChem, 17 October 2026; not shipped). Before the names in drugs.ts and the reagent formulas,
// and while paste read text as SMILES first, 62 of the 200 gave the right structure, 7 a wrong one ("aspirin" drew
// H3NPS) and 129 none.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { citable, COMMON, commonKey } from "./common.ts";
import { DRUGS } from "./drugs.ts";
import { abbreviationOf, attachOpsin, knownName, looksLikeSmiles, nameToSmiles, namesStarting } from "./names.ts";

const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("names.check: skipped (no OPSIN build)"); process.exit(0); }
const pack = readFileSync(new URL("opsin-data.bin", dir));
const files = new Map<string, Int8Array>();
for (let p = 0; ; ) {
  const n = pack.readUInt16BE(p); p += 2;
  if (!n) break;
  const name = pack.toString("latin1", p, p + n); p += n;
  const size = pack.readInt32BE(p); p += 4;
  files.set(name, new Int8Array(pack.buffer, pack.byteOffset + p, size)); p += size;
}
(globalThis as { opsinResource?: unknown }).opsinResource = (name: string) => files.get(name) ?? null;
const opsin = await import(new URL("opsin.js", dir).href);
opsin.init();
const index: Record<string, string> = JSON.parse(readFileSync(new URL("./nameindex.json", import.meta.url), "utf8"));
const cites: Record<string, string> = JSON.parse(readFileSync(new URL("./abbreviations.json", import.meta.url), "utf8"));
// Before the engine loads, the search has common.ts alone.
assert.deepEqual(namesStarting("tren"), ["TREN"]);
attachOpsin(opsin, readFileSync(new URL("names.txt", dir), "utf8"), index, DRUGS, cites);
const indigo = await (await import(new URL("../node_modules/indigo-ketcher/indigo-ketcher-norender.js", import.meta.url).href)).default();
const options = (kv: Record<string, string> = {}) => { const o = new indigo.MapStringString(); for (const [k, v] of Object.entries(kv)) o.set(k, v); return o; };
// What the app draws for SMILES, and its standard InChI (tools/names/index.mjs: Indigo's layout, and an atom bonded
// to a metal keeps the hydrogens Octet draws).
const { abbreviations, build, countsOf, drawnKet: drawn, inchiOf } = await import(new URL("../tools/names/index.mjs", import.meta.url).href);
const inchiKey = (s: string) => { const o = options(); try { return indigo.convert(s, "inchi-key", o).trim() as string; } catch { return undefined; } finally { o.delete(); } };
const keyOf = (smiles: string) => inchiKey(drawn(smiles));
const partKeys = (smiles: string) => smiles.split(".").map(keyOf).sort();

// Text that looks like SMILES, and text that does not (Indigo would read "aspirin" and "spiro" as query atoms).
for (const t of ["CCO", "c1ccccc1", "C[C@@H](N)C(=O)O", "OC(=O)c1ccccc1OC(C)=O", "[Na+].[Cl-]", "InChI=1S/CH4/h1H4", "CC>>CO", "C1CC1 |$_R1;;$|", "c1ccccc1 benzene", "CC(=O)O acetic acid"])
  assert.ok(looksLikeSmiles(t), `${t} looks like SMILES`);
for (const t of ["aspirin", "spiro", "ethyl acetate", "Pd(PPh3)4", "2-methylpropane", "caffeine", "Et3N·HCl", "CCO ethanol", "NBS reagent", "5", "2:1", "1.5", "5 mg", "Boc", "Bn", "Cs", "Co", "Sn", "on"]) assert.ok(!looksLikeSmiles(t), `${t} does not look like SMILES`);
assert.equal(nameToSmiles("spiro"), undefined);
// A formula that is not SMILES reads from the table (SO2, COCl2). A formula that is also SMILES ("CO") is read as SMILES.
assert.equal(nameToSmiles("SO2"), "O=S=O");
assert.equal(nameToSmiles("COCl2"), "O=C(Cl)Cl");
assert.equal(nameToSmiles("CO"), undefined);

// Every entry reads, keeps no aromatic bond once Indigo has drawn it (so the app's formula and mass work), and
// every "=name" points to an entry. No key is in both tables.
const entries: [string, string][] = [
  ...Object.entries(COMMON).map(([k, v]): [string, string] => { const w = v.startsWith("=") ? COMMON[v.slice(1)] ?? "" : v; return [k, w.startsWith("smiles:") ? w.slice(7) : opsin.parseToSmiles(w) ?? ""]; }),
  ...Object.entries(DRUGS).map(([k, v]): [string, string] => [k, v.startsWith("=") ? DRUGS[v.slice(1)] ?? "" : v]),
];
for (const [k, smiles] of entries) {
  assert.ok(smiles && !smiles.startsWith("="), `${k} reads`);
  const ket = JSON.parse(drawn(smiles));
  const aromatic = ket.root.nodes.some(({ $ref }: { $ref: string }) => ket[$ref]?.bonds?.some((b: { type: number }) => b.type === 4));
  assert.ok(!aromatic, `${k} draws with Kekulé bonds`);
  assert.ok(nameToSmiles(k), `${k} reads through nameToSmiles`);
}
const shared = Object.keys(DRUGS).filter((k) => Object.keys(COMMON).some((c) => commonKey(c) === commonKey(k)));
assert.deepEqual(shared, [], "a name in both common.ts and drugs.ts");

// Salts, adducts, hydrates and mixtures read in parts. A whole-number ratio draws that many of each part, as OPSIN
// does; another ratio draws each part once.
const ethanol = keyOf("CCO"), water = keyOf("O");
for (const name of ["2:1 mixture of ethanol and water", "a 2:1 mixture of ethanol and water", "ethanol and water (2:1)", "EtOH/H2O 2:1"])
  assert.deepEqual(partKeys(nameToSmiles(name) ?? ""), [ethanol, ethanol, water].sort(), name);
for (const name of ["EtOH/H2O", "ethanol--water (0.72/0.28)", "ethanol + water", "ethanol–water", "mixture of ethanol and water"])
  assert.deepEqual(partKeys(nameToSmiles(name) ?? ""), [ethanol, water].sort(), name);
assert.deepEqual(partKeys(nameToSmiles("CuSO4·5H2O") ?? ""), partKeys(`${COMMON.CuSO4.slice(7)}.O.O.O.O.O`), "CuSO4·5H2O");
assert.deepEqual(partKeys(nameToSmiles("sertraline hydrochloride") ?? ""), partKeys(`${DRUGS.sertraline}.Cl`), "sertraline hydrochloride");
// A full stop between parts reads as "·" does: the same structure from the table.
assert.equal(nameToSmiles("Et3N.HCl"), nameToSmiles("Et3N·HCl"));
assert.equal(keyOf(nameToSmiles("MeI") ?? ""), keyOf("CI"));
assert.deepEqual(partKeys(nameToSmiles("EDC·HCl") ?? ""), partKeys(`${opsin.parseToSmiles(COMMON.EDC)}.Cl`), "EDC·HCl");
assert.equal(nameToSmiles("ethanol and unobtainium"), undefined);

// The index of Octet's own names for Structure to Name is up to date (tools/names/index.mjs), and each name in it
// reads back as its structure.
assert.deepEqual(build(), index, "src/nameindex.json is out of date: run node tools/names/index.mjs");
const inchi = (smiles: string) => inchiOf(smiles) as string | undefined;
for (const [key, name] of Object.entries(index)) assert.equal(inchi(nameToSmiles(name) ?? ""), key, `${name} reads back`);
assert.equal(knownName(inchi(DRUGS.imatinib)), "imatinib");
assert.equal(knownName(inchi(opsin.parseToSmiles(COMMON.DBU))), COMMON.DBU);

// Literature abbreviations. TREN is tris(2-aminoethyl)amine, whatever its case, spaces or hyphens.
const tren = inchi(opsin.parseToSmiles("tris(2-aminoethyl)amine"));
for (const name of ["TREN", "tren", "Tren", "T-REN"]) assert.equal(inchi(nameToSmiles(name) ?? ""), tren, name);
assert.equal(inchi(nameToSmiles("[Ru(bpy)3]Cl2") ?? ""), inchi(nameToSmiles("Ru(bpy)3Cl2") ?? ""));
// The search: Octet's own names that begin as typed, the exact one first, then the shortest, one per structure.
assert.deepEqual(namesStarting("TR").slice(0, 4), ["Trp", "TREN", "Tris", "trien"]);
assert.deepEqual(namesStarting("TRE").slice(0, 1), ["TREN"]);
assert.equal(namesStarting("en")[0], "en");
assert.equal(namesStarting("dppb")[0], "dppb");
assert.ok(namesStarting("dppb").includes("dppbz"));
assert.deepEqual(namesStarting("Et3N"), ["Et3N", "Et3N·HCl"]);
assert.ok(!namesStarting("TE").includes("Et3N") && namesStarting("TE").includes("TEA"));
assert.ok(namesStarting("tris").filter((n) => n.toLowerCase().startsWith("tris(hydroxymethyl)") || n === "Tris").length === 1, "Tris once");
assert.deepEqual(namesStarting("sertral"), ["sertraline"], "drug names once the engine has loaded");
assert.equal(namesStarting("x".repeat(30)).length, 0);
assert.ok(namesStarting("p", 8).length === 8);

// What can be cited after a name: not the structure's formula in element symbols, not a drug's name. An acronym whose
// letters are element symbols (NBS, DIOP) is cited.
const counts = (k: string) => countsOf(inchi(nameToSmiles(k) ?? "") ?? "InChI=1S/");
for (const k of ["CH2Cl2", "NaCl", "K2CO3", "(COCl)2", "H2O", "D2O", "CDCl3", "PdCl2", "LiAlH4", "NaOH", "KCN", "CuSO4", "FeCl3", "Mn(CO)5Br", "aspirin", "naproxen"]) assert.ok(!citable(k, counts(k)), k);
for (const k of ["TREN", "Et3N", "AcOH", "TsCl", "PPh3", "Pd(OAc)2", "CuTC", "LAH", "DMSO-d6", "IMes·HCl", "Wilkinson's catalyst", "NBS", "DIOP", "DBU", "HFIP", "PCC"]) assert.ok(citable(k, counts(k)), k);
assert.ok(!citable("CuSO4·5H2O", { Cu: 1, S: 1, O: 9, H: 10 }));
// The abbreviations by InChI are up to date, and each is the first citable key listed for its structure.
assert.deepEqual(abbreviations(), cites, "src/abbreviations.json is out of date: run node tools/names/index.mjs");
assert.equal(abbreviationOf(tren), "TREN");
assert.equal(abbreviationOf(inchi("CCN(CC)CC")), "Et3N");
assert.equal(abbreviationOf(inchi("ClCCl")), "DCM");
assert.equal(abbreviationOf(inchi(nameToSmiles("LiAlH4") ?? "")), "LAH");
assert.equal(abbreviationOf(inchi("CC(=O)CC(C)=O")), "acacH");
assert.equal(abbreviationOf(inchi("O")), undefined, "water");
assert.equal(abbreviationOf(inchi("[Na+].[Cl-]")), undefined, "NaCl");
assert.equal(abbreviationOf(inchi("CC(=O)Oc1ccccc1C(O)=O")), undefined, "aspirin is a name");
assert.equal(abbreviationOf(inchi("C[C@H](N)C(O)=O")), "Ala");
assert.equal(abbreviationOf(inchi("C[C@@H](N)C(O)=O")), undefined, "D-alanine is not Ala");
// An entry drawn with no stereochemistry also names a drawing with it: (R,R)-DIOP is DIOP.
const diop = inchi("CC1(C)O[C@H](CP(c2ccccc2)c2ccccc2)[C@@H](CP(c2ccccc2)c2ccccc2)O1");
assert.ok(diop?.includes("/t"));
assert.equal(abbreviationOf(diop), "DIOP");
assert.equal(abbreviationOf(undefined), undefined);

// 200 common drug and reagent names, with the standard InChIKey of the structure each should give. PCC and
// Wilkinson's catalyst are drawn as Octet draws them (pyridinium chlorochromate as an ion pair, Rh bonded to Cl),
// where PubChem keeps PCC as pyridine, CrO3 and HCl and Wilkinson's chloride apart.
const WANT: Record<string, string> = {
  "aspirin": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N", "paracetamol": "RZVAJINKPMORJF-UHFFFAOYSA-N",
  "acetaminophen": "RZVAJINKPMORJF-UHFFFAOYSA-N", "ibuprofen": "HEFNNWSXXWATRW-UHFFFAOYSA-N",
  "naproxen": "CMWTZPSULFXXJA-VIFPVBQESA-N", "diclofenac": "DCOPUUMXTXDBNB-UHFFFAOYSA-N",
  "celecoxib": "RZEKVGVHFLEQIL-UHFFFAOYSA-N", "indomethacin": "CGIGDMFJXJATDK-UHFFFAOYSA-N",
  "ketoprofen": "DKYWVDODHFEZIM-UHFFFAOYSA-N", "meloxicam": "ZRVUJXDFFKFLMG-UHFFFAOYSA-N",
  "caffeine": "RYYVLZVUVIJVGH-UHFFFAOYSA-N", "nicotine": "SNICXCGAKADSCV-JTQLQIEISA-N",
  "morphine": "BQJCRHHNABKAKU-KBQPJGBKSA-N", "codeine": "OROGSEYTTFOCAN-DNJOTXNNSA-N",
  "oxycodone": "BRUQQQPBMZOVGD-XFKAJCMBSA-N", "hydrocodone": "LLPOLZWFYMWNKH-CMKMFDCUSA-N",
  "fentanyl": "PJMPHNIQZUBGLI-UHFFFAOYSA-N", "tramadol": "TVYLLZQTGLZFBW-ZBFHGGJFSA-N",
  "methadone": "USSIQXCVUWKGNF-UHFFFAOYSA-N", "naloxone": "UZHSEJADLWPNLE-GRGSLBFTSA-N",
  "cocaine": "ZPUCINDJVBIVPJ-LJISPDSOSA-N", "lidocaine": "NNJVILVZKWQKPM-UHFFFAOYSA-N",
  "procaine": "MFDFERRIHVXMIY-UHFFFAOYSA-N", "benzocaine": "BLFLLBZGZJTVJG-UHFFFAOYSA-N",
  "bupivacaine": "LEBVLXFERQHONN-UHFFFAOYSA-N", "amoxicillin": "LSQZJLSUYDQPKJ-NJBDSQKTSA-N",
  "ampicillin": "AVKUERGKIZMTKX-NJBDSQKTSA-N", "penicillin G": "JGSARLDLIJGVTE-MBNYWOFBSA-N",
  "cefalexin": "ZAIPMKNFIOOWCQ-UEKVPHQBSA-N", "ciprofloxacin": "MYSWGUAQZAJSOK-UHFFFAOYSA-N",
  "levofloxacin": "GSDSWSVVBLHKDQ-JTQLQIEISA-N", "doxycycline": "SGKRLCUYIXIAHR-AKNGSSGZSA-N",
  "tetracycline": "NWXMGUDVXFXRIG-WESIUVDSSA-N", "metronidazole": "VAOCPAMSLUNLGC-UHFFFAOYSA-N",
  "trimethoprim": "IEDVJHCEMCRBQM-UHFFFAOYSA-N", "sulfamethoxazole": "JLKIGFTWXXRPMT-UHFFFAOYSA-N",
  "chloramphenicol": "WIIZWVCIJKGZOK-RKDXNWHRSA-N", "isoniazid": "QRXWMOHMRWLFEY-UHFFFAOYSA-N",
  "linezolid": "TYZROVQLWOKYKF-ZDUSSCGKSA-N", "fluconazole": "RFHAOTPXVQNOHP-UHFFFAOYSA-N",
  "aciclovir": "MKUXAQIIEYXACX-UHFFFAOYSA-N", "oseltamivir": "VSZGPKBBMSAYNT-RRFJBIMHSA-N",
  "zidovudine": "HBOMLICNUCNMMY-XLPZGREQSA-N", "atorvastatin": "XUKUURHRXDUEBC-KAYWLYCHSA-N",
  "simvastatin": "RYMZZMVNJRMUDD-HGQWONQESA-N", "rosuvastatin": "BPRHUIZQVSMCRT-VEUZHWNKSA-N",
  "pravastatin": "TUZYXOIXSAXUGO-PZAWKZKUSA-N", "lovastatin": "PCZOHLXUXFIOCF-BXMDZJJMSA-N",
  "metformin": "XZWYZXLIPXDOLR-UHFFFAOYSA-N", "glipizide": "ZJJXGWJIGJFDTL-UHFFFAOYSA-N",
  "glibenclamide": "ZNNLBTZKUZBEKO-UHFFFAOYSA-N", "sitagliptin": "MFFMDFFZMYYVKS-SECBINFHSA-N",
  "pioglitazone": "HYAFETHFCAUJAY-UHFFFAOYSA-N", "lisinopril": "RLAWWYSOJDYHDC-BZSNNMDCSA-N",
  "enalapril": "GBXSMTUPTTWBMN-XIRDDKMYSA-N", "captopril": "FAKRSMQSSFJEIM-RQJHMYQMSA-N",
  "ramipril": "HDACQVRGBOVJII-JBDAPHQKSA-N", "losartan": "PSIFNNKUMBGKDQ-UHFFFAOYSA-N",
  "valsartan": "ACWBQPMHZXGDFX-QFIPXVFZSA-N", "amlodipine": "HTIQEAQVCYTUBX-UHFFFAOYSA-N",
  "nifedipine": "HYIMSNHJOBLJNT-UHFFFAOYSA-N", "diltiazem": "HSUGRBWQSSZJOP-RTWAWAEBSA-N",
  "verapamil": "SGTNSNPWRIOYBX-UHFFFAOYSA-N", "metoprolol": "IUBSYMUCCVWXPE-UHFFFAOYSA-N",
  "atenolol": "METKIMKYRPQLGS-UHFFFAOYSA-N", "propranolol": "AQHHHDLHHXJYJD-UHFFFAOYSA-N",
  "carvedilol": "OGHNVEJMJSYVRP-UHFFFAOYSA-N", "bisoprolol": "VHYCDWMUTMEGQY-UHFFFAOYSA-N",
  "hydrochlorothiazide": "JZUFKLXOESDKRF-UHFFFAOYSA-N", "furosemide": "ZZUFCTLCJUWOSV-UHFFFAOYSA-N",
  "spironolactone": "LXMSZDCAJNLERA-ZHYRCANASA-N", "warfarin": "PJVWKTKQMONHTI-UHFFFAOYSA-N",
  "clopidogrel": "GKTWGGQPFAXNFI-HNNXBMFYSA-N", "apixaban": "QNZCBYKSOIHPEH-UHFFFAOYSA-N",
  "rivaroxaban": "KGFYHTZWPPHNLQ-AWEZNQCLSA-N", "omeprazole": "SUBDBMMJDZJVOS-UHFFFAOYSA-N",
  "esomeprazole": "SUBDBMMJDZJVOS-DEOSSOPVSA-N", "lansoprazole": "MJIHNNLFOKEZEW-UHFFFAOYSA-N",
  "pantoprazole": "IQPSEEYGBUAQFF-UHFFFAOYSA-N", "ranitidine": "VMXUWOKSQNHOCA-UKTHLTGXSA-N",
  "famotidine": "XUFQPHANEAPEMJ-UHFFFAOYSA-N", "sertraline": "VGKDLMBJGBXTGI-SJCJKPOMSA-N",
  "fluoxetine": "RTHCYVBBDHJXIQ-UHFFFAOYSA-N", "paroxetine": "AHOUBRCZNHFOSL-YOEHRIQHSA-N",
  "citalopram": "WSEQXVZVJXJVFP-UHFFFAOYSA-N", "escitalopram": "WSEQXVZVJXJVFP-FQEVSTJZSA-N",
  "venlafaxine": "PNVNVHUZROJLTJ-UHFFFAOYSA-N", "duloxetine": "ZEUITGRIYCTCEM-KRWDZBQOSA-N",
  "bupropion": "SNPPWIUOZRMYNY-UHFFFAOYSA-N", "amitriptyline": "KRMDCWKBEZIMAB-UHFFFAOYSA-N",
  "imipramine": "BCGWQEUPMDMJNV-UHFFFAOYSA-N", "mirtazapine": "RONZAEMNMFQXRA-UHFFFAOYSA-N",
  "trazodone": "PHLBKPHSAVXXEF-UHFFFAOYSA-N", "diazepam": "AAOVKJBEBIDNHE-UHFFFAOYSA-N",
  "alprazolam": "VREFGVBLTWBCJP-UHFFFAOYSA-N", "lorazepam": "DIWRORZWFLOCLC-UHFFFAOYSA-N",
  "clonazepam": "DGBIGWXXNGSACT-UHFFFAOYSA-N", "midazolam": "DDLIGBOFAVUZHB-UHFFFAOYSA-N",
  "zolpidem": "ZAFYATHCZYHLPB-UHFFFAOYSA-N", "haloperidol": "LNEPOXFFQSENCJ-UHFFFAOYSA-N",
  "chlorpromazine": "ZPEIMTDSQAKGNT-UHFFFAOYSA-N", "olanzapine": "KVWDHTXUZHCGIO-UHFFFAOYSA-N",
  "quetiapine": "URKOMYMAXPYINW-UHFFFAOYSA-N", "risperidone": "RAPZEAPATHNIPO-UHFFFAOYSA-N",
  "aripiprazole": "CEUORZQYGODEFX-UHFFFAOYSA-N", "clozapine": "QZUDBNBUXVUHMW-UHFFFAOYSA-N",
  "levothyroxine": "XUIIKFGFIJCVMT-LBPRGKRZSA-N", "prednisolone": "OIGNJSKKLXVSLS-VWUMJDOOSA-N",
  "prednisone": "XOFYZVNMUHMLCC-ZPOLXVRWSA-N", "dexamethasone": "UREBDLICKHMUKA-CXSFZGCWSA-N",
  "hydrocortisone": "JYGXADMDTFJGBT-VWUMJDOOSA-N", "testosterone": "MUMGGOZAMZWBJJ-DYKIIFRCSA-N",
  "estradiol": "VOXZDWNPVJITMN-ZBRFXRBCSA-N", "progesterone": "RJKFOVLPORLFTN-LEKSSAKUSA-N",
  "sildenafil": "BNRNXUUZRGQAQC-UHFFFAOYSA-N", "tadalafil": "WOXKDUGGOYFFRN-IIBYNOLFSA-N",
  "salbutamol": "NDAUXUAQIAJITI-UHFFFAOYSA-N", "loratadine": "JCCNYMKQOSZNPW-UHFFFAOYSA-N",
  "cetirizine": "ZKLPARSLTMPFCP-UHFFFAOYSA-N", "diphenhydramine": "ZZVUWRFHKOJYTH-UHFFFAOYSA-N",
  "gabapentin": "UGJMXCAKCUNAIE-UHFFFAOYSA-N", "pregabalin": "AYXYPKUFHZROOJ-ZETCQYMHSA-N",
  "levetiracetam": "HPHUVLMMVZITSG-LURJTMIESA-N", "carbamazepine": "FFGPTBGBLSHEPO-UHFFFAOYSA-N",
  "phenytoin": "CXOFVDLJLONNDW-UHFFFAOYSA-N", "valproic acid": "NIJJYAXOARWZEE-UHFFFAOYSA-N",
  "lamotrigine": "PYZRQGJRPPTADH-UHFFFAOYSA-N", "donepezil": "ADEBPBSSDYVVLD-UHFFFAOYSA-N",
  "levodopa": "WTDRDQBEARUVNC-LURJTMIESA-N", "ondansetron": "FELGMEQIXOGIFQ-UHFFFAOYSA-N",
  "metoclopramide": "TTWJBBZEZQICBI-UHFFFAOYSA-N", "loperamide": "RDOIQAHITMMDAJ-UHFFFAOYSA-N",
  "tamoxifen": "NKANXQFJJICGDU-QPLCGJKRSA-N", "imatinib": "KTUFNOKKBVMGRW-UHFFFAOYSA-N",
  "methotrexate": "FBOZXECLQNJBKD-ZDUSSCGKSA-N", "fluorouracil": "GHASVSINZRGABV-UHFFFAOYSA-N",
  "cyclophosphamide": "CMSMOCZEIVJLDB-UHFFFAOYSA-N", "allopurinol": "OFCNXPDARWKPPY-UHFFFAOYSA-N",
  "colchicine": "IAKHMKGGTNLKSZ-INIZCTEOSA-N", "chloroquine": "WHTVZRBIWZFKQO-UHFFFAOYSA-N",
  "hydroxychloroquine": "XXSMGPRMXLTPCZ-UHFFFAOYSA-N", "quinine": "LOUPRKONTZGTKE-WZBLMQSHSA-N",
  "thalidomide": "UEJJHQNACJXSKW-UHFFFAOYSA-N", "ketamine": "YQEZLKZALYSWHR-UHFFFAOYSA-N",
  "propofol": "OLBCVFGFOZPWHH-UHFFFAOYSA-N", "adrenaline": "UCTWMZQNUQWSLP-VIFPVBQESA-N",
  "dopamine": "VYFYYTLLBUKUHU-UHFFFAOYSA-N", "serotonin": "QZAYGJVTTNCVMB-UHFFFAOYSA-N",
  "melatonin": "DRLFMBDRBRZALE-UHFFFAOYSA-N", "amphetamine": "KWTSXDURSIMDCE-UHFFFAOYSA-N",
  "menthol": "NOOLISFMXDJSKH-UHFFFAOYSA-N", "vanillin": "MWOOGOJBHIARFG-UHFFFAOYSA-N",
  "camphor": "DSSYKIVIOFKYAU-UHFFFAOYSA-N", "cholesterol": "HVYWMOMLDIMFJA-DPAQBDIFSA-N",
  "ascorbic acid": "CIWBSHSKHKDKBQ-JLAZNSOCSA-N", "THF": "WYURNTSHIVDZCO-UHFFFAOYSA-N",
  "DCM": "YMWUJEATGCHHMB-UHFFFAOYSA-N", "DMF": "ZMXDDKWLCZADIW-UHFFFAOYSA-N", "DMSO": "IAZDPXIOMUYVGZ-UHFFFAOYSA-N",
  "acetone": "CSCPPACGZOOCGX-UHFFFAOYSA-N", "pyridine": "JUJWROOIHBZHMG-UHFFFAOYSA-N",
  "triethylamine": "ZMANZCXQSJIPKH-UHFFFAOYSA-N", "DIPEA": "JGFZNNIVVJXRND-UHFFFAOYSA-N",
  "DMAP": "VHYFNPMBLIVWCW-UHFFFAOYSA-N", "DBU": "GQHTUMJGOHRCHB-UHFFFAOYSA-N", "TFA": "DTQVDTLACAAQTR-UHFFFAOYSA-N",
  "mCPBA": "NHQDETIJWKXCTC-UHFFFAOYSA-N", "NBS": "PCLIMKBDDGJMGD-UHFFFAOYSA-N", "Boc2O": "DYHSDKLCOJIUFX-UHFFFAOYSA-N",
  "TsCl": "YYROPELSRYBVMQ-UHFFFAOYSA-N", "SOCl2": "FYSNRJHAOHDILO-UHFFFAOYSA-N",
  "oxalyl chloride": "CTSLXHKWHWQRSH-UHFFFAOYSA-N", "POCl3": "XHXFXVLFKHQFAL-UHFFFAOYSA-N",
  "K2CO3": "BWHMMNNQKKPAPP-UHFFFAOYSA-L", "NaHCO3": "UIIMBOGNXHQVGW-UHFFFAOYSA-M",
  "Cs2CO3": "FJDQFPXHSGXQBY-UHFFFAOYSA-L", "NaH": "BZKBCQXYZZXSCO-UHFFFAOYSA-N", "NaOH": "HEMHJVSKTPXQMS-UHFFFAOYSA-M",
  "LiAlH4": "OCZDCIYGECBNKL-UHFFFAOYSA-N", "NaBH4": "YOQDYZUWIQVZSF-UHFFFAOYSA-N",
  "DIBAL-H": "AZWXAPCAJCYGIA-UHFFFAOYSA-N", "n-BuLi": "MZRVEZGGRBJDDB-UHFFFAOYSA-N",
  "LDA": "ZCSHNCUQKCANBX-UHFFFAOYSA-N", "Pd(PPh3)4": "NFHFRUOZVGFOOS-UHFFFAOYSA-N",
  "Pd(OAc)2": "YJVFFLUZDVXJQI-UHFFFAOYSA-L", "Pd2(dba)3": "CYPYTURSJDMMMP-WVCUSYJESA-N",
  "HATU": "FKBFHOSFPRWJNV-UHFFFAOYSA-N", "EDC": "LMDZBCPBFSXMTL-UHFFFAOYSA-N", "DCC": "QOSSAOTZNIDXMA-UHFFFAOYSA-N",
  "HOBt": "ASOKPJOREAFHNY-UHFFFAOYSA-N", "TBAF": "FPGGTKZVZWFYPV-UHFFFAOYSA-M", "TBSCl": "BCNZYOJHNLTNEZ-UHFFFAOYSA-N",
  "PCC": "LEHBURLTIWGHEM-UHFFFAOYSA-N", "Dess-Martin periodinane": "NKLCNNUWBJBICK-UHFFFAOYSA-N",
  "Grubbs catalyst": "PNPBGYBHLCEVMK-UHFFFAOYSA-L", "Wilkinson's catalyst": "IXAYKDDZKIZSPV-UHFFFAOYSA-M",
  "Et3N·HCl": "ILWRPSCZWQJDMK-UHFFFAOYSA-N", "TEMPO": "QYTDEUPAUMOIOP-UHFFFAOYSA-N",
  "NaN3": "PXIPVTKHYLBLMZ-UHFFFAOYSA-N", "KMnO4": "VZJVWSHVAAUDKD-UHFFFAOYSA-N",
};
let right = 0;
const wrong: string[] = [];
const t0 = performance.now();
for (const [name, want] of Object.entries(WANT)) {
  const smiles = nameToSmiles(name), got = smiles && keyOf(smiles);
  if (got === want) right++;
  else wrong.push(`${name}: ${got ?? "no structure"}`);
}
const ms = (performance.now() - t0) / Object.keys(WANT).length;
if (wrong.length) console.log(`wrong: ${wrong.join("; ")}`);
console.log(`names.check: ${right}/${Object.keys(WANT).length} common names give the right structure (${ms.toFixed(1)} ms each with layout); ${entries.length} table entries read`);
assert.equal(Object.keys(WANT).length, 200);
assert.equal(wrong.length, 0);

// ——— The user's own dictionary (ChemDraw's Structure > Add Structure to Dictionary) ———
// A structure drawn and named by the user (here a sulfonamide no table has, as "Cat-7"), kept with its SMILES and
// InChI as Add to Dictionary keeps it. The name then reads in Name to Structure (any case, spaces or hyphens), in
// mixtures, completes in the library's search and the command palette (namesStarting), and names the structure when
// it is drawn (abbreviationOf, as the Structure panel shows an abbreviation).
{
  const { cleanOwnName, mergeOwnNames, ownName, ownNamesFile, readOwnNamesFile, renameOwnName, setOwnNames, withOwnName, withoutOwnName, MOST_OWN_NAMES } = await import("./names.ts");
  const cat = "Cc1ccc(cc1)S(=O)(=O)NC1CCCCC1", catInchi = inchi(cat)!;
  assert.equal(nameToSmiles("Cat-7"), undefined, "not a name before it is added");
  assert.equal(abbreviationOf(catInchi), undefined);
  let mine = withOwnName([], { name: "  Cat-7 \u0007", smiles: cat, inchi: catInchi });
  assert.deepEqual(mine, [{ name: "Cat-7", smiles: cat, inchi: catInchi }], "the name is cleaned");
  setOwnNames(mine);
  for (const typed of ["Cat-7", "cat 7", "CAT7"]) assert.equal(nameToSmiles(typed), cat, typed);
  assert.equal(ownName("cat7")?.name, "Cat-7");
  assert.equal(namesStarting("ca", 3)[0], "Cat-7", "first in the search and the command palette");
  assert.ok(namesStarting("ca", 3).length <= 3);
  assert.equal(abbreviationOf(catInchi), "Cat-7", "a drawn Cat-7 is named");
  assert.deepEqual(partKeys(nameToSmiles("Cat-7 and water") ?? ""), partKeys(`${cat}.O`), "in a mixture");
  // A name of the user's reads first: their THF is theirs, until they remove it.
  mine = withOwnName(mine, { name: "THF", smiles: "C1CCCO1C", inchi: inchi("C1CCCO1C") });
  setOwnNames(mine);
  assert.equal(nameToSmiles("THF"), "C1CCCO1C");
  assert.equal(abbreviationOf(inchi("C1CCOC1")), "THF", "oxolane is still THF");
  // The same name again replaces its entry (Add to Dictionary asks first).
  mine = withOwnName(mine, { name: "cat-7", smiles: "CC", inchi: inchi("CC") });
  assert.equal(mine.length, 2);
  assert.equal(mine[0].smiles, "CC");
  mine = withOwnName(mine, { name: "Cat-7", smiles: cat, inchi: catInchi });
  // Settings > Dictionary: rename (not to another entry's name, not to nothing), remove.
  assert.equal(renameOwnName(mine, "Cat-7", "thf"), mine, "two entries cannot share a name");
  assert.equal(renameOwnName(mine, "Cat-7", "  "), mine);
  mine = renameOwnName(mine, "Cat-7", "Catalyst 7");
  setOwnNames(mine);
  assert.equal(nameToSmiles("Cat-7"), undefined, "the old name is gone");
  assert.equal(nameToSmiles("catalyst 7"), cat);
  assert.equal(abbreviationOf(catInchi), "Catalyst 7");
  mine = withoutOwnName(mine, "THF");
  setOwnNames(mine);
  assert.equal(nameToSmiles("THF"), nameToSmiles("oxolane"), "THF is Octet's again");
  // Export and import: a SMILES file with names. Read back, it is the same list; a file's damaged lines are left out,
  // and a name the user has keeps the user's structure.
  const file = ownNamesFile(mine);
  assert.equal(file, `${cat}\tCatalyst 7`);
  assert.deepEqual(readOwnNamesFile(file), [{ name: "Catalyst 7", smiles: cat }]);
  const from = readOwnNamesFile(["CCO\tmy ethanol", "", "CCN", "# a comment", `${"C".repeat(5000)}\tlong`, "c1ccccc1 Benzene, my  way\u0000", "CCC\tMY ETHANOL", "CCCl\tCatalyst 7"].join("\r\n"));
  assert.deepEqual(from, [{ name: "my ethanol", smiles: "CCO" }, { name: "Benzene, my way", smiles: "c1ccccc1" }, { name: "Catalyst 7", smiles: "CCCl" }]);
  const merged = mergeOwnNames(mine, from);
  assert.deepEqual([merged.added, merged.kept], [2, 1]);
  assert.equal(merged.list.find((n) => n.name === "Catalyst 7")?.smiles, cat, "the user's own stays");
  assert.equal(readOwnNamesFile(Array.from({ length: MOST_OWN_NAMES + 10 }, (_, k) => `C\tn${k}`).join("\n")).length, MOST_OWN_NAMES);
  assert.equal(cleanOwnName("a\tb\nc"), "a b c");
  // An empty dictionary: back to Octet's names alone.
  setOwnNames([]);
  assert.equal(nameToSmiles("catalyst 7"), undefined);
  assert.equal(abbreviationOf(catInchi), undefined);
  console.log("names.check: the user's own dictionary (add, read, search, recognise, rename, remove, export, import) ok");
}
