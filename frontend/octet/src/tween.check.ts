// Run: node src/tween.check.ts. Fails loudly if a glide (Clean Up, Rotate 180°, Flip, Align: FEEL-38) can lose its
// motion to the work done before it starts (decision 0024). In 1.1.1 the glide's clock was the page's animation
// timeline, which keeps the time its frame began: a Clean Up of 150 ms used up 150 ms of the 180 ms glide before its
// first frame, and on a slower computer the whole glide. Here the first frame comes late, and the glide must still
// take its whole time, start near 0 and end at 1.
import assert from "node:assert/strict";

// A browser of our own: frames run when asked, and the clock moves only when the check moves it.
let now = 0, queue: (() => void)[] = [], timeline = 0;
const g = globalThis as Record<string, unknown>;
g.performance = { now: () => now };
g.requestAnimationFrame = (f: () => void) => queue.push(f);
g.cancelAnimationFrame = () => { queue = []; };
// The effect's progress follows the animation's own current time, eased (an ease-out, as the brand's).
g.KeyframeEffect = class { timing: { duration: number }; constructor(_target: null, _frames: null, timing: { duration: number }) { this.timing = timing; } };
g.Animation = class {
  startTime: number | null = null;
  hold: number | null = null;
  effect: { timing: { duration: number } };
  constructor(effect: { timing: { duration: number } }) {
    this.effect = effect;
    const self = this;
    Object.assign(effect, { getComputedTiming: () => ({ progress: self.currentTime === null ? null : 1 - (1 - Math.min(1, self.currentTime / effect.timing.duration)) ** 3 }) });
  }
  // As the page's timeline: time moves at each frame only, and an animation played now starts at the time this frame
  // began, however long ago that was.
  get currentTime() { return this.startTime !== null ? timeline - this.startTime : this.hold; }
  set currentTime(t: number | null) { this.startTime = null; this.hold = t; }
  get playState() { return (this.currentTime ?? 0) >= this.effect.timing.duration ? "finished" : this.currentTime === null ? "idle" : "running"; }
  play() { this.startTime = timeline; }
  cancel() { this.startTime = null; this.hold = null; }
};
const frame = (at: number) => { now = at; timeline = at; const q = queue; queue = []; q.forEach((f) => f()); };

const { frames } = await import("./tween.ts");
const DURATION = 180;
for (const busy of [400, 150, 0]) {
  // A frame began at 0; the work took `busy` ms, then the glide was started.
  now = 0; timeline = 0; queue = [];
  const seen: [number, number][] = [];
  now = busy;
  frames((t) => seen.push([now, t]), { duration: DURATION, easing: "ease-out" });
  for (let t = busy + 16; queue.length && t < busy + 2000; t += 16) frame(t);
  const first = seen[0], last = seen[seen.length - 1];
  // The caller draws 0; the first step is one frame (16 ms of 180) into the glide, eased.
  assert.ok(first[1] > 0 && first[1] < 0.5, `after ${busy} ms of work the glide's first step is early in it, not at ${first[1].toFixed(2)}`);
  assert.equal(last[1], 1, "the glide ends at 1");
  assert.ok(last[0] - first[0] >= DURATION - 16, `after ${busy} ms of work the glide still takes ${DURATION} ms (took ${last[0] - first[0]})`);
  assert.ok(seen.length >= 10, `after ${busy} ms of work the glide still has its frames (${seen.length})`);
  assert.ok(seen.every(([, t], k) => k === 0 || t >= seen[k - 1][1]), "the glide only goes forward");
}
// Frames that take long (a very large drawing on a slow computer: 120 ms each) make the motion longer, never a jump:
// at least LEAST_FRAMES frames, each at most 1/LEAST_FRAMES of the way on.
const { LEAST_FRAMES } = await import("./tween.ts");
{
  now = 0; timeline = 0; queue = [];
  const seen: [number, number][] = [];
  frames((t) => seen.push([now, t]), { duration: DURATION, easing: "ease-out" });
  for (let t = 120; queue.length && t < 10000; t += 120) frame(t);
  assert.ok(seen.length >= LEAST_FRAMES, `slow frames: the glide still has ${LEAST_FRAMES} frames (${seen.length})`);
  assert.ok(seen.slice(0, -1).every(([, t]) => t < 1) && seen[seen.length - 1][1] === 1, "slow frames: it ends at 1, and only at the end");
}
// Stopped, it draws no more frames.
queue = [];
const stop = frames(() => {}, { duration: DURATION, easing: "ease-out" });
stop();
assert.equal(queue.length, 0, "a stopped glide asks for no more frames");

// Every glide goes through this clock: no motion between two drawings keeps its own (decision 0024).
const { readdirSync, readFileSync } = await import("node:fs");
for (const f of readdirSync(new URL(".", import.meta.url)).filter((x) => /\.tsx?$/.test(x) && !x.endsWith(".check.ts") && x !== "tween.ts")) {
  const text = readFileSync(new URL(`./${f}`, import.meta.url), "utf8");
  assert.ok(!/new Animation\(new KeyframeEffect\(null/.test(text), `${f} makes a motion clock of its own: use tween (motion.tsx)`);
}
console.log("tween.check: ok");
