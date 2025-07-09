import re
import sys
from pathlib import Path

def update_readme_with_coverage(coverage_summary_file: Path, readme_file: Path):
    """
    Updates the README.md file with the code coverage summary.
    """
    if not coverage_summary_file.exists() or coverage_summary_file.stat().st_size == 0:
        print(f"Coverage summary file not found or is empty at {coverage_summary_file}. Skipping update.")
        sys.exit(0)

    coverage_data = coverage_summary_file.read_text().strip()

    readme_content = readme_file.read_text()

    # The report will be inside a code block
    replacement = (
        "<!-- COVERAGE_START -->\n\n"
        "```text\n"
        f"{coverage_data}\n"
        "```\n\n"
        "<!-- COVERAGE_END -->"
    )

    # Use a regex to find and replace the content between the markers
    new_readme_content, count = re.subn(
        r"<!-- COVERAGE_START -->.*<!-- COVERAGE_END -->",
        replacement,
        readme_content,
        flags=re.DOTALL
    )

    if count == 0:
        print("Coverage markers not found in README.md. Aborting.")
        sys.exit(1)

    readme_file.write_text(new_readme_content)
    print(f"Successfully updated {readme_file} with coverage data.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python update_coverage.py <path_to_coverage.txt> <path_to_readme.md>")
        sys.exit(1)
    
    update_readme_with_coverage(Path(sys.argv[1]), Path(sys.argv[2]))
