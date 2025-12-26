#!/usr/bin/env python3
"""
Command-line chat interface using OpenAI GPT-5 with context-based system prompts.

Usage:
    python main.py <context_key>

Example:
    python main.py parent
    python main.py child
    python main.py mentor
    python main.py friend
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Optional

import yaml
import dotenv

from openai import OpenAI


def print_char_by_char(text: str, delay: float = 0.03) -> None:
    """Print text character by character with a delay.

    Args:
        text: Text to print.
        delay: Delay between characters in seconds.
    """
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()  # Newline at the end


def load_context(config_path: Path, context_key: str) -> str:
    """Load context prompt for the given context from a YAML file.

    Args:
        config_path: Path to YAML file.
        context_key: Key to look up in context section.

    Returns:
        str: Context text, or None if not found.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If config is invalid.
    """
    if not config_path.exists():
        return None

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    contexts = config.get("context", {})
    if not isinstance(contexts, dict):
        return None

    if context_key not in contexts:
        return None

    context_data = contexts[context_key]
    if isinstance(context_data, dict):
        prompt = context_data.get("prompt", "")
    else:
        prompt = str(context_data)

    return prompt.strip() if prompt else None


def load_combined_context(analysis_path: Path, raw_path: Path, context_key: str) -> tuple[str, bool]:
    """Load and combine both psychological analysis and raw context.

    Args:
        analysis_path: Path to psychological analysis YAML.
        raw_path: Path to raw Perplexity data YAML.
        context_key: Key to look up (person's name).

    Returns:
        tuple: (combined_context, is_unknown)
            - combined_context: str with context or unknown person prompt
            - is_unknown: bool indicating if person was not found
    """
    # Load psychological analysis
    analysis = load_context(analysis_path, context_key)
    
    # Load raw context
    raw = load_context(raw_path, context_key)
    
    # If neither exists, create "unknown person" prompt
    if not analysis and not raw:
        unknown_prompt = f"""=== UNKNOWN PARTICIPANT ===

You are meeting someone who is not in our participant database.

Their identifier: {context_key}

IMPORTANT FIRST MESSAGE:
Start the conversation by saying:

"I don't have any background information about you yet. To have a meaningful conversation about change and growth, I'd love to learn about you.

Could you share:
- What are you working on right now that feels significant to you?
- What's a choice you've made recently that surprised you or others?
- What brought you here tonight?

Feel free to share as much or as little as you'd like."

AFTER THEY RESPOND:
- Listen carefully to what they share
- Ask follow-up questions to understand patterns in their choices
- Look for contradictions between what they say and what might be underneath
- Challenge them gently about their relationship to change
- Help them see themselves from a new angle

Approach this as a skilled facilitator would - curious, perceptive, and focused on helping them articulate concrete change they will make."""
        
        return unknown_prompt, True
    
    # Build combined context for known person
    parts = []
    
    if analysis:
        parts.append("=== PSYCHOLOGICAL ANALYSIS ===")
        parts.append("This is a synthesized psychological and social analysis of the person:")
        parts.append("")
        parts.append(analysis)
        parts.append("")
    
    if raw:
        parts.append("=== RAW CONTEXT DATA ===")
        parts.append("Below is additional raw information about the person's background:")
        parts.append("")
        parts.append(raw)
    
    return "\n".join(parts), False


def chat_loop(client: OpenAI, system_prompt: str, context_key: str, debug: bool = False) -> None:
    """Run interactive chat loop with GPT-5.

    Args:
        client: OpenAI client instance.
        system_prompt: System prompt to initialize conversation.
        context_key: Context name for display purposes.
        debug: Show debug information about conversation history.
    """
    # Initialize conversation with system prompt (includes context about the person)
    messages = [{"role": "system", "content": system_prompt}]
    
    print(f"\n{'='*60}")
    print(f"{context_key}")
    print(f"{'='*60}")
    print("Type your message and press Enter. Type 'quit' or 'exit' to end.")
    print("Type 'history' to see conversation history.")
    if debug:
        print("DEBUG MODE: Message counts will be shown after each response.")
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit"):
            print("\nGoodbye!")
            break
        
        # Show conversation history
        if user_input.lower() == "history":
            print("\n" + "="*60)
            print("CONVERSATION HISTORY")
            print("="*60)
            for i, msg in enumerate(messages):
                role = msg["role"].upper()
                content = msg["content"]
                if role == "SYSTEM":
                    print(f"\n[{role}] (System prompt + context - {len(content)} chars)")
                    print(f"Preview: {content[:200]}...")
                else:
                    print(f"\n[{role}]")
                    print(content)
            print("="*60 + "\n")
            continue

        # Add user message to conversation history
        # This history will be sent with the next API call
        messages.append({"role": "user", "content": user_input})

        try:
            # Call OpenAI API with FULL conversation history
            # messages array contains:
            #   1. System prompt with participant context (always first)
            #   2. All previous user messages
            #   3. All previous assistant responses
            # This ensures the AI remembers the entire conversation
            stream = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,  # <-- FULL HISTORY PASSED HERE
                temperature=0.9,  # Higher temperature for more natural, varied responses
                max_tokens=150,   # Limit response length to keep it concise
                presence_penalty=0.6,  # Encourage new topics/questions
                frequency_penalty=0.3,  # Reduce repetition
                stream=True
            )

            print("\nAssistant: ", end='', flush=True)

            # Collect the full message while streaming
            assistant_message = ""
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    assistant_message += content
                    print(content, end='', flush=True)

            print()  # Newline after streaming completes

            # Add the complete assistant message to conversation history
            # This will be included in the next API call
            messages.append({"role": "assistant", "content": assistant_message})
            
            # Show debug info if enabled
            if debug:
                user_msgs = sum(1 for m in messages if m["role"] == "user")
                assistant_msgs = sum(1 for m in messages if m["role"] == "assistant")
                total_chars = sum(len(m["content"]) for m in messages)
                print(f"\n[DEBUG] Messages in history: {len(messages)} total " +
                      f"(1 system + {user_msgs} user + {assistant_msgs} assistant) " +
                      f"| {total_chars} chars")
            
            print()

        except Exception as exc:
            print(f"\nError: {exc}\n")
            # Remove the failed user message to maintain conversation state
            messages.pop()

def load_system_prompt(config_path: Path) -> str:
    """Load system prompt from participant_background.yaml.

    Args:
        config_path: Path to participant_background.yaml file.

    Returns:
        str: System prompt text.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    system_prompt = config.get("system_prompt", "")
    if not system_prompt or not system_prompt.strip():
        raise ValueError("System prompt is empty")

    return system_prompt.strip()


def main() -> int:
    """Main entry point.

    Returns:
        int: Exit code (0 for success, 1 for error).
    """
    parser = argparse.ArgumentParser(
        description="Chat interface with GPT-5 using context-based prompts"
    )
    parser.add_argument(
        "context",
        type=str,
        help="Context key from participant_background.yaml (e.g., participant name)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent / "config.yaml",
        help="Path to config YAML with system prompt (default: ./config.yaml)",
    )
    parser.add_argument(
        "--analysis-config",
        type=Path,
        default=Path(__file__).parent / "participant_background_analysis.yaml",
        help="Path to psychological analysis YAML (default: ./participant_background_analysis.yaml)",
    )
    parser.add_argument(
        "--raw-config",
        type=Path,
        default=Path(__file__).parent / "participant_background.yaml",
        help="Path to raw context YAML (default: ./participant_background.yaml)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug info including message history size after each response",
    )

    args = parser.parse_args()

    # Get OpenAI API key from environment (GitHub secrets)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set", file=sys.stderr)
        return 1

    # Load system prompt from config.yaml and BOTH participant contexts
    try:
        base_system_prompt = load_system_prompt(args.config)
        
        # Load combined context (analysis + raw data)
        participant_context, is_unknown = load_combined_context(
            args.analysis_config,
            args.raw_config,
            args.context
        )
        
        system_prompt = base_system_prompt + "\n\n" + participant_context
        
        if args.debug:
            if is_unknown:
                print(f"\n[DEBUG] Unknown participant: {args.context}")
                print(f"  - Will ask them to introduce themselves")
            else:
                print(f"\n[DEBUG] Loaded context sources:")
                print(f"  - Analysis: {args.analysis_config}")
                print(f"  - Raw data: {args.raw_config}")
                print(f"  - Total context length: {len(participant_context)} chars")
            print()
        
        # Show special message for unknown participants
        if is_unknown and not args.debug:
            print(f"\n⚠️  No context found for '{args.context}'")
            print(f"Starting conversation in discovery mode...")
            
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Show loading message with delay
    print_char_by_char("Loading Your Past...")
    time.sleep(5)

    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)

    # Run chat loop
    try:
        chat_loop(client, system_prompt, args.context, debug=args.debug)
        return 0
    except Exception as exc:
        print(f"\nFatal error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    dotenv.load_dotenv(override=True)
    sys.exit(main())
