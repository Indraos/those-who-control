#!/usr/bin/env python3
"""
Generate psychological and social analysis of a person using OpenAI API.
Takes a person's name and optional search results, returns essay-form analysis
exploring patterns, motivations, blind spots, and social positioning.
"""

import os
import sys
import argparse
import yaml
import csv
import dotenv
from openai import OpenAI

dotenv.load_dotenv()


def extract_primary_guests(csv_file):
    """Extract primary guest names from CSV, filtering out plus-ones."""
    primary_guests = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Name'].strip()
            is_plus_one_of = row.get('Is Plus One Of', '').strip()
            
            # Skip plus-ones
            if is_plus_one_of or name.endswith("'s +1"):
                continue
            
            primary_guests.append(name)
    
    return primary_guests


def load_existing_context(person_name, input_file):
    """Load existing Perplexity context for a person from input file."""
    if not os.path.exists(input_file):
        return None
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    
    key_name = person_name.lower().replace(" ", "_").replace("'", "")
    
    if 'context' in data and key_name in data['context']:
        context_data = data['context'][key_name]
        if isinstance(context_data, dict) and 'prompt' in context_data:
            return context_data['prompt']
        elif isinstance(context_data, str):
            return context_data
    
    return None


def generate_context_with_openai(person_name: str, perplexity_results: str = None) -> str:
    """
    Generate psychological and social analysis of a person using OpenAI.
    
    Creates an essay-form analysis exploring:
    - Patterns in choices and career trajectory
    - Underlying motivations and values
    - Social positioning and relationship to communities
    - Potential blind spots and areas for growth
    
    Args:
        person_name: Name of the person to analyze
        perplexity_results: Optional raw search results to ground the analysis
    
    Returns:
        str: Essay-form psychological and social analysis (800-1500 chars)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    client = OpenAI(api_key=api_key)
    
    # Event context for filtering
    event_context = """
EVENT CONTEXT:
This person is attending an intimate evening at Stanford focused on personal transformation and change.
The community includes ambitious individuals from Stanford, Harvard, MIT, and the SF Bay Area tech scene.
This is a conversation about growth, blind spots, and life choices - not professional networking.

Your analysis should help facilitate a challenging but supportive conversation about change.
"""
    
    # Build the prompt based on whether we have Perplexity results
    if perplexity_results:
        prompt = f"""You are a perceptive psychologist and social observer analyzing someone for a transformative conversation.

{event_context}

PERSON: {person_name}

RAW SEARCH RESULTS:
{perplexity_results}

TASK:
Write a concise psychological and social analysis (800-1500 characters) in essay form. This is NOT a resume summary.

CRITICAL: Ground every insight in SPECIFIC, CONCRETE examples from the search results. Reference actual:
- Companies they founded/joined
- Projects they worked on
- Transitions they made
- Choices they faced
- Communities they joined/left

YOUR ANALYSIS SHOULD EXPLORE:

1. PATTERNS & PSYCHOLOGY
   - What patterns emerge from their SPECIFIC choices? (Name them)
   - What drives them based on WHAT THEY'VE ACTUALLY DONE?
   - What do they value based on their ACTUAL actions?
   - What contradictions exist between SPECIFIC pursuits? (Reference both)

2. SOCIAL POSITIONING
   - How do they position themselves? (Give SPECIFIC examples)
   - What roles have they ACTUALLY taken on?
   - What does moving from [X] to [Y] say about them?

3. BLIND SPOTS & THEMES
   - What might they NOT see about [SPECIFIC PATTERN]?
   - What narrative are they telling based on [SPECIFIC TRAJECTORY]?
   - Where might they be stuck? (Point to CONCRETE evidence)
   - What questions would challenge them about [SPECIFIC CHOICES]?

STYLE:
- Write as a fluid essay with SPECIFIC references
- Ground every claim in observable behavior/choices
- Be direct: "When you left [X] for [Y]..." or "The pattern from [A] to [B] to [C] reveals..."
- Make the person feel: "They really looked at what I've done"

EXAMPLE OF GOOD SPECIFICITY:
"The arc from founding a longevity startup at 18 to building a VC fund that invests in other founders reveals..."
NOT: "They show entrepreneurial drive"

FILTER OUT:
- Generic observations that could apply to anyone
- Vague psychologizing without evidence
- Different people with same name"""
    else:
        prompt = f"""You are a perceptive psychologist and social observer analyzing someone for a transformative conversation.

{event_context}

PERSON: {person_name}

TASK:
First, research this person thoroughly. Then write a concise psychological and social analysis (800-1500 characters) in essay form.

CRITICAL: Your analysis MUST reference SPECIFIC, CONCRETE facts about what they've done:
- Actual companies/organizations they've worked with
- Real projects or roles they've taken
- Specific transitions in their career
- Named institutions or communities

YOUR ANALYSIS SHOULD EXPLORE:

1. PATTERNS & PSYCHOLOGY
   - What patterns emerge from SPECIFIC choices they've made?
   - What drives them based on OBSERVABLE actions?
   - What contradictions exist in their ACTUAL trajectory?

2. SOCIAL POSITIONING  
   - How have they ACTUALLY positioned themselves? (Give examples)
   - What roles have they TAKEN ON in practice?

3. POTENTIAL BLIND SPOTS
   - What might they not see about [SPECIFIC PATTERN YOU IDENTIFIED]?
   - What questions could challenge them about [SPECIFIC CHOICES]?

STYLE:
- Write as a fluid essay with specific references
- Ground every insight in concrete examples
- Be direct: "When you moved from [X] to [Y]..." or "The pattern of [A], [B], [C] shows..."
- Make them think: "They really understood what I've done"

AVOID:
- Generic observations that could apply to anyone
- Vague speculation without evidence
- Psychological jargon without grounding"""
    
    print(f"Analyzing: {person_name}")
    print("Generating psychological and social analysis...")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are a perceptive psychologist and social analyst. Your analyses reveal patterns, motivations, and blind spots in people's lives.

Your writing is:
- Essay-form, flowing prose (not lists or bullets)
- Psychologically insightful but compassionate
- Direct about contradictions and patterns
- ALWAYS grounded in SPECIFIC, CONCRETE examples
- Focused on themes of identity, growth, and social positioning

CRITICAL: Every insight must be targetable and specific:
✓ "The move from academia to startup life, then back to a research role, suggests..."
✗ "They seem drawn to intellectual pursuits"

✓ "Founding three companies before 25, then joining a VC fund to invest in others, reveals..."
✗ "They're entrepreneurial"

✓ "Your work spans MIT's AI lab, a stint at Google, then an independent research project - each progressively more autonomous..."
✗ "You value independence"

You help people see themselves through the SPECIFIC CHOICES they've made. Reference actual projects, transitions, and decisions so they can't dismiss your insights as generic."""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.8,  # Slightly higher for more creative psychological insight
            max_tokens=1200  # More tokens for essay-form analysis
        )
        
        context = response.choices[0].message.content.strip()
        print("✓ Analysis complete")
        return context
        
    except Exception as e:
        print(f"✗ Error generating analysis: {e}")
        return f"Unable to generate analysis for {person_name}."


def save_to_participant_background(person_name: str, context: str, output_file: str = "participant_background_analysis.yaml"):
    """
    Save or update the analysis in participant_background.yaml
    
    Args:
        person_name: Name of the person
        context: Generated psychological analysis text
        output_file: Path to the YAML file
    """
    # Normalize name to key format (lowercase, underscores)
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
    
    print(f"✓ Saved analysis for '{person_name}' as key '{key_name}' in {output_file}")


def process_batch(csv_file, input_file, output_file):
    """Process all participants from CSV file."""
    print(f"\nReading participants from: {csv_file}")
    primary_guests = extract_primary_guests(csv_file)
    print(f"✓ Found {len(primary_guests)} primary guests\n")
    
    print("="*60)
    print("Generating psychological analyses")
    print("="*60)
    
    for idx, person_name in enumerate(primary_guests, 1):
        print(f"\n[{idx}/{len(primary_guests)}] {person_name}")
        
        # Load existing context from input file
        perplexity_results = load_existing_context(person_name, input_file)
        
        if perplexity_results:
            print(f"  → Using existing context ({len(perplexity_results)} chars)")
        else:
            print(f"  → No existing context, generating fresh")
        
        try:
            # Generate analysis
            context = generate_context_with_openai(person_name, perplexity_results)
            
            # Save to output file
            save_to_participant_background(person_name, context, output_file)
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue
    
    print("\n" + "="*60)
    print(f"✓ Complete! Analyses saved to: {output_file}")
    print("="*60)
    print(f"\nNow you can run:")
    print(f"  python main.py <person_name>")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate psychological and social analysis using OpenAI"
    )
    parser.add_argument(
        "input",
        type=str,
        help="Person name (e.g., 'John Doe') OR path to participants CSV for batch processing"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all people from CSV file (input should be CSV path)"
    )
    parser.add_argument(
        "--input-context",
        type=str,
        default="participant_background.yaml",
        help="Input YAML with existing context (default: participant_background.yaml)"
    )
    parser.add_argument(
        "--perplexity-results",
        type=str,
        help="Optional: Raw search results to analyze (for single person mode)"
    )
    parser.add_argument(
        "--perplexity-file",
        type=str,
        help="Optional: Path to file containing raw search results (for single person mode)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="participant_background_analysis.yaml",
        help="Output YAML file (default: participant_background_analysis.yaml)"
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Only print the analysis, don't save to file (single person mode only)"
    )
    
    args = parser.parse_args()
    
    try:
        # Batch mode: process CSV
        if args.batch:
            if not os.path.exists(args.input):
                print(f"Error: CSV file not found: {args.input}", file=sys.stderr)
                return 1
            
            process_batch(args.input, args.input_context, args.output)
            return 0
        
        # Single person mode
        person_name = args.input
        
        # Load Perplexity results if provided
        perplexity_results = args.perplexity_results
        
        if args.perplexity_file:
            print(f"Loading Perplexity results from: {args.perplexity_file}")
            with open(args.perplexity_file, 'r', encoding='utf-8') as f:
                perplexity_results = f.read()
        
        # Generate analysis
        context = generate_context_with_openai(person_name, perplexity_results)
        
        print("\n" + "="*60)
        print(f"PSYCHOLOGICAL & SOCIAL ANALYSIS: {person_name}")
        print("="*60)
        print(context)
        print("="*60 + "\n")
        
        # Save to file unless --print-only
        if not args.print_only:
            save_to_participant_background(person_name, context, args.output)
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

