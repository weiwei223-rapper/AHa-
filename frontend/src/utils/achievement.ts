export type LoginMeta = {
  lastLoginDate: string;
  consecutiveLoginDays: number;
  totalLoginDays: number;
};

export type AchievementItem = {
  key: string;
  category: 'video' | 'quiz' | 'login';
  title: string;
  description: string;
  points: number;
  threshold: number;
  unlocked: boolean;
  progress: string;
  badgeImage: string;
};

const STORAGE_KEYS = {
  loginMeta: 'learningLoginMeta',
  unlockedAchievements: 'learningAchievements',
  achievementPoints: 'learningAchievementPoints',
  videoCount: 'learningVideoCount', // 新增：用來記錄影片總數
};

const parseJson = <T>(value: string | null): T | null => {
  if (!value) return null;
  try {
    return JSON.parse(value) as T;
  } catch {
    return null;
  }
};

export const getTodayDateString = (): string => {
  return new Date().toISOString().slice(0, 10);
};

export const getYesterdayDateString = (): string => {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  return yesterday.toISOString().slice(0, 10);
};

export const loadLoginMeta = (): LoginMeta => {
  const raw = localStorage.getItem(STORAGE_KEYS.loginMeta);
  const stored = parseJson<LoginMeta>(raw);
  return {
    lastLoginDate: stored?.lastLoginDate || '',
    consecutiveLoginDays: stored?.consecutiveLoginDays || 0,
    totalLoginDays: stored?.totalLoginDays || 0,
  };
};

export const saveLoginMeta = (meta: LoginMeta): void => {
  localStorage.setItem(STORAGE_KEYS.loginMeta, JSON.stringify(meta));
};

export const updateLoginMetaForToday = (): LoginMeta => {
  const today = getTodayDateString();
  const yesterday = getYesterdayDateString();
  const current = loadLoginMeta();

  if (current.lastLoginDate === today) {
    return current;
  }

  const consecutiveLoginDays = current.lastLoginDate === yesterday ? current.consecutiveLoginDays + 1 : 1;
  const totalLoginDays = current.lastLoginDate === today ? current.totalLoginDays : current.totalLoginDays + 1;
  const nextMeta: LoginMeta = {
    lastLoginDate: today,
    consecutiveLoginDays,
    totalLoginDays,
  };
  saveLoginMeta(nextMeta);
  return nextMeta;
};

// 新增：讀取目前影片數量
export const loadVideoCount = (): number => {
  const raw = localStorage.getItem(STORAGE_KEYS.videoCount);
  const stored = parseJson<number>(raw);
  return typeof stored === 'number' ? stored : 0;
};

// 新增：更新影片數量（傳入增加的數量，預設為加 1）
export const updateVideoCount = (addCount: number = 1): number => {
  const current = loadVideoCount();
  const next = current + addCount;
  localStorage.setItem(STORAGE_KEYS.videoCount, JSON.stringify(next));
  return next;
};

export const loadUnlockedAchievementKeys = (): string[] => {
  const raw = localStorage.getItem(STORAGE_KEYS.unlockedAchievements);
  const stored = parseJson<string[]>(raw);
  return Array.isArray(stored) ? stored : [];
};

export const saveUnlockedAchievementKeys = (keys: string[]): void => {
  localStorage.setItem(STORAGE_KEYS.unlockedAchievements, JSON.stringify(keys));
};

export const loadAchievementPoints = (): number => {
  const raw = localStorage.getItem(STORAGE_KEYS.achievementPoints);
  const stored = parseJson<number>(raw);
  return typeof stored === 'number' ? stored : 0;
};

export const saveAchievementPoints = (points: number): void => {
  localStorage.setItem(STORAGE_KEYS.achievementPoints, JSON.stringify(points));
};

export const addAchievementPoints = (points: number): number => {
  const current = loadAchievementPoints();
  const next = current + points;
  localStorage.setItem(STORAGE_KEYS.achievementPoints, JSON.stringify(next));
  return next;
};

const quizMilestones = [1, 5, 15, 30, 50, 100] as const;
const videoMilestones = [1, 5, 10] as const;

const specialQuizTitles: Record<number, string> = {
  1: '學習啟動徽章',
  15: '學習新手',
  30: '學習學員',
  50: '學習探究者',
  100: '學習對話達人',
};

const videoTitles: Record<number, string> = {
  1: '學習啟航者',
  5: '知識累積者',
  10: '精通實踐者',
};

const loginMilestones = [1, 7, 30, 60, 100] as const;
const loginTitles: Record<number, string> = {
  1: '學習報到者',
  7: '學習堅持者',
  30: '學習投入者',
  60: '學習精進者',
  100: '學習典範者',
};
const loginPoints: Record<number, number> = {
  1: 20,
  7: 30,
  30: 100,
  60: 200,
  100: 300,
};

export const buildAchievements = (params: {
  videoCount: number;
  questionCount: number;
  loginStreakDays: number;
  totalLoginDays: number;
}): AchievementItem[] => {
  const { videoCount, questionCount, loginStreakDays, totalLoginDays } = params;
  const achievements: AchievementItem[] = [];

  // 使用固定的影片里程碑，不再動態調整
  videoMilestones.forEach((threshold) => {
    achievements.push({
      key: `video-${threshold}`,
      category: 'video',
      title: videoTitles[threshold] || '教材里程碑',
      description: `完成 ${threshold} 個教材分析`,
      points: 200,
      threshold,
      unlocked: videoCount >= threshold,
      progress: `${Math.min(videoCount, threshold)}/${threshold}`,
      badgeImage: `/achievements/video-${threshold}.png`,
    });
  });

  quizMilestones.forEach((threshold) => {
    const title = specialQuizTitles[threshold] ?? '階段精進徽章';
    achievements.push({
      key: `quiz-${threshold}`,
      category: 'quiz',
      title,
      description: `完成 ${threshold} 題 AI 程式測驗`,
      points: 30,
      threshold,
      unlocked: questionCount >= threshold,
      progress: `${Math.min(questionCount, threshold)}/${threshold}`,
      badgeImage: `/achievements/quiz-${threshold}.png`,
    });
  });

  loginMilestones.forEach((threshold) => {
    achievements.push({
      key: `login-${threshold}`,
      category: 'login',
      title: loginTitles[threshold],
      description:
        threshold === 7
          ? '連續登入 7 天，維持學習節奏'
          : threshold === 1
            ? '首次開啟學習日誌'
            : `累積登入 ${threshold} 天，保持學習習慣`,
      points: loginPoints[threshold],
      threshold,
      unlocked:
        threshold === 7 ? loginStreakDays >= threshold : totalLoginDays >= threshold,
      progress: `${Math.min(threshold === 7 ? loginStreakDays : totalLoginDays, threshold)}/${threshold}`,
      badgeImage: `/achievements/login-${threshold}.png`,
    });
  });

  return achievements;
};