
from thefuzz import fuzz

def find_best_issue_match(pr_title, issues):
    """
    Finds the best issue match for a given pull request title.

    Args:
        pr_title: The title of the pull request.
        issues: A list of issues, where each issue is a dictionary with at least a 'title' key.

    Returns:
        The issue that is the best match, or None if no suitable match is found.
    """
    best_match = None
    highest_score = 0
    threshold = 60  # Configurable threshold

    for issue in issues:
        score = fuzz.token_set_ratio(pr_title, issue['title'])
        if score > highest_score:
            highest_score = score
            best_match = issue

    if highest_score > threshold:
        return best_match
    else:
        return None
