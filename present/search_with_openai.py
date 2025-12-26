#!/usr/bin/env python3
"""
Enhanced search that combines Perplexity results with OpenAI filtering.
Processes participants CSV and generates filtered context for Stanford event.
"""

import os
import sys
import csv
import yaml
import argparse
import dotenv
from pathlib import Path

# Import from existing modules
from generate_context import generate_context_with_openai

dotenv.load_dotenv()


def extract_primary_guests(csv_file):
    """
    Extract primary guest names from CSV.
    Filters out plus-ones.
    """
    primary_guests = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Name'].strip()
            is_plus_one_of = row['Is Plus One Of'].strip()
            
            # Skip plus-ones
            if is_plus_one_of or name.endswith("'s +1"):
                continue
            
            primary_guests.append(name)
    
    return primary_guests


def load_perplexity_context_for_person(person_name, participant_background_file):
    """
    Load existing Perplexity results from participant_background.yaml if they exist.
    
    Returns:
        str: Existing context or None
    """
    if not os.path.exists(participant_background_file):
        return None
    
    with open(participant_background_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    
    # Normalize name to key format
    key_name = person_name.lower().replace(" ", "_").replace("'", "")
    
    if 'context' in data and key_name in data['context']:
        context_data = data['context'][key_name]
        if isinstance(context_data, dict) and 'prompt' in context_data:
            return context_data['prompt']
        elif isinstance(context_data, str):
            return context_data
    
    return None


def save_to_participant_background(person_name, context, output_file):
    """
    Save the filtered context to participant_background.yaml
    """
    key_name = person_name.lower().replace(" ", "_").replace("'", "")
    
    # Load existing data
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    
    # Ensure context dict exists
    if 'context' not in data:
        data['context'] = {}
    
    # Add or update the person's context
    data['context'][key_name] = {
        'prompt': context
    }
    
    # Save back to file
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"  ✓ Saved filtered context for '{person_name}'")


def process_all_participants(csv_file, participant_background_file, output_file, use_existing=True):
    """
    Process all participants: load Perplexity results and filter through OpenAI.
    
    Args:
        csv_file: Path to participants CSV
        participant_background_file: Path to existing participant_background.yaml with Perplexity results
        output_file: Where to save filtered results
        use_existing: Whether to use existing Perplexity results or generate fresh
    """
    print(f"\nReading participants from: {csv_file}")
    primary_guests = extract_primary_guests(csv_file)
    print(f"✓ Found {len(primary_guests)} primary guests\n")
    
    print("="*60)
    print("Processing participants through OpenAI filter")
    print("="*60)
    
    for idx, person_name in enumerate(primary_guests, 1):
        print(f"\n[{idx}/{len(primary_guests)}] {person_name}")
        
        # Load existing Perplexity results if available
        perplexity_results = None
        if use_existing:
            perplexity_results = load_perplexity_context_for_person(
                person_name, 
                participant_background_file
            )
            
            if perplexity_results:
                print(f"  → Found existing context ({len(perplexity_results)} chars)")
            else:
                print(f"  → No existing context, will generate fresh")
        
        # Generate filtered context with OpenAI
        try:
            filtered_context = generate_context_with_openai(person_name, perplexity_results)
            
            # Save to output file
            save_to_participant_background(person_name, filtered_context, output_file)
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue
    
    print("\n" + "="*60)
    print(f"✓ Processing complete!")
    print(f"✓ Filtered contexts saved to: {output_file}")
    print("="*60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process participants with OpenAI filtering for Stanford event"
    )
    parser.add_argument(
        "csv_file",
        type=str,
        help="Path to participants CSV file"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="participant_background.yaml",
        help="Input YAML with Perplexity results (default: participant_background.yaml)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="participant_background_analysis.yaml",
        help="Output YAML for psychological analyses (default: participant_background_analysis.yaml)"
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Generate fresh context without using existing Perplexity results"
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv_file):
        print(f"Error: CSV file not found: {args.csv_file}")
        return 1
    
    try:
        process_all_participants(
            args.csv_file,
            args.input,
            args.output,
            use_existing=not args.fresh
        )
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

