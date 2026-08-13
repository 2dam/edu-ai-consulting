import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

// 빌드 전에 public/ads.txt 의 __ADSENSE_PUBLISHER_ID__ 플레이스홀더를
// 실제 VITE_ADSENSE_PUBLISHER_ID 로 치환한다.
// 미설정/플레이스홀더면 주석 처리된 안내문으로 둔다(승인 전 안전 기본값).
const id = process.env.VITE_ADSENSE_PUBLISHER_ID || "";
const out = resolve(process.cwd(), "public/ads.txt");
const real = id && !id.startsWith("pub-0") ? id : "";

let body;
if (real) {
  body = `google.com, ${real}, DIRECT, f08c47fec0942fa0\n`;
} else {
  body = `# AdSense 게시자 ID(VITE_ADSENSE_PUBLISHER_ID)가 설정되지 않았습니다.\n# AdSense 가입 후 .env.production 에 실제 pub-XXXXXXXXXXXXXXXX 값을 입력하세요.\n`;
}
writeFileSync(out, body, "utf8");
console.log(`[ads.txt] publisherId=${real || "(unset)"}`);
