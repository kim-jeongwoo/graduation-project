"""
평가 지표 모듈
"""
import numpy as np


def compute_correlation(pred, gt):
    """
    Pearson correlation coefficient
    """
    pred = pred - np.mean(pred)
    gt = gt - np.mean(gt)
    
    denom = np.sqrt(np.sum(pred**2)) * np.sqrt(np.sum(gt**2))
    if denom < 1e-8:
        return 0.0
    
    return np.sum(pred * gt) / denom


def compute_mse(pred, gt):
    """
    Mean Squared Error
    """
    return np.mean((pred - gt) ** 2)


def compute_rmse(pred, gt):
    """
    Root Mean Squared Error
    """
    return np.sqrt(compute_mse(pred, gt))


def compute_r2(pred, gt):
    """
    R² (coefficient of determination)
    """
    ss_res = np.sum((gt - pred) ** 2)
    ss_tot = np.sum((gt - np.mean(gt)) ** 2)
    
    if ss_tot < 1e-8:
        return 0.0
    
    return 1 - (ss_res / ss_tot)


def compute_mae(pred, gt):
    """
    Mean Absolute Error
    """
    return np.mean(np.abs(pred - gt))
