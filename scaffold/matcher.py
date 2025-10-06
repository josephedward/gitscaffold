
try:
    from thefuzz import fuzz  # Preferred for accuracy/performance
except Exception:  # Fallback when thefuzz isn't installed
    from difflib import SequenceMatcher

    class _SimpleFuzz:
        @staticmethod
        def _ratio(a: str, b: str) -> int:
            return int(100 * SequenceMatcher(None, a, b).ratio())

        @staticmethod
        def token_set_ratio(a: str, b: str) -> int:
            # Basic approximation of token_set_ratio using difflib
            ta = set(a.lower().split())
            tb = set(b.lower().split())
            inter = " ".join(sorted(ta & tb))
            a_rem = " ".join(sorted(ta - tb))
            b_rem = " ".join(sorted(tb - ta))

            if not inter:
                return _SimpleFuzz._ratio(a, b)

            candidates = [
                _SimpleFuzz._ratio(inter, (inter + " " + a_rem).strip()),
                _SimpleFuzz._ratio(inter, (inter + " " + b_rem).strip()),
                _SimpleFuzz._ratio((inter + " " + a_rem).strip(), (inter + " " + b_rem).strip()),
                _SimpleFuzz._ratio(inter, inter),
            ]
            return max(candidates)

    fuzz = _SimpleFuzz()

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
