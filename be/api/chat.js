"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.default = handler;
const sdk_1 = __importDefault(require("@anthropic-ai/sdk"));
const prompts_1 = require("../src/prompts");
const anthropic = new sdk_1.default({
    apiKey: process.env.ANTHROPIC_API_KEY,
});
function handler(req, res) {
    return __awaiter(this, void 0, void 0, function* () {
        var _a;
        if (req.method !== 'POST') {
            return res.status(405).json({ message: 'Method not allowed' });
        }
        try {
            const { messages } = req.body;
            const response = yield anthropic.messages.create({
                messages: messages,
                model: 'claude-3-5-sonnet-20241022',
                max_tokens: 8000,
                system: (0, prompts_1.getSystemPrompt)()
            });
            console.log(response);
            res.json({
                response: (_a = response.content[0]) === null || _a === void 0 ? void 0 : _a.text
            });
        }
        catch (error) {
            console.error('Error:', error);
            res.status(500).json({ message: 'Internal server error' });
        }
    });
}
