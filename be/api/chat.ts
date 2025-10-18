import { VercelRequest, VercelResponse } from '@vercel/node';
import Anthropic from "@anthropic-ai/sdk";
import { getSystemPrompt } from "../src/prompts";
import { TextBlock } from "@anthropic-ai/sdk/resources";

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Method not allowed' });
  }

  try {
    const { messages } = req.body;
    
    const response = await anthropic.messages.create({
      messages: messages,
      model: 'claude-3-5-haiku-20241022',
      max_tokens: 8000,
      system: getSystemPrompt()
    });

    console.log(response);

    res.json({
      response: (response.content[0] as TextBlock)?.text
    });
  } catch (error) {
    console.error('Error:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
}
