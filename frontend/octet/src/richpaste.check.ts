// Which pasted text counts as a citation, so the caption offers to keep its formatting (richpaste.ts). The HTML
// reading needs a browser's DOMParser and is checked in the app.
import assert from "node:assert/strict";
import { citation } from "./richpaste.ts";

for (const yes of [
  "Smith, J.; Jones, K. J. Am. Chem. Soc. 2021, 143, 1234–1240.",
  "doi:10.1021/jacs.1c01234",
  "https://doi.org/10.1039/D1SC00001A",
  "A. Author et al., Nature 2020, 580, 71.",
  "Angew. Chem. Int. Ed. 2019, 58 (12), 3726",
]) assert.ok(citation(yes), yes);
for (const no of ["Ph3P, THF, 0 °C", "Compound 12", "Yield 85%, 2 steps", "10 mg in 2021"]) assert.ok(!citation(no), no);
console.log("richpaste.check: citations ok");
