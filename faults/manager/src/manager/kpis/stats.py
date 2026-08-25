import numpy as np

from scipy.stats import mannwhitneyu

def has_effect(
    baseline,
    compare,
    alpha=0.05,
):
    baseline = np.array(baseline)
    compare = np.array(compare)

    res = mannwhitneyu(
        baseline,
        compare,
        alternative="less",
    )

    return res.pvalue < alpha

    # statistical_effect = p_value < alpha

    # practical_effect = (
    #     abs(relative_change) >= min_relative_change
    #     and abs(absolute_change) >= min_absolute_change
    # )

    # return {
    #     "effect": statistical_effect and practical_effect,
    #     "p_value": p_value,
    #     "baseline": baseline_value,
    #     "compare": compare_value,
    #     "absolute_change": absolute_change,
    #     "relative_change": relative_change,
    # }
