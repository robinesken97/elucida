// Run: node src/docproperties.check.ts. Fails loudly if the document's properties (Settings > Document > Properties:
// title, author, keywords) stop being its Title, Author and Keywords annotations, stop leaving an experiment's other
// details and other annotations as they were, make a drawing an experiment page, or stop coming back through CDXML,
// CDX and .oct. A file with none keeps none.
import assert from "node:assert/strict";
import { DEFAULT_STYLE } from "./docstyle.ts";
import { PROPERTIES, detailsOf, experimentPage, withDetails } from "./experiment.ts";
import { fromCdxml, parseXml, toCdxml } from "./cdxml.ts";
import { cdxToXml, xmlToCdx } from "./cdx.ts";
import { readCdx, readOct, writeCdx, writeOct } from "./oct.ts";
import type { Mol } from "./render.ts";

const props = { title: "Aspirin, route 2", author: "Zoë Ångström", keywords: "acetylation, β-lactam, <test> & \"quotes\"" };
const guid = { keyword: "GUID", content: "0A1B" }, date = { keyword: "Date", content: "4 November 2026" };

// Read and written by keyword: the experiment's details and other annotations stay; an empty value takes its keyword out.
{
  const annotations = withDetails([guid, date, { keyword: "Title", content: "Old" }], props, PROPERTIES)!;
  assert.deepEqual(annotations, [guid, date, { keyword: "Title", content: props.title }, { keyword: "Author", content: props.author }, { keyword: "Keywords", content: props.keywords }]);
  assert.deepEqual(detailsOf(annotations, PROPERTIES), props);
  // Title and Author are an experiment page's details too, but alone they do not make a drawing from a template this
  // computer does not have an experiment page.
  assert.deepEqual(detailsOf(annotations), { title: props.title, date: "4 November 2026", author: props.author });
  assert.equal(experimentPage(undefined, "u1abc", withDetails(undefined, props, PROPERTIES)), false);
  assert.equal(experimentPage(undefined, "u1abc", annotations), true);
  assert.deepEqual(withDetails(annotations, { ...props, keywords: "" }, PROPERTIES)?.map((a) => a.keyword), ["GUID", "Date", "Title", "Author"]);
  assert.equal(withDetails(undefined, {}, PROPERTIES), undefined);
  // A value from a file is one line of 200 characters at most.
  assert.deepEqual(detailsOf([{ keyword: "Title", content: `a\nb\u0007c${"x".repeat(300)}` }], PROPERTIES), { title: `a b c${"x".repeat(195)}` });
}

// Through CDXML (ChemDraw's document annotations, so ChemDraw shows and keeps them), CDX and .oct.
{
  const m: Mol = { atoms: [{ label: "C", location: [0, 0, 0] }], bonds: [], annotations: withDetails([guid], props, PROPERTIES) };
  const cdxml = toCdxml(m, DEFAULT_STYLE);
  assert.match(cdxml, /<annotation\s+Keyword="Title"\s+Content="Aspirin, route 2"\s*\/>/);
  assert.match(cdxml, /<annotation\s+Keyword="Keywords"\s+Content="acetylation, β-lactam, &lt;test&gt; &amp; &quot;quotes&quot;"\s*\/>/);
  assert.deepEqual(detailsOf(fromCdxml(cdxml).mol.annotations, PROPERTIES), props);
  assert.deepEqual(fromCdxml(cdxml).mol.annotations?.[0], guid);
  assert.deepEqual(detailsOf(fromCdxml(cdxToXml(xmlToCdx(parseXml(cdxml)))).mol.annotations, PROPERTIES), props);
  assert.deepEqual(detailsOf(readOct(writeOct(m, DEFAULT_STYLE)).mol.annotations, PROPERTIES), props);
  assert.deepEqual(detailsOf(readOct(writeOct(m, DEFAULT_STYLE).replace(/<!--Octet[^]*$/, "")).mol.annotations, PROPERTIES), props, "the CDXML alone");
  assert.deepEqual(detailsOf(readCdx(writeCdx(m, DEFAULT_STYLE)).mol.annotations, PROPERTIES), props);
}

// A drawing with no properties (every file from before) writes and reads none.
{
  const m: Mol = { atoms: [{ label: "C", location: [0, 0, 0] }], bonds: [] };
  const cdxml = toCdxml(m, DEFAULT_STYLE);
  assert.doesNotMatch(cdxml, /<annotation/);
  assert.equal(fromCdxml(cdxml).mol.annotations, undefined);
  assert.deepEqual(detailsOf(readOct(writeOct(m, DEFAULT_STYLE)).mol.annotations, PROPERTIES), {});
}
