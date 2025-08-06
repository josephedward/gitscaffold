use std::fs;
use std::process;

use clap::Parser;
use pulldown_cmark::{Event, Parser as MdParser};
use serde::Serialize;

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Path to Markdown file to parse
    input: String,
}

#[derive(Serialize)]
struct Node {
    event: String,
    text: Option<String>,
}

fn main() {
    let args = Args::parse();
    let content = match fs::read_to_string(&args.input) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Error reading file {}: {}", args.input, e);
            process::exit(1);
        }
    };
    let parser = MdParser::new(&content);
    let mut nodes = Vec::new();
    let mut buffer = String::new();
    for event in parser {
        match &event {
            Event::Text(text) => buffer.push_str(text),
            _ => {
                if !buffer.is_empty() {
                    nodes.push(Node {
                        event: "Text".into(),
                        text: Some(buffer.clone()),
                    });
                    buffer.clear();
                }
                let ev = match &event {
                    Event::Start(tag) => format!("Start {:?}", tag),
                    Event::End(tag) => format!("End {:?}", tag),
                    Event::Code(text) => format!("Code {{}}", text),
                    Event::Html(html) => format!("Html {{}}", html),
                    Event::SoftBreak => "SoftBreak".into(),
                    Event::HardBreak => "HardBreak".into(),
                    Event::Rule => "Rule".into(),
                    Event::FootnoteReference(name) => format!("FootnoteReference {{}}", name),
                    _ => format!("{:?}", event),
                };
                nodes.push(Node { event: ev, text: None });
            }
        }
    }
    if !buffer.is_empty() {
        nodes.push(Node {
            event: "Text".into(),
            text: Some(buffer.clone()),
        });
    }
    // Emit JSON
    match serde_json::to_string(&nodes) {
        Ok(json) => println!("{}", json),
        Err(e) => {
            eprintln!("Error serializing JSON: {}", e);
            process::exit(1);
        }
    }
}
