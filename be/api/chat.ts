import { VercelRequest, VercelResponse } from '@vercel/node';
import Anthropic from '@anthropic-ai/sdk';
import { getSystemPrompt } from '../src/prompts';

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

const MODEL = 'claude-3-5-sonnet-latest';

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Method not allowed' });
  }

  const { messages } = req.body as { messages: any };

  res.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders?.();

  try {
    const stream = await anthropic.messages.stream({
      messages,
      model: MODEL,
      max_tokens: 8000,
      system: getSystemPrompt(),
    });

    const abort = () => {
      stream.controller.abort();
    };

    req.on('close', abort);
    req.on('aborted', abort);

    for await (const event of stream) {
      if (
        event.type === 'content_block_delta' &&
        event.delta.type === 'text_delta' &&
        event.delta.text
      ) {
        res.write(`data: ${JSON.stringify({ text: event.delta.text })}\n\n`);
      }
    }

    await stream.finalMessage();
    res.write('data: [DONE]\n\n');
    res.end();
  } catch (error) {
    console.error('Anthropic streaming error:', error);
    if (!res.headersSent) {
      res.status(500).json({ message: 'Internal server error' });
      return;
    }
    res.write(`event: error\ndata: ${JSON.stringify({ message: 'stream_error' })}\n\n`);
    res.end();
  }
}
