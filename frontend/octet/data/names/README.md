# Name to Structure's dictionary

`dictionary.tsv.gz` holds common, trivial, German and trade names, CAS registry numbers and InChIKeys of chemical
compounds, each with its structure. Name to Structure reads it after OPSIN and Octet's own tables (decision 0015).
`scripts/build-dictionary.ts` builds it from Wikidata, read on 27 October 2026.

Wikidata's data is under CC0 1.0 (no rights reserved). `NOTICE.txt` names the source.

## What goes in

- Compounds with a SMILES (P233 or P2017) and an article in one of ten Wikipedias (English, German, French,
  Japanese, Spanish, Italian, Russian, Chinese, Polish and Dutch): the compounds chemists name.
- For each: its English and German labels and aliases, the English name of each brand with it as its one active
  ingredient (P3781), its CAS numbers (P231, check digit checked) and the InChIKey of its structure. The structure is
  the isomeric SMILES where there is one, chosen to match Wikidata's InChIKey (P235).
- Names spelt with Greek letters or umlauts also go in spelt out (alpha-pinene, Essigsaeure).

## What is left out, and how PubChem decides

- Molecular formulas (C6H6 has more than one structure), formulas with charges or subscripts, atomic numbers,
  SMILES, InChI, InChIKeys, CAS, EC and UNII numbers, and names over 80 characters.
- Names in `src/common.ts` and `src/drugs.ts` (asked first).
- Names OPSIN reads as the same compound. The compound's label stays for spelling suggestions only.
- Names OPSIN reads as a compound with other bonds: where PubChem's compound for the name has Wikidata's bonds and
  not OPSIN's, the name stays, marked to be read before OPSIN. Otherwise OPSIN keeps it, and always for a compound
  with a metal or a bare bracket atom ([B]), which OPSIN draws as Octet draws them (sec-butyllithium bonded).
- SMILES with a CXSMILES part: Name to Structure joins structures with "." for salts and lists.
- Names easily meant as something else (a code of up to eight capitals and digits, any name of up to five
  characters, an English word or its plural: "TEN", "salt", "beans"): kept only where PubChem gives the same
  compound for the name (or its salt or parent).
- A name or CAS number that two compounds share stays with the one PubChem gives for it, or with neither.

## Size and agreement (27 October 2026)

- 28,880 compounds, 67,602 names (2,208 of them read before OPSIN), 27,031 CAS numbers, an InChIKey for each, and
  names OPSIN reads kept for suggestions. 4.05 MB of text, 1.63 MB gzipped.
- Of 29,227 compounds Wikidata gave, 106 had no SMILES Indigo reads and 207 had SMILES that disagree with their own
  InChIKey; those are left out.
- 4,940 names OPSIN reads as another compound went to PubChem; 2,215 are read from the dictionary first. 7,911
  names easily meant as something else went to PubChem; 5,676 stay. 322 names two compounds share went to PubChem;
  231 stay with one compound.
- Check (`--check 200`): of 200 random names PubChem knows (72 more it does not know were skipped), 181 give
  PubChem's structure exactly, 9 the same compound with other stereo, 6 the same compound as a salt where the other
  has the parent (or the reverse), and 4 a different tautomer (three tetracyclines and epacadostat, drawn as keto or
  enol forms). None is another compound.

## Format

UTF-8 text, gzipped. One compound a line, tab-separated: SMILES; names, `|` between, a name OPSIN misreads marked
`!`; CAS numbers, `|` between; InChIKey; names OPSIN reads, for suggestions only, `|` between.

## Rebuild

    node scripts/build-dictionary.ts <cache directory> --check 200

The cache directory (outside the repository) keeps every answer from Wikidata and PubChem, so a second run asks
neither again. A first run takes about an hour, most of it PubChem's limit of five requests a second. `--check`
compares random names with PubChem's structure for each.
