// Run: node src/store.check.ts. Fails loudly if a store tells its listeners too often or too little.
import assert from "node:assert/strict";
import { store } from "./store.ts";

const s = store(1);
let told = 0;
const off = s.subscribe(() => told++);
s.set(1);
assert.equal(told, 0, "the same value changes nothing");
s.set(2);
assert.equal(s.get(), 2);
assert.equal(told, 1, "a new value tells each listener once");
off();
s.set(3);
assert.equal(told, 1, "a listener that left is not told");

// With its own test of sameness, an equal new object changes nothing.
const hover = store<{ atom?: number }>({}, (a, b) => a.atom === b.atom);
const first = hover.get();
let moves = 0;
hover.subscribe(() => moves++);
hover.set({});
assert.equal(hover.get(), first, "the value held stays");
hover.set({ atom: 4 });
assert.equal(moves, 1);
console.log("store.check: ok");
