import React, { useState } from 'react';
import { videoAPI } from '../api';
import "./PageIndex.css";

const Tutorial = () => {
  const [expandedSeries, setExpandedSeries] = useState<number | null>(null);
  const [activeVideos, setActiveVideos] = useState<Record<number, { id: string, title: string }>>({
    0: { id: "PLRjgE3pAnTIKu2Mr1kiCanx_vnMFD97Ac", title: "阿嬤都會：Python 入門系列 (播放清單)" },
    1: { id: "PLpZ8gOBZmTy5QMSpXdhipOrccWSQd3WxI", title: "程式柴：Python 完整教學 (播放清單)" },
    2: { id: "PL7enJ2-v6SPk5vrrzV_f0QJy7bDa06vI5", title: "電腦教室：Python 與自動化應用 (播放清單)" }
  });
  const [adding, setAdding] = useState<Record<number, boolean>>({});
  const [message, setMessage] = useState<string | null>(null);

  const videoSeries = [
    {
      title: "阿嬤都會：Python 入門系列",
      author: "GrandmaCan",
      description: "最親民的 Python 教學，適合完全零基礎的初學者。用最簡單的語言讓你快速掌握程式基礎。",
      playlistId: "PLRjgE3pAnTIKu2Mr1kiCanx_vnMFD97Ac",
      category: "入門基礎",
      videos: [
        { title: "1. 環境建置", id: "jtsBrJyElHg" },
        { title: "2. 資料型態 & 變數", id: "rU4I1NQLteo" },
        { title: "3. 字串", id: "dNFI2c007Sw" },
        { title: "4. 數字", id: "eRnRi3n0gIM" },
        { title: "5. 建立一個基本計算機", id: "D7R67Hh8wLA" },
        { title: "6. 列表 lists", id: "orCsnSHc8Mo" },
        { title: "7. 元組 tuples", id: "gM-puiT5lu8" },
        { title: "8. 函式 functions", id: "4dZBM3vyxfk" },
        { title: "9. if 判斷式", id: "z3cUEOyiQIw" },
        { title: "10. 建立進階計算機", id: "xyeiZqrXMvA" },
        { title: "11. 字典 dictionaries", id: "DOWswV0CASg" },
        { title: "12. while 迴圈", id: "cZnp_HtZStg" },
        { title: "13. 猜數字遊戲", id: "aWfeDWEU6tM" },
        { title: "14. for 迴圈", id: "4KkK-8CrEz4" },
        { title: "15. 2D 列表與巢狀迴圈", id: "pEPlcN7gOVs" },
        { title: "16. 檔案讀寫", id: "uHV4V-z5c8E" },
        { title: "17. 模組 modules", id: "SV5OqR46kEM" },
        { title: "18. 類別與物件", id: "_AgguyVzt4o" },
        { title: "19. 製作測驗程式", id: "q_X4amTktHU" },
        { title: "20. 物件函式", id: "aPYZXngue28" },
        { title: "21. 繼承 inheritance", id: "JdLLacLF5Wc" }
      ]
    },
    {
      title: "程式柴：Python 完整教學 (2023)",
      author: "CodeShiba",
      description: "深入淺出的邏輯解說，並包含豐富的實戰演練與除錯技巧。涵蓋從基礎語法到進階應用的完整 61 集課程。",
      playlistId: "PLpZ8gOBZmTy5QMSpXdhipOrccWSQd3WxI",
      category: "進階實戰",
      videos: [
        { title: "1. Python 介紹 + 撰寫第一支程式 (Win)", id: "qXqWloRfBUw" },
        { title: "2. 環境準備 (Mac) + 第一支程式", id: "EkPG9vi1Ano" },
        { title: "3. 變數與資料型別", id: "3snNDFcpXZY" },
        { title: "4. 輕鬆學會型別轉換", id: "roZs4po0njw" },
        { title: "5. 輕鬆學會使用者輸入", id: "8JouYo55trA" },
        { title: "6. 輕鬆學會 Python 中的數學", id: "89jNYQ3yBiU" },
        { title: "7. If else 好簡單啊", id: "Bsp2ocHd0SA" },
        { title: "8. 簡易計算機", id: "fJhBAmON15E" },
        { title: "9. 體重轉換器", id: "d7By41Wta6A" },
        { title: "10. 溫度轉換器", id: "55pPx6K0eOk" },
        { title: "11. 輕鬆學會邏輯運算子", id: "Z04rakFc69A" },
        { title: "12. 輕鬆學習字串方法", id: "j2R9fb3kfMI" },
        { title: "13. 字串索引好簡單啊！", id: "HFomro6yubE" },
        { title: "14. Email 字串解析", id: "mOv_9xUs9zw" },
        { title: "15. 輕鬆學 f-string 格式化", id: "zGyFNeOOYeE" },
        { title: "16. 輕鬆學 while 迴圈", id: "v_8yp32ZhqQ" },
        { title: "17. 實作練習：複利計算機", id: "AnnWiCctAXw" },
        { title: "18. 輕鬆學 for 迴圈", id: "mecbdactbAQ" },
        { title: "19. 輕鬆學 巢狀迴圈", id: "3LayhRs9y5I" },
        { title: "20. 用 Python 實作碼錶", id: "VyCqpkRz8s8" },
        { title: "21. list, sets, tuple", id: "nNYTkhEeRc4" },
        { title: "22. 實作練習：購物車程式", id: "Dh4HTGg5QhI" },
        { title: "23. 字典 Dictionary 基礎", id: "FKLco0IJLcU" },
        { title: "24. 用 Python 寫一個販賣機程式", id: "feHvl8EcM8k" },
        { title: "25. 猜數字遊戲 (random)", id: "ktVwObyHxug" },
        { title: "26. 實作練習：骰子程式", id: "-BDdso4Ef2g" },
        { title: "27. 函式 function 原來那麼簡單", id: "dSgOlXQlNJk" },
        { title: "28. 函式的預設引數", id: "O6BO1TfLs5Q" },
        { title: "29. 剪刀石頭布", id: "Y56e9YomKw0" },
        { title: "30. 關鍵字引數", id: "rzZoEm0mcRI" },
        { title: "31. Python 中的 Args 與 Kwargs", id: "FC8zJAdwJrs" },
        { title: "32. Python 中的模組", id: "OAEOQeCL4GM" },
        { title: "33. 作用域 Scope", id: "87CS4wBoZ2M" },
        { title: "34. Python 中的異常處理", id: "6tr33fU4Cpo" },
        { title: "35. 檢測檔案是否存在", id: "23s7TuYGoyA" },
        { title: "36. Python 讀取檔案", id: "0sSQKITWFZ8" },
        { title: "37. Python 寫入檔案", id: "Rpr8jzwD9yo" },
        { title: "38. Python 複製文件", id: "dms6NBZ4tiY" },
        { title: "39. Python 刪除檔案", id: "0I9RD6wMd9k" },
        { title: "40. OOP 10 分鐘快速入門", id: "LQZLeYQEzkM" },
        { title: "41. Python 中的類別變數", id: "p1imcsITk1g" },
        { title: "42. Python 中的繼承", id: "L_Um_D8ZXD0" },
        { title: "43. Python 中的重寫方法", id: "rfo9scMnedI" },
        { title: "44. Python 中的方法鏈", id: "V3gyL7HqtaM" },
        { title: "45. Python 中的 super 方法", id: "K25yFPkoDZo" },
        { title: "46. Python 物件作為引數", id: "dVtrJKGG_cI" },
        { title: "47. Python 中的鴨子型別", id: "MueiRw7GMQo" },
        { title: "48. Python 獠牙運算符 :=", id: "LcuwvX_UAKc" },
        { title: "49. 將函式指派給變數", id: "rO7-Grmo2BI" },
        { title: "50. Python lambda λ", id: "xbZYS8pRZSU" },
        { title: "51. 學會排序 Sort", id: "GqU9E6PeqgM" },
        { title: "52. Python map", id: "yQ32NZ0OV7Q" },
        { title: "53. Python filter", id: "_6zPn2G79BU" },
        { title: "54. Python 列表推導式", id: "pGhMxGZYRPU" },
        { title: "55. 字典推導式", id: "M20_qbKKbFw" },
        { title: "56. 什麼是 if name == 'main'", id: "QIqMUHJiwsE" },
        { title: "57. Python zip 函式", id: "U-I8fToNEgI" },
        { title: "58. Python time 模組", id: "MYDJr0xCz4M" },
        { title: "59. 套件管理工具 pip", id: "gilozIKlfBE" },
        { title: "★ 6 小時完整版 (合集)", id: "lvH4-4iYjgs" }
      ]
    }
,
    {
      title: "電腦教室：Python 零基礎快速上手",
      author: "PAPAYA",
      description: "由專業講師帶領，著重於語法細節與實際應用案例，是打好紮實基本功的最佳選擇。",
      playlistId: "PL7enJ2-v6SPk5vrrzV_f0QJy7bDa06vI5",
      category: "紮實基礎",
      videos: [
        { title: "#01 基本簡介與安裝", id: "zD7dXqE-VVA" },
        { title: "#02 變數與資料型態", id: "eUNHOcw-2MA" },
        { title: "#03 IF 條件判斷式", id: "onrMi-D7lvY" },
        { title: "#04 List 清單(串列)", id: "8UHmhfnUIRo" },
        { title: "#05 For Loop (迴圈)", id: "uTBXt6F37_s" },
        { title: "#06 While Loop (迴圈)", id: "KnGdj1cjOlY" },
        { title: "#07 Function (函式)", id: "74Qt9Qdl3Hs" },
        { title: "#08 Dictionaries (字典)", id: "2uhs3TOmb64" },
        { title: "#09 Module (模組)", id: "I-xm8wVqO1o" },
        { title: "#10 Class (類別)", id: "AJfZvl9Hsn4" }
      ]
    }
  ];

  const handleAddVideo = async (seriesIndex: number) => {
    const video = activeVideos[seriesIndex];
    if (!video || video.id.startsWith('PL')) {
      alert("請先從列表中選擇一支具體影片進行新增。");
      return;
    }

    const userId = Number(localStorage.getItem('userId'));
    if (!userId) {
      alert("請先登入系統。");
      return;
    }

    setAdding(prev => ({ ...prev, [seriesIndex]: true }));
    try {
      const videoLink = `https://www.youtube.com/watch?v=${video.id}`;
      await videoAPI.createVideo({
        video_link: videoLink,
        title: video.title,
        user_id: userId
      });
      
      setMessage(`成功新增：${video.title}`);
      setTimeout(() => setMessage(null), 3000);
    } catch (error) {
      console.error("Failed to add video:", error);
      alert("新增影片失敗，請稍後再試。");
    } finally {
      setAdding(prev => ({ ...prev, [seriesIndex]: false }));
    }
  };

  const getEmbedUrl = (seriesIndex: number) => {
    const active = activeVideos[seriesIndex];
    if (active.id.startsWith('PL')) {
      return `https://www.youtube.com/embed/videoseries?list=${active.id}`;
    }
    return `https://www.youtube.com/embed/${active.id}?autoplay=1`;
  };

  return (
    <div className="page-shell">
      {message && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          zIndex: 1000,
          background: '#2bc1f1',
          color: '#0f172a',
          padding: '12px 24px',
          borderRadius: '12px',
          fontWeight: 'bold',
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          animation: 'fadeIn 0.3s ease'
        }}>
          {message}
        </div>
      )}

      <section className="page-hero">
        <div>
          <div className="page-eyebrow">Learning Library</div>
          <h1>精選推薦教材</h1>
          <p>
            我們為您挑選了優質的 Python 教學系列。您可以點擊列表中的教材直接觀看，並點擊「新增」按鈕將其收藏至您的教材庫。
          </p>
        </div>
      </section>

      <section style={{ display: 'grid', gap: '30px', marginTop: '20px' }}>
        {videoSeries.map((series, index) => (
          <div key={index} className="panel-card" style={{ gap: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '15px' }}>
              <div style={{ flex: '1', minWidth: '300px' }}>
                <span className="page-eyebrow" style={{ color: '#2bc1f1' }}>{series.category}</span>
                <h2 style={{ margin: '5px 0', color: 'white' }}>{series.title}</h2>
                <p style={{ color: '#94a3b8', margin: '5px 0 15px 0' }}>講師：{series.author}</p>
                <p style={{ color: '#cbd5e1', lineHeight: '1.6', marginBottom: '20px' }}>{series.description}</p>
                
                <div style={{ marginBottom: '20px' }}>
                  <button 
                    onClick={() => setExpandedSeries(expandedSeries === index ? null : index)}
                    style={{ 
                      width: 'auto', 
                      padding: '8px 16px', 
                      fontSize: '14px',
                      background: expandedSeries === index ? '#2bc1f1' : 'transparent',
                      color: expandedSeries === index ? '#0f172a' : '#2bc1f1',
                      border: '1px solid #2bc1f1',
                      marginRight: '10px'
                    }}
                  >
                    {expandedSeries === index ? '收起列表 ▲' : '查看影片列表 ▼'}
                  </button>
                  <button 
                    onClick={() => {
                      setActiveVideos(prev => ({ 
                        ...prev, 
                        [index]: { id: series.playlistId, title: `${series.title} (播放清單)` } 
                      }));
                    }}
                    style={{ 
                      width: 'auto', 
                      padding: '8px 16px', 
                      fontSize: '14px',
                      background: 'transparent',
                      color: '#94a3b8',
                      border: '1px solid #334155'
                    }}
                  >
                    重置播放器 ↺
                  </button>
                </div>

                {expandedSeries === index && (
                  <div style={{ 
                    background: 'rgba(0,0,0,0.2)', 
                    borderRadius: '12px', 
                    padding: '15px',
                    maxHeight: '300px',
                    overflowY: 'auto',
                    border: '1px solid rgba(255,255,255,0.05)'
                  }}>
                    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                      {series.videos.map((video, vIdx) => (
                        <li 
                          key={vIdx} 
                          onClick={() => {
                            setActiveVideos(prev => ({ 
                              ...prev, 
                              [index]: { id: video.id, title: video.title } 
                            }));
                          }}
                          style={{ 
                            padding: '10px 12px', 
                            borderBottom: vIdx === series.videos.length - 1 ? 'none' : '1px solid rgba(255,255,255,0.05)',
                            color: activeVideos[index].id === video.id ? '#2bc1f1' : '#94a3b8',
                            fontSize: '0.9rem',
                            cursor: 'pointer',
                            borderRadius: '6px',
                            background: activeVideos[index].id === video.id ? 'rgba(43, 193, 241, 0.1)' : 'transparent',
                            transition: 'all 0.2s ease'
                          }}
                        >
                          ▶ {video.title}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div style={{ flex: '1.2', minWidth: '320px' }}>
                <div style={{ 
                  position: 'relative', 
                  paddingBottom: '56.25%', 
                  height: 0, 
                  overflow: 'hidden', 
                  borderRadius: '15px',
                  border: '1px solid rgba(43, 193, 241, 0.2)',
                  boxShadow: '0 10px 30px rgba(0,0,0,0.3)',
                  marginBottom: '15px'
                }}>
                  <iframe
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: '100%',
                      border: 0
                    }}
                    src={getEmbedUrl(index)}
                    title={activeVideos[index].title}
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                    allowFullScreen
                  ></iframe>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ color: '#94a3b8', fontSize: '0.85rem', maxWidth: '70%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    正在播放：{activeVideos[index].title}
                  </div>
                  <button
                    disabled={adding[index] || activeVideos[index].id.startsWith('PL')}
                    onClick={() => handleAddVideo(index)}
                    style={{
                      padding: '8px 20px',
                      background: activeVideos[index].id.startsWith('PL') ? '#1e293b' : '#2bc1f1',
                      color: activeVideos[index].id.startsWith('PL') ? '#475569' : '#0f172a',
                      border: 'none',
                      borderRadius: '8px',
                      fontWeight: 'bold',
                      cursor: activeVideos[index].id.startsWith('PL') ? 'not-allowed' : 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    {adding[index] ? '處理中...' : '✚ 新增至教材庫'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </section>
    </div>
  );
};

export default Tutorial;
