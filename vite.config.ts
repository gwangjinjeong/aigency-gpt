import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// lovable-tagger는 선택적으로 사용
let componentTagger: any = null;
try {
  const tagger = require("lovable-tagger");
  componentTagger = tagger.componentTagger;
} catch (e) {
  // lovable-tagger가 없으면 무시
  console.log("lovable-tagger not found, skipping...");
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const plugins = [react()];

  // development 모드이고 componentTagger가 있을 때만 추가
  if (mode === 'development' && componentTagger) {
    plugins.push(componentTagger());
  }

  return {
    server: {
      host: "::",
      port: 8080,
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        }
      }
    },
    plugins,
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  };
});