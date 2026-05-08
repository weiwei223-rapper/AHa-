// 請確保安裝了 dotenv 和 @google/generative-ai
const { GoogleGenerativeAI } = require("@google/generative-ai");
require("dotenv").config({ path: './API_key.env' }); // 讀取您的 API_key.env 檔案

async function main() {
  try {
    const apiKey = process.env.AI_API_KEY;
    if (!apiKey) throw new Error("找不到 AI_API_KEY，請確認 API_key.env 檔案配置");

    const genAI = new GoogleGenerativeAI(apiKey);
    const model = genAI.getGenerativeModel({ model: 'models/gemini-3-flash-preview' });

    console.log("⏳ 傳送問題中，準備接收串流回覆...\n");

    // 使用串流方式發送請求
    const result = await model.generateContentStream("請用繁體中文簡介 AHa!! 系統的可能應用場景。");

    // 逐字印出回覆內容
    for await (const chunk of result.stream) {
      process.stdout.write(chunk.text()); // 使用 stdout.write 讓文字接續印在同一行
    }

    console.log("\n\n✅ 輸出完畢！");
    
  } catch (error) {
    console.error("❌ 發生錯誤：", error);
  }
}

main();