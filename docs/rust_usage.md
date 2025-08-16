# Rust Usage

This project uses Rust for performance-critical tasks, specifically for parsing Markdown files.

## Markdown Parser

The Rust-based Markdown parser is located in the `rust/mdparser` directory. It is a small, standalone command-line application that takes a path to a Markdown file and outputs a structured representation of the document as JSON.

### Rationale

Parsing large Markdown files, such as project roadmaps, can be a bottleneck in Python. By implementing the parser in Rust, we leverage Rust's performance and safety features to significantly speed up this process.

### Integration

The Python application, specifically in `scaffold/parser.py`, invokes the compiled Rust executable as a subprocess. It passes the Markdown file path to the Rust program and captures its standard output to get the parsed data.

This approach allows us to keep the performance-sensitive code isolated while the main application logic remains in Python, benefiting from its rich ecosystem and ease of development.

### Building

To build the Rust component, you will need the Rust toolchain installed. Navigate to the `rust/mdparser` directory and run:

```bash
cargo build --release
```

The compiled binary will be located at `rust/mdparser/target/release/mdparser`.
