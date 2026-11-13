// The later template sets, which library.ts loadMore imports. A static import, as Vite's dev server keeps the
// attributes of a dynamic import() and serves the JSON file as a script, which the webview then refuses.
export { default } from "./library-more.json" with { type: "json" };
