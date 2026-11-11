import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({plugins:[react()], base:"./", define:{__FEEDBACK__:false}, optimizeDeps:{exclude:["indigo-ketcher"]}, build:{minify:false,outDir:"../../assets/octet",emptyOutDir:true,rollupOptions:{input:"embedded.html"}}});
