import { GoogleGenerativeAI } from "@google/generative-ai";

// 1. 確保環境變數存在（TypeScript 最佳實踐，避免型別報錯或執行期錯誤）
const apiKey = process.env.GEMINI_API_KEY;
if (!apiKey) {
  throw new Error("系統環境變數中找不到 GEMINI_API_KEY");
}

// 初始化 GoogleGenerativeAI
const genAI = new GoogleGenerativeAI(apiKey);

/**
 * 呼叫 AHa 助手模型
 * @param userPrompt 使用者的輸入提示詞
 * @returns AI 回傳的文字結果
 */
// 2. 定義參數型別為 string，並標明這是一個會回傳 string 的非同步函式 (Promise)
export async function askAHaAI(userPrompt: string): Promise<string> {
  try {
    // 選擇模型
    const model = genAI.getGenerativeModel({ 
      model: "gemini-1.5-flash",
      systemInstruction: "你現在是 AHa 助手...", // 貼上你在 AI Studio 測試好的指令
    });

    const result = await model.generateContent(userPrompt);
    const response = await result.response;
    return response.text();
    
  } catch (error) {
    // 3. 加上基礎的錯誤捕捉機制，方便後端除錯
    console.error("呼叫 AHa AI 時發生錯誤:", error);
    throw error;
  }
}