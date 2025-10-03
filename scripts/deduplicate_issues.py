import subprocess
import json
import argparse
from thefuzz import fuzz

def get_open_issues():
    """Fetches all open issues from the GitHub repository."""
    command = [
        "gh",
        "issue",
        "list",
        "--state",
        "open",
        "--json",
        "number,title,body",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error fetching issues: {result.stderr}")
        return []
    return json.loads(result.stdout)

def find_duplicate_issues(issues, threshold=80):
    """Finds duplicate issues based on title and body similarity."""
    duplicates = []
    for i in range(len(issues)):
        for j in range(i + 1, len(issues)):
            issue1 = issues[i]
            issue2 = issues[j]
            title_similarity = fuzz.ratio(issue1["title"], issue2["title"])
            body_similarity = fuzz.ratio(issue1["body"], issue2["body"])
            
            if title_similarity > threshold or body_similarity > threshold:
                duplicates.append(
                    {
                        "issue1": issue1,
                        "issue2": issue2,
                        "title_similarity": title_similarity,
                        "body_similarity": body_similarity,
                    }
                )
    return duplicates

def merge_issues(issue_to_keep, issue_to_close, comment, dry_run=False):
    """Merges two issues by closing one and adding a comment to the other."""
    if dry_run:
        print(f"DRY RUN: Would close issue #{issue_to_close['number']} and add a comment to issue #{issue_to_keep['number']}.")
        return

    # Add a comment to the issue to keep
    command = [
        "gh",
        "issue",
        "comment",
        str(issue_to_keep["number"]),
        "-b",
        comment,
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error adding comment: {result.stderr}")
        return

    # Close the other issue
    command = [
        "gh",
        "issue",
        "close",
        str(issue_to_close["number"]),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error closing issue: {result.stderr}")
        return

    print(f"Successfully merged issue #{issue_to_close['number']} into #{issue_to_keep['number']}.")

def main():
    """Main function to find and merge duplicate issues."""
    parser = argparse.ArgumentParser(description="Find and merge duplicate GitHub issues.")
    parser.add_argument("--threshold", type=int, default=80, help="Similarity threshold for finding duplicates.")
    parser.add_argument("--dry-run", action="store_true", help="Show which issues would be merged without actually merging them.")
    args = parser.parse_args()

    issues = get_open_issues()
    if not issues:
        print("No open issues found.")
        return
    
    duplicates = find_duplicate_issues(issues, args.threshold)
    
    if not duplicates:
        print("No duplicate issues found.")
        return
        
    print("Potential duplicate issues found:")
    for i, dup in enumerate(duplicates):
        print(f"  [{i+1}] Issue #{dup['issue1']['number']} and #{dup['issue2']['number']}")
        print(f"    Title similarity: {dup['title_similarity']}%")
        print(f"    Body similarity: {dup['body_similarity']}%")

    if not args.dry_run:
        while True:
            try:
                selection = input("Enter the number of the duplicate pair to merge (or 'q' to quit): ")
                if selection.lower() == 'q':
                    break
                
                selection = int(selection)
                if 1 <= selection <= len(duplicates):
                    dup = duplicates[selection - 1]
                    issue1 = dup["issue1"]
                    issue2 = dup["issue2"]
                    
                    while True:
                        choice = input(f"Which issue do you want to keep? (1 for #{issue1['number']} or 2 for #{issue2['number']}): ")
                        if choice == "1":
                            issue_to_keep = issue1
                            issue_to_close = issue2
                            break
                        elif choice == "2":
                            issue_to_keep = issue2
                            issue_to_close = issue1
                            break
                        else:
                            print("Invalid choice. Please enter 1 or 2.")
                    
                    comment = f"This issue is a duplicate of #{issue_to_keep['number']}."
                    if issue_to_close["body"]:
                        comment += f"\n\nAdditional content from #{issue_to_close['number']}:\n{issue_to_close['body']}"
                    
                    merge_issues(issue_to_keep, issue_to_close, comment, args.dry_run)
                    break
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Invalid input. Please enter a number.")

if __name__ == "__main__":
    main()