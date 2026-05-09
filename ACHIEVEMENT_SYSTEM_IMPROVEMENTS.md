# 成就系统改进方案

## 问题分析

原有成就系统存在的问题：
1. **前端未同步后端数据**：前端有 `updateVideoCount()` 函数但从未被调用
2. **使用本地存储**：仅从 localStorage 读取影片数量，与后端数据不同步
3. **缺少初始化逻辑**：用户首次登陆时没有从后端获取影片计数

## 改进方案

### 修改文件：Profile.tsx

#### 1. **导入 userAPI（获取后端统计数据）**
```typescript
import { userAPI } from "../api";
import { updateVideoCount } from "../utils/achievement";
```

#### 2. **初始化时从后端获取影片计数**
- 在组件挂载时，调用 `/users/{userId}/stats` API
- 获取 `video_count`（所有上传的视频数）
- 同步到 localStorage 和组件状态

#### 3. **监听视频上传事件**
当 `videoUploaded` 事件触发时：
- 从后端 API 获取最新统计信息
- 使用 `updateVideoCount()` 更新 localStorage 差值
- 调用 `refreshAchievements()` 重新计算成就

### 修改文件：Video.tsx

#### 1. **视频分析完成后触发事件**
在 `handleAnalyze()` 中，分析完成后发送 `videoUploaded` 事件
- 这样即使没有上传新视频，分析完成也能触发成就检查

## 成就与视频数量的关系

### 影片里程碑
| 里程碑 | 成就名称 | 点数 | 触发条件 |
|------|--------|------|--------|
| 1 部 | 学习启航者 | 200 | 上传 1 部影片 |
| 5 部 | 知识累积者 | 200 | 上传 5 部影片 |
| 10 部 | 精通实践者 | 200 | 上传 10 部影片 |

### 测验里程碑
| 里程碑 | 成就名称 | 点数 | 触发条件 |
|------|--------|------|--------|
| 1 题 | 学习启动徽章 | 30 | 完成 1 题测验 |
| 5 题 | 学习新手 | 30 | 完成 5 题测验 |
| 15 题 | 学习学员 | 30 | 完成 15 题测验 |
| 30 题 | 学习探究者 | 30 | 完成 30 题测验 |
| 50 题 | 学习对话达人 | 30 | 完成 50 题测验 |
| 100 题 | 学习对话达人 | 30 | 完成 100 题测验 |

### 登录里程碑
| 里程碑 | 成就名称 | 点数 | 触发条件 |
|------|--------|------|--------|
| 1 天 | 学习报到者 | 20 | 首次登陆 |
| 7 天 | 学习坚持者 | 30 | 连续登入 7 天 |
| 30 天 | 学习投入者 | 100 | 累积登入 30 天 |
| 60 天 | 学习精进者 | 200 | 累积登入 60 天 |
| 100 天 | 学习典范者 | 300 | 累积登入 100 天 |

## 数据同步流程

```
User Action (Upload/Analyze Video)
    ↓
Video.tsx sends 'videoUploaded' event
    ↓
Profile.tsx handleVideoUploaded()
    ↓
userAPI.getStats(userId) [Backend API]
    ↓
Backend returns:
- video_count (all uploaded videos)
- analyzed_video_count (analyzed videos)
- completed_quizzes
- average_accuracy
    ↓
updateVideoCount() updates localStorage
    ↓
setVideoCount() updates component state
    ↓
refreshAchievements() recalculates achievements
    ↓
User sees updated progress bars and unlocked achievements
```

## 测试检查清单

### 基础测试
- [ ] 上传一个新视频后，进度条更新
- [ ] 上传 5 个视频后，"知识累积者"成就解锁
- [ ] 上传 10 个视频后，"精通实践者"成就解锁
- [ ] 分析视频完成后，成就页面自动刷新
- [ ] 页面刷新后，成就进度保持一致

### 数据同步测试
- [ ] 删除视频后，成就进度相应减少
- [ ] localStorage 与后端数据一致
- [ ] 多浏览器标签页情况下，数据同步正确

### 错误处理测试
- [ ] 后端 API 不可用时，使用本地 localStorage 降级
- [ ] 网络错误时，显示适当的错误提示

## 相关代码文件位置

| 文件 | 用途 |
|-----|------|
| `frontend/src/pages/Profile.tsx` | 成就总览页面（主要改动） |
| `frontend/src/pages/Video.tsx` | 视频管理页面（事件触发改动） |
| `frontend/src/utils/achievement.ts` | 成就计算逻辑 |
| `frontend/src/api.ts` | API 定义（userAPI.getStats） |
| `backend/main.py` | 后端统计端点 `/users/{user_id}/stats` |
| `backend/schema.py` | UserStatsResponse 数据结构 |

## 设计决策说明

### 为什么使用 video_count 而不是 analyzed_video_count？

成就描述为"完成 X 部影片上傳"，这指的是**上传**的行为，而不是**分析完成**的状态。

- **video_count**：用户上传的所有视频数（包括未分析的）
- **analyzed_video_count**：已分析且生成了 outline 的视频数

当前实现使用 `video_count`，这样用户上传视频后立即可以获得成就，而不需要等待系统分析完成。

如果需要改为等待分析完成后再解锁成就，只需将代码中的 `stats.video_count` 改为 `stats.analyzed_video_count`。
