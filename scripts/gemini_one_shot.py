import os
import sys
import argparse
import logging

try:
    import google.generativeai as genai
except ImportError:
    genai = None
    print("Error: google-generativeai is not installed. Please install it using 'pip install google-generativeai'.")
    sys.exit(1)

# Add the parent directory to the Python path so we can import scaffold modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scaffold.cli import get_config_file, load_config, setup_logging

def invoke_gemini_one_shot(prompt: str, model_name: str, api_key: str) -> str:
    """Invokes the Gemini API with a given prompt and returns the response."""
    if genai is None:
        raise ImportError("google-generativeai is not installed.")

    if not api_key:
        raise ValueError("Gemini API key was not provided.")

    genai.configure(api_key=api_key)
    logging.info(f"Using Gemini model '{model_name}' for one-shot invocation.")
    model = genai.GenerativeModel(model_name)

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logging.error(f"Gemini API call failed: {e}")
        raise RuntimeError(f"Gemini API call failed: {e}") from e

def main():
    parser = argparse.ArgumentParser(description="Run Gemini in one-shot mode with auto-approval.")
    parser.add_argument("--prompt", required=True, help="The prompt to send to Gemini.")
    parser.add_argument("--model", default="gemini-pro", help="The Gemini model to use (e.g., gemini-pro).")
    parser.add_argument("--auto-approve", action="store_true", help="Automatically approve Gemini's response.")
    parser.add_argument("--config-file", default=None, help="Path to the configuration file.")
    parser.add_argument("--api-key", default=None, help="Gemini API Key. Overrides config file and environment variable.")

    args = parser.parse_args()

    # Setup logging
    setup_logging()

    # Load configuration
    config_file = args.config_file if args.config_file else get_config_file()
    config = load_config(config_file)

    # Determine API Key
    api_key = args.api_key or os.getenv('GOOGLE_API_KEY') or config.get('gemini', {}).get('api_key')

    if not api_key:
        print("Error: Gemini API key not found. Please provide it via --api-key, GOOGLE_API_KEY environment variable, or in your config file.")
        sys.exit(1)

    print(f"Sending prompt to Gemini model: {args.model}")
    print(f"Prompt: {args.prompt}")

    try:
        response_text = invoke_gemini_one_shot(args.prompt, args.model, api_key)

        if response_text:
            print("\n--- Gemini Response ---")
            print(response_text)

            if args.auto_approve:
                print("\nAuto-approving response.")
                # In a real scenario, you would add logic here to process/apply the response
                # For this script, we just print it.
            else:
                print("\nResponse not auto-approved. Exiting.")
        else:
            print("No response received from Gemini.")

    except (ImportError, ValueError, RuntimeError) as e:
        print(f"Error: {e}")
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()