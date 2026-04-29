// To run this code you need to install the following dependencies:
// npm install @google/generative-ai mime
// npm install -D @types/node

import {
  GoogleGenerativeAI,
} from '@google/generative-ai';
import { config } from 'dotenv';

async function main() {
  config({ path: './API_key.env' });
  const apiKey = process.env.AI_API_KEY;
  if (!apiKey) {
    throw new Error('AI_API_KEY is not set');
  }
  const genAI = new GoogleGenerativeAI(apiKey);
  const model = genAI.getGenerativeModel({
    model: 'models/gemini-3-flash-preview',
  });
  const contents = [
    {
      role: 'user',
      parts: [
        {
          text: `INSERT_INPUT_HERE`,
        },
      ],
    },
  ];

  const response = await model.generateContentStream({
    contents,
  });
  for await (const chunk of response.stream) {
    if (chunk.text) {
      console.log(chunk.text);
    }
  }
}

main();


