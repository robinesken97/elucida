import assert from "node:assert/strict";
import { reagentLabels } from "./elucida.ts";
const labels = reagentLabels("NaBH4 (1,5 Äq.); Pd(PPh3)4 (5 mol%), MeOH");
assert.deepEqual(labels.map(x => x.substance), ["NaBH4", "Pd(PPh3)4", "MeOH"]);
assert.deepEqual(labels.map(x => x.equiv), [1.5, .05, undefined]);
assert.equal(reagentLabels("1,2-dichloroethane").length, 1);
assert.equal(reagentLabels("catalyst (aq.)")[0].substance, "catalyst (aq.)");
console.log("elucida.check: reagent labels ok");
