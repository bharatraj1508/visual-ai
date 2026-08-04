/**
 * Generates one MP3 per narration line and writes them to apps/web/public/vo/<id>.mp3,
 * where Remotion picks them up with staticFile(). Also writes manifest.json with each
 * clip's measured duration so scene lengths auto-fit the narration.
 *
 * Run from apps/web:
 *   yarn remotion:voiceover                 # default: free edge-tts (Microsoft neural, no key)
 *   TTS_PROVIDER=say yarn remotion:voiceover # free, offline macOS voice
 *   TTS_PROVIDER=elevenlabs yarn remotion:voiceover   # needs ELEVENLABS_API_KEY (paid voices)
 *
 * Pick a voice:  TTS_VOICE="en-US-GuyNeural" yarn remotion:voiceover
 *   edge-tts voices:  uvx edge-tts --list-voices
 *   say voices:       say -v '?'
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { ALL_FORMATS, BlobSource, Input } from "mediabunny";
import { NARRATION, VO_DIR, VOICE_ID } from "../flow/narration.ts";

type Provider = "edge" | "say" | "elevenlabs";
const provider = (process.env.TTS_PROVIDER as Provider) || "edge";

const DEFAULT_VOICE: Record<Provider, string> = {
  // multilingual neural voice — noticeably warmer & more expressive than Aria
  edge: "en-US-AvaMultilingualNeural",
  say: "Ava (Premium)",
  elevenlabs: VOICE_ID,
};
const voice = process.env.TTS_VOICE || DEFAULT_VOICE[provider];
// prosody for edge-tts — a touch faster & brighter reads as more energetic
const rate = process.env.TTS_RATE || "+8%";
const pitch = process.env.TTS_PITCH || "+8Hz";

const outDir = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "public", VO_DIR);
mkdirSync(outDir, { recursive: true });

// --- provider backends: each writes an mp3 to `out` for `text` ------------------
function viaEdge(text: string, out: string) {
  // uses Microsoft Edge's neural TTS through uvx (no install, no API key)
  execFileSync(
    "uvx",
    ["edge-tts", "--voice", voice, `--rate=${rate}`, `--pitch=${pitch}`, "--text", text, "--write-media", out],
    { stdio: ["ignore", "ignore", "inherit"] },
  );
}

function viaSay(text: string, out: string) {
  const aiff = out.replace(/\.mp3$/, ".aiff");
  execFileSync("say", ["-v", voice, "-o", aiff, text], { stdio: "inherit" });
  execFileSync("ffmpeg", ["-y", "-i", aiff, out, "-loglevel", "error"], { stdio: "inherit" });
  rmSync(aiff, { force: true });
}

async function viaElevenLabs(text: string, out: string) {
  const apiKey = process.env.ELEVENLABS_API_KEY;
  if (!apiKey) throw new Error("ELEVENLABS_API_KEY is not set");
  const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voice}`, {
    method: "POST",
    headers: { "xi-api-key": apiKey, "Content-Type": "application/json", Accept: "audio/mpeg" },
    body: JSON.stringify({
      text,
      model_id: process.env.VO_MODEL || "eleven_multilingual_v2",
      voice_settings: { stability: 0.5, similarity_boost: 0.75, style: 0.25, use_speaker_boost: true },
    }),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${await res.text()}`);
  writeFileSync(out, Buffer.from(await res.arrayBuffer()));
}

async function synth(text: string, out: string) {
  if (provider === "edge") return viaEdge(text, out);
  if (provider === "say") return viaSay(text, out);
  return viaElevenLabs(text, out);
}

async function main() {
  console.log(`→ Generating ${NARRATION.length} clips · provider=${provider} · voice=${voice}`);
  const manifest: { id: string; seconds: number }[] = [];

  for (const line of NARRATION) {
    const file = join(outDir, `${line.id}.mp3`);
    try {
      await synth(line.text, file);
    } catch (err) {
      console.error(`✖ ${line.id}: ${(err as Error).message}`);
      process.exit(1);
    }
    const input = new Input({ formats: ALL_FORMATS, source: new BlobSource(new Blob([readFileSync(file)])) });
    const seconds = await input.computeDuration();
    manifest.push({ id: line.id, seconds });
    console.log(`✓ ${line.id}.mp3  (${seconds.toFixed(2)}s)`);
  }

  writeFileSync(join(outDir, "manifest.json"), JSON.stringify(manifest, null, 2));
  console.log(`\n✔ Done. Wrote ${manifest.length} clips + manifest.json to public/${VO_DIR}/.`);
  console.log(`  Re-render:  yarn remotion:render`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
