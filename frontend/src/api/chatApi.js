const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

/**
 * Stream a chat message via Server-Sent Events using fetch + ReadableStream.
 *
 * Decision (UI-01): EventSource is GET-only; chat needs POST with JSON body.
 * Uses fetch + ReadableStream for full control over SSE parsing.
 *
 * @param {object} params
 * @param {string} params.message - User message text
 * @param {number|null} params.project_id - Target project for vector search (null = general)
 * @param {string} params.provider - LLM provider: "gemini" | "openai" | "claude" | "ollama"
 * @param {string} params.api_key - Provider API key or Ollama base URL
 * @param {number} params.temperature - Sampling temperature (0-2)
 * @param {number} params.max_tokens - Max tokens in response
 * @param {function} params.onToken - Called with each text token string
 * @param {function} params.onDone - Called with citations array when stream completes
 * @param {function} params.onError - Called with error message string on failure
 * @returns {function} abort - Call to cancel the stream
 */
export async function streamChat({
  message,
  project_id = null,
  provider = 'gemini',
  api_key = '',
  temperature = 0.7,
  max_tokens = 2048,
  onToken,
  onDone,
  onError,
}) {
  const controller = new AbortController();

  try {
    const response = await fetch(`${BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify({ message, project_id, provider, api_key, temperature, max_tokens }),
      signal: controller.signal,
    });

    if (!response.ok) {
      let errText = '';
      try {
        errText = await response.text();
      } catch {
        errText = 'Unknown error';
      }
      onError && onError(`Request failed: ${response.status} ${errText}`);
      return () => {};
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    const processChunk = async () => {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        // Keep the last (potentially incomplete) line in the buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;

          try {
            const event = JSON.parse(jsonStr);
            if (event.error) {
              onError && onError(event.error);
            } else if (event.done) {
              onDone && onDone(event.citations || []);
            } else if (event.text !== undefined) {
              onToken && onToken(event.text);
            }
          } catch {
            // Skip malformed SSE lines — do not crash the stream
          }
        }
      }
    };

    processChunk().catch((err) => {
      if (err.name !== 'AbortError') {
        onError && onError(err.message || 'Stream read error');
      }
    });

  } catch (err) {
    if (err.name !== 'AbortError') {
      onError && onError(err.message || 'Connection failed');
    }
  }

  return () => controller.abort();
}
