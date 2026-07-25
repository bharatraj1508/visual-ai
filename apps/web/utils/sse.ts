export interface SSEMessage {
  event: string;
  data: string;
}

/**
 * Consume a Server-Sent Events stream (the format sse-starlette emits) and
 * invoke onMessage for each `event:`/`data:` pair.
 */
export async function consumeSSE(
  stream: ReadableStream<Uint8Array>,
  onMessage: (message: SSEMessage) => void,
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let event = "message";

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("event:")) {
        event = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        onMessage({ event, data: line.slice(5).trim() });
      } else if (line === "") {
        event = "message";
      }
    }
  }
}
