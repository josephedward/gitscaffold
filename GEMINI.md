## Gemini Configuration for Gitscaffold

Gitscaffold is a versatile tool designed in Go, aimed at simplifying the process of setting up new Go projects with a proper git repository structure. It automates the creation of a standardized project layout, ensuring that new projects adhere to best practices from the start.

### Key Commands

**Setup**: Initializes a new project, creating necessary directories and initializing a git repository.

**Sync**: Synchronizes project documentation with GitHub issues, converting roadmap items into actionable tasks.

**Delete-Closed**: Removes all closed issues from the GitHub repository to keep the project clean and focused.

**Enrich**: Enhances issue descriptions using AI-driven content generation, providing clearer and more detailed context for project tasks.

### Purpose

The primary purpose of Gitscaffold is to provide developers with a quick and efficient way to set up new Go projects while integrating best practices and tools. By automating repetitive tasks, Gitscaffold allows developers to focus more on writing code and less on project setup.

### Integration with Gemini

With the integration of the `google-github-actions/run-gemini-cli`, Gitscaffold leverages Google's Gemini models to further enhance its capabilities. This integration allows for automated tasks such as AI-driven issue generation and enrichment, making the tool even more powerful for project management and development workflows.
