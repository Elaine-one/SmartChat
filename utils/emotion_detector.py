"""
情感检测模块 - 分析用户文本中的情感倾向
"""
import re
import logging
import random
from utils.config import CONFIG

# 配置日志记录
logger = logging.getLogger(__name__)

class EmotionDetector:
    """情感检测器，用于识别用户情绪并生成相应的回应"""
    
    def __init__(self):
        # 获取配置
        self.emotion_config = CONFIG.get("emotion_detection", {})
        self.enabled = self.emotion_config.get("enabled", False)
        self.keywords = self.emotion_config.get("keywords", {})
        
        # 情绪回应模板
        self.response_templates = {
            "positive": [
                "看起来您心情不错！",
                "很高兴看到您这么开心！",
                "您的好心情真是令人愉快！"
            ],
            "negative": [
                "看起来您有些不开心，希望我能帮到您。",
                "似乎您遇到了一些困扰，我会尽力提供帮助。",
                "我理解您可能感到沮丧，让我们一起解决问题。"
            ],
            "neutral": [
                "我会尽力回答您的问题。",
                "我很乐意为您提供帮助。",
                "让我看看如何回答您的问题。"
            ]
        }
        
        # 英文情绪回应模板
        self.english_response_templates = {
            "positive": [
                "You seem to be in a good mood!",
                "I'm glad to see you're happy!",
                "Your positive energy is wonderful!"
            ],
            "negative": [
                "I see you might be feeling down. I hope I can help.",
                "It seems you're facing some challenges. I'll do my best to assist.",
                "I understand you might be frustrated. Let's work through this together."
            ],
            "neutral": [
                "I'll do my best to answer your question.",
                "I'm happy to help you with that.",
                "Let me see how I can address your query."
            ]
        }
        
        # 配置日志
        logger.info(f"初始化情感检测器，启用状态: {self.enabled}")
        
    def detect_emotion(self, text):
        """检测文本中的情绪"""
        if not self.enabled or not text:
            return None
            
        # 转换为小写进行匹配
        text_lower = text.lower()
        
        # 匹配计数
        emotion_scores = {"positive": 0, "negative": 0, "neutral": 0}
        
        # 检查各类情绪关键词
        for emotion, keywords in self.keywords.items():
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text_lower):
                    emotion_scores[emotion] += 1
        
        # 添加情感符号检测
        if re.search(r'[\😊\😄\😃\😀\👍\❤️\💕\🙏\✌️\👌]', text):
            emotion_scores["positive"] += 1
        elif re.search(r'[\😢\😭\😞\😔\😣\😖\😫\😩\😠\😡\👎\💔]', text):
            emotion_scores["negative"] += 1
            
        # 添加标点符号模式检测
        exclamation_count = len(re.findall(r'!+|\！+', text))
        question_count = len(re.findall(r'\?+|\？+', text))
        
        if exclamation_count > 1:
            # 多个感叹号可能表示强烈情绪
            emotion_scores["positive"] += 0.5
            emotion_scores["negative"] += 0.5
            
        if question_count > 2:
            # 多个问号可能表示困惑或焦虑
            emotion_scores["negative"] += 0.5
            
        # 如果没有明显情绪，加强中性分数
        if max(emotion_scores.values()) == 0:
            emotion_scores["neutral"] = 1
            
        # 获取得分最高的情绪
        emotion = max(emotion_scores, key=emotion_scores.get)
        
        # 如果得分为0，返回None表示无法检测
        if emotion_scores[emotion] == 0:
            return None
            
        logger.info(f"检测到情绪: {emotion}, 得分: {emotion_scores}")
        return emotion
        
    def get_emotional_response(self, emotion, is_chinese=True):
        """获取对应情绪的回应模板"""
        if not emotion:
            return ""
            
        # 选择语言对应的模板
        templates = self.response_templates if is_chinese else self.english_response_templates
        
        # 随机选择一个模板
        emotion_templates = templates.get(emotion, templates["neutral"])
        return random.choice(emotion_templates)

# 创建全局情感检测器实例
emotion_detector = EmotionDetector() 