// One narration line per scene, in the same order as FLOW_SCENES.
// `id` is the mp3 filename written to public/vo/<id>.mp3 by generate-voiceover.ts.
export type NarrationLine = { id: string; text: string };

export const NARRATION: NarrationLine[] = [
  { id: "01-intro", text: "Okay, so — this is Visual AI. And no, it's not another chatbot. It actually reads your data, and writes the whole report for you." },
  { id: "02-signup", text: "Alright, let's get you started. Honestly? It takes just a few seconds. Create your account, and you're in." },
  { id: "03-inbox", text: "Now, real quick — pop open your inbox, and confirm your email." },
  { id: "04-verified", text: "And… boom. You're verified, and your free credits are ready to roll." },
  { id: "05-credits", text: "See that? Fifty free credits, right off the bat. That's about five full reports — on us." },
  { id: "06-upload", text: "Okay, here's the fun part. Just drag in a CSV. No SQL, no Python, no setup — nothing." },
  { id: "07-ideas", text: "And in seconds, the AI reads through your data, and lines up the five reports actually worth running." },
  { id: "08-report", text: "So pick one — and watch. It writes the entire thing. The findings, a real narrative, interactive charts… all for just ten credits." },
  { id: "09-download", text: "Love it? Go ahead and grab it. Download as a PDF, or a ZIP — it's yours to keep." },
  { id: "10-outro", text: "So, yeah — stop chatting with your data, and start reading its report. Come give it a try. It's free." },
];

// ElevenLabs voice. "Rachel" is a warm, clear default; override with VO_VOICE_ID.
export const VOICE_ID = "21m00Tcm4TlvDq8ikWAM";
export const VO_DIR = "vo";
