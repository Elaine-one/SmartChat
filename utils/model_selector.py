"""
模型选择器 - 根据查询内容智能选择最适合的模型
"""
import re
import logging
from utils.config import CONFIG

logger = logging.getLogger(__name__)

class ModelSelector:
    """智能模型选择器，根据消息内容自动选择最佳模型"""
    
    def __init__(self):
        # 获取配置
        self.algorithm_config = CONFIG.get("model_selection_algorithm", {})
        self.models_config = CONFIG.get("models", {})
        self.enabled = self.algorithm_config.get("enabled", False)
        self.features = self.algorithm_config.get("features", [])
        self.weights = self.algorithm_config.get("weights", {})
        self.thresholds = self.algorithm_config.get("thresholds", {})
        
        # 配置日志
        logger.info(f"初始化智能模型选择器，启用状态: {self.enabled}")
        
    def select_model(self, message, history=None):
        """根据消息内容和历史记录选择最佳模型"""
        # 如果未启用智能选择，返回默认模型
        if not self.enabled or not self.models_config:
            return self._get_default_model()
            
        # 如果没有提供历史记录，默认为空列表
        if history is None:
            history = []
            
        # 提取消息特征
        features = self._extract_features(message, history)
        
        # 计算每个模型的得分
        model_scores = {}
        for model_id, model_info in self.models_config.items():
            score = self._calculate_score(features, model_info)
            model_scores[model_id] = score
            
        # 记录得分
        logger.info(f"模型评分: {model_scores}")
        
        # 选择得分最高的模型
        if model_scores:
            best_model = max(model_scores.items(), key=lambda x: x[1])[0]
            logger.info(f"智能选择模型: {best_model}")
            return best_model
            
        # 如果没有计算得分，返回默认模型
        return self._get_default_model()
        
    def _extract_features(self, message, history):
        """从消息中提取特征"""
        features = {}
        
        # 提取消息长度特征
        if "message_length" in self.features:
            message_length = len(message)
            is_long = message_length > self.thresholds.get("long_message", 500)
            features["message_length"] = 1.0 if is_long else 0.5
            
        # 提取复杂度特征
        if "complexity" in self.features:
            # 使用几个简单指标评估复杂度
            word_count = len(re.findall(r'\b\w+\b', message))
            avg_word_length = sum(len(word) for word in re.findall(r'\b\w+\b', message)) / max(word_count, 1)
            special_chars = len(re.findall(r'[^a-zA-Z0-9\s\u4e00-\u9fff]', message))
            
            # 复杂度指标：词数、平均词长、特殊字符比例的加权和
            complexity = (0.4 * min(word_count / 100, 1.0) + 
                          0.3 * min(avg_word_length / 6, 1.0) + 
                          0.3 * min(special_chars / 30, 1.0))
                          
            is_complex = complexity > self.thresholds.get("high_complexity", 0.7)
            features["complexity"] = 1.0 if is_complex else 0.5
            
        # 提取语言特征
        if "language" in self.features:
            # 检测是否是中文
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', message))
            chinese_ratio = chinese_chars / max(len(message), 1)
            features["language"] = "chinese" if chinese_ratio > 0.5 else "english"
            
        return features
        
    def _calculate_score(self, features, model_info):
        """根据特征和模型信息计算得分"""
        score = 0.0
        
        # 加权计算模型得分
        if "message_length" in features and "message_length" in self.weights:
            # 长消息优先使用上下文窗口大的模型
            context_window = model_info.get("context_window", 2048)
            length_score = features["message_length"] * (context_window / 8192)
            score += self.weights["message_length"] * length_score
            
        if "complexity" in features and "complexity" in self.weights:
            # 复杂内容优先使用更大的模型
            is_complex = features["complexity"] > 0.7
            has_large_model = "max_tokens" in model_info and model_info["max_tokens"] >= 4096
            complexity_score = 1.0 if (is_complex and has_large_model) else 0.5
            score += self.weights["complexity"] * complexity_score
            
        if "language" in features and "language" in self.weights:
            # 按照描述判断模型对特定语言的支持
            description = model_info.get("description", "").lower()
            if features["language"] == "chinese" and "中文" in description:
                score += self.weights["language"] * 1.0
            elif features["language"] == "english" and "英文" in description:
                score += self.weights["language"] * 1.0
            else:
                score += self.weights["language"] * 0.5
                
        # 考虑模型优先级
        priority = model_info.get("priority", 99)  # 默认最低优先级
        priority_score = 1.0 / (priority + 1)  # 优先级越小，得分越高
        score += 0.1 * priority_score  # 优先级作为加权因子
                
        return score
        
    def _get_default_model(self):
        """获取默认模型"""
        # 尝试获取优先级最高的模型
        if self.models_config:
            # 按优先级排序
            sorted_models = sorted(
                self.models_config.items(), 
                key=lambda x: x[1].get("priority", 99)
            )
            if sorted_models:
                return sorted_models[0][0]
        
        # 如果没有配置模型，返回"qwen2.5:3b"作为默认值
        return "qwen2.5:3b"

# 创建全局模型选择器实例
model_selector = ModelSelector() 