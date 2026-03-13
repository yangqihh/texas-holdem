# Texas Hold'em Poker - Android APK

德州扑克单人游戏，玩家 vs AI 对手。

## 游戏特性
- 玩家 vs 2个AI对手（Alice 普通 / Bob 激进）
- 完整德州扑克规则：盲注、弃牌、跟注、加注、全押
- AI基于手牌强度和底池赔率决策
- 横屏布局，支持触屏操作
- 起始筹码 $1000

## 打包APK
推送代码到 main 分支后，工蜂CI 自动打包。完成后在 Artifacts 下载 APK。

## 本地运行（需Python 3.11/3.12 + Kivy）
```bash
pip install kivy
python main.py
```
