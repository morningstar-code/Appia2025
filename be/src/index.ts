require("dotenv").config();
import express from "express";
import Anthropic from "@anthropic-ai/sdk";
import { BASE_PROMPT, getSystemPrompt } from "./prompts";
import { TextBlock } from "@anthropic-ai/sdk/resources";
import {basePrompt as nodeBasePrompt} from "./defaults/node";
import {basePrompt as reactBasePrompt} from "./defaults/react";
import cors from "cors";

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});
const app = express();
app.use(cors())
app.use(express.json())

app.post("/template", async (req, res) => {
    const prompt = req.body.prompt;
    
    const response = await anthropic.messages.create({
        messages: [{
            role: 'user', content: prompt
        }],
        model: 'claude-3-5-sonnet-latest',
        max_tokens: 200,
        system: "Return either node or react based on what do you think this project should be. Only return a single word either 'node' or 'react'. Do not return anything extra"
    })

    const answer = (response.content[0] as TextBlock).text; // react or node
    if (answer == "react") {
        res.json({
            prompts: [BASE_PROMPT, `Here is an artifact that contains all files of the project visible to you.\nConsider the contents of ALL files in the project.\n\n${reactBasePrompt}\n\nHere is a list of files that exist on the file system but are not being shown to you:\n\n  - .gitignore\n  - package-lock.json\n`],
            uiPrompts: [reactBasePrompt]
        })
        return;
    }

    if (answer === "node") {
        res.json({
            prompts: [`Here is an artifact that contains all files of the project visible to you.\nConsider the contents of ALL files in the project.\n\n${reactBasePrompt}\n\nHere is a list of files that exist on the file system but are not being shown to you:\n\n  - .gitignore\n  - package-lock.json\n`],
            uiPrompts: [nodeBasePrompt]
        })
        return;
    }

    res.status(403).json({message: "You cant access this"})
    return;

})

app.post("/chat", async (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
    res.setHeader('Cache-Control', 'no-cache, no-transform');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders?.();

    try {
        const messages = req.body.messages;
        const stream = await anthropic.messages.stream({
            messages,
            model: 'claude-3-5-sonnet-latest',
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
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
