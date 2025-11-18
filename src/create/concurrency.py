# 并发控制和计数器
import threading

# 全局变量申明
ZERO_SAMPLING_COUNT = 0
sampling_lock = threading.Lock()
FAILED_ATTEMPTS = 0
failed_attempts_lock = threading.Lock()
MAX_FAILED_ATTEMPTS = 100  # 最大失败次数


def get_zero_sampling_count():
    """获取零采样计数"""
    global ZERO_SAMPLING_COUNT
    with sampling_lock:
        return ZERO_SAMPLING_COUNT


def increment_zero_sampling_count():
    """增加零采样计数"""
    global ZERO_SAMPLING_COUNT
    with sampling_lock:
        ZERO_SAMPLING_COUNT += 1
        return ZERO_SAMPLING_COUNT


def get_failed_attempts():
    """获取失败尝试次数"""
    global FAILED_ATTEMPTS
    with failed_attempts_lock:
        return FAILED_ATTEMPTS


def increment_failed_attempts():
    """增加失败尝试次数"""
    global FAILED_ATTEMPTS
    with failed_attempts_lock:
        FAILED_ATTEMPTS += 1
        return FAILED_ATTEMPTS


def check_max_failed_attempts():
    """检查是否达到最大失败次数"""
    global FAILED_ATTEMPTS, MAX_FAILED_ATTEMPTS
    with failed_attempts_lock:
        return FAILED_ATTEMPTS >= MAX_FAILED_ATTEMPTS