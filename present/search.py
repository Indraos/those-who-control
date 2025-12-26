#!/usr/bin/env python3
"""
Search script to generate context prompts from web research.
Processes a CSV of participants and creates a combined config.yml for main.py.
"""

import os
import sys
import json
import yaml
import csv
import argparse
from serpapi import GoogleSearch
from perplexity import Perplexity
import dotenv

dotenv.load_dotenv()

# Configuration file path
CONFIG_FILE = "config.yaml"

# Default configuration
DEFAULT_CONFIG = {
    "search_settings": {
        "person_name": "John Doe",
        "top_results_count": 10,
        "max_perplexity_sources": 3,
        "max_content_length": 1500,
        "max_words_per_query": 250,
        "show_full_snippets": True
    },
    "validation": {
        "enabled": True,
        "use_reference_context": True,
        "min_confidence": "high"
    }
}


def load_config():
    """Load configuration from config.yaml"""
    if os.path.exists(CONFIG_FILE):
        print(f"Loading configuration from {CONFIG_FILE}...")
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f)
        print("✓ Configuration loaded")
    else:
        print(f"Config file not found. Creating default {CONFIG_FILE}...")
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, sort_keys=False)
        config = DEFAULT_CONFIG
        print(f"✓ Default configuration created in {CONFIG_FILE}")
        print("  You can edit this file to customize search settings")

    return config


def extract_primary_guests(csv_file):
    """
    Extract primary guest names from CSV.
    Filters out plus-ones (names ending in "'s +1" or with "Is Plus One Of" populated).

    Returns:
        list: Names of primary guests
    """
    primary_guests = []

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Name'].strip()
            is_plus_one_of = row['Is Plus One Of'].strip()

            # Skip if this is someone's plus-one
            if is_plus_one_of:
                continue

            # Skip if name ends with "'s +1"
            if name.endswith("'s +1"):
                continue

            primary_guests.append(name)

    return primary_guests


def search_person(person_name, config, serpapi_key, perplexity_api_key):
    """
    Perform comprehensive search for a single person.

    Returns:
        dict: Search results containing serp_results and detailed_results
    """
    TOP_RESULTS_COUNT = config['search_settings']['top_results_count']
    MAX_PERPLEXITY_SOURCES = config['search_settings']['max_perplexity_sources']
    MAX_CONTENT_LENGTH = config['search_settings']['max_content_length']
    MAX_WORDS_PER_QUERY = config['search_settings']['max_words_per_query']

    print(f"\n{'='*60}")
    print(f"Searching for: {person_name}")
    print(f"{'='*60}")

    # Step 1: Get initial information from SerpAPI
    print(f"[1/2] Fetching search results from SerpAPI...")
    serp_params = {
        "q": person_name,
        "api_key": serpapi_key
    }

    serp_search = GoogleSearch(serp_params)
    serp_results = serp_search.get_dict()

    # Get top N results for deep dive
    top_results = serp_results.get("organic_results", [])[:TOP_RESULTS_COUNT]
    print(f"  ✓ Found {len(top_results)} results to analyze")

    # Step 2: Perform Perplexity searches with validation
    print(f"[2/2] Performing deep Perplexity search on top {len(top_results)} results...")
    client = Perplexity(api_key=perplexity_api_key)

    # Store detailed results
    detailed_results = []

    # Build reference context for validation
    reference_info = []
    if "knowledge_graph" in serp_results:
        kg = serp_results["knowledge_graph"]
        if 'title' in kg:
            reference_info.append(kg['title'])
        if 'description' in kg:
            reference_info.append(kg['description'])

    # Add snippets from top 3 results as reference
    for ref_result in top_results[:3]:
        if 'snippet' in ref_result:
            reference_info.append(ref_result['snippet'])

    reference_context = " ".join(reference_info)

    for idx, result in enumerate(top_results, 1):
        result_title = result.get('title', 'Untitled')
        result_url = result.get('link', 'No URL')
        result_snippet = result.get('snippet', 'No snippet available')

        print(f"  [{idx}/{len(top_results)}] {result_title[:50]}...", end=' ')

        # Create focused query with validation
        focused_query = f"""IMPORTANT: Verify this is about the correct person.

Target Person: {person_name}

Reference Information: {reference_context}

Current Result:
Title: {result_title}
URL: {result_url}
Snippet: {result_snippet}

VALIDATION:
1. Verify this is the same {person_name} from the reference
2. If DIFFERENT person, state "NOT_SAME_PERSON" and stop
3. If CANNOT verify, state "CANNOT_VERIFY" and stop

If validated, provide key facts: achievements, roles, affiliations, dates, locations.
Maximum {MAX_WORDS_PER_QUERY} words."""

        try:
            perplexity_result = client.search.create(
                query=focused_query,
                max_results=MAX_PERPLEXITY_SOURCES,
            )

            # Check validation
            is_valid = True
            validation_status = "validated"

            if hasattr(perplexity_result, 'results'):
                for perp_result in perplexity_result.results:
                    content = ""
                    if hasattr(perp_result, 'content') and perp_result.content:
                        content = perp_result.content
                    elif hasattr(perp_result, 'snippet') and perp_result.snippet:
                        content = perp_result.snippet

                    if "NOT_SAME_PERSON" in content:
                        is_valid = False
                        validation_status = "different_person"
                        print("⚠️ Rejected")
                        break
                    elif "CANNOT_VERIFY" in content:
                        is_valid = False
                        validation_status = "cannot_verify"
                        print("⚠️ Cannot verify")
                        break

            if is_valid:
                detailed_results.append({
                    'original_result': result,
                    'perplexity_data': perplexity_result,
                    'index': idx,
                    'validation_status': validation_status
                })
                print(f"✓ Validated")
            else:
                detailed_results.append({
                    'original_result': result,
                    'perplexity_data': None,
                    'index': idx,
                    'validation_status': validation_status,
                    'rejected': True
                })

        except Exception as e:
            print(f"✗ Error: {e}")
            detailed_results.append({
                'original_result': result,
                'perplexity_data': None,
                'index': idx,
                'error': str(e),
                'validation_status': 'error'
            })

    validated_count = sum(1 for d in detailed_results if d.get('validation_status') == 'validated')
    print(f"  ✓ Completed: {validated_count} validated results")

    return {
        'serp_results': serp_results,
        'detailed_results': detailed_results,
        'person_name': person_name
    }


def generate_paragraph_summary(search_result, max_content_length):
    """
    Generate a one-paragraph summary from search results.

    Returns:
        str: Paragraph summary
    """
    person_name = search_result['person_name']
    serp_results = search_result['serp_results']
    detailed_results = search_result['detailed_results']

    summary_parts = []

    # Add knowledge graph if available
    if "knowledge_graph" in serp_results:
        kg = serp_results["knowledge_graph"]
        if 'description' in kg:
            summary_parts.append(kg['description'])

    # Add validated content from detailed results
    for detail in detailed_results:
        if detail.get('validation_status') == 'validated' and detail.get('perplexity_data'):
            perp_data = detail['perplexity_data']

            if hasattr(perp_data, 'results'):
                for perp_result in perp_data.results:
                    content = ""
                    if hasattr(perp_result, 'content') and perp_result.content:
                        content = perp_result.content
                    elif hasattr(perp_result, 'snippet') and perp_result.snippet:
                        content = perp_result.snippet

                    if content:
                        # Limit length
                        if len(content) > max_content_length // 2:
                            content = content[:max_content_length // 2].rsplit(' ', 1)[0] + "..."
                        summary_parts.append(content)

    # Combine into single paragraph
    if summary_parts:
        paragraph = " ".join(summary_parts)
        # Limit total paragraph length
        if len(paragraph) > max_content_length:
            paragraph = paragraph[:max_content_length].rsplit('.', 1)[0] + "."
        return paragraph
    else:
        return f"No detailed information found for {person_name}."


def main():
    """
    Main function to process CSV and generate combined config.
    """
    parser = argparse.ArgumentParser(
        description='Generate context prompts from participant CSV'
    )
    parser.add_argument(
        'csv_file',
        help='Path to participants CSV file'
    )

    args = parser.parse_args()

    if not os.path.exists(args.csv_file):
        print(f"Error: CSV file not found: {args.csv_file}")
        sys.exit(1)

    # Load configuration
    config = load_config()

    # Read API keys from environment
    serpapi_key = os.getenv('SERPAPI_KEY')
    perplexity_api_key = os.getenv('PERPLEXITY_API_KEY')

    if not serpapi_key:
        print("Error: SERPAPI_KEY environment variable not set. Add it to your .env file.")
        sys.exit(1)
    if not perplexity_api_key:
        print("Error: PERPLEXITY_API_KEY environment variable not set. Add it to your .env file.")
        sys.exit(1)

    # Extract primary guests from CSV
    print(f"\nReading participants from: {args.csv_file}")
    primary_guests = extract_primary_guests(args.csv_file)
    print(f"✓ Found {len(primary_guests)} primary guests (excluding plus-ones)")
    print(f"\nParticipants to search:")
    for name in primary_guests:
        print(f"  - {name}")

    # Search each person
    all_search_results = []
    max_content_length = config['search_settings']['max_content_length']

    for person_name in primary_guests:
        search_result = search_person(person_name, config, serpapi_key, perplexity_api_key)
        all_search_results.append(search_result)

    # Generate combined config.yml
    print(f"\n{'='*60}")
    print("Generating combined config.yml...")
    print(f"{'='*60}")

    system_prompt = """You are facilitating a transformative conversation about change and growth.
Your role is to help the user articulate one concrete change they will make in their life.

Use the provided context information about the person to guide the conversation meaningfully.
Push the user to be specific and concrete about what they will actually do differently.
Do NOT propose changes yourself - the user must come up with the change.
Gradually increase your directness over approximately 5 minutes of conversation.

The conversation should feel challenging but supportive."""

    contexts = {}
    for search_result in all_search_results:
        person_name = search_result['person_name']
        # Create context key (lowercase, replace spaces with underscores)
        context_key = person_name.lower().replace(' ', '_').replace("'", "")

        # Generate paragraph summary
        paragraph = generate_paragraph_summary(search_result, max_content_length)

        contexts[context_key] = {
            'prompt': paragraph
        }

        print(f"  ✓ {person_name} → context.{context_key}")

    # Create combined config
    config_output = {
        'system_prompt': system_prompt,
        'context': contexts
    }

    output_filename = "participant_background.yaml"
    with open(output_filename, 'w', encoding='utf-8') as f:
        yaml.dump(config_output, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"\n✓ Participant background saved to: {output_filename}")
    print(f"  Contains {len(contexts)} participant contexts")
    print(f"\nUsage examples:")
    for context_key in list(contexts.keys())[:3]:
        print(f"  python main.py {context_key}")
    if len(contexts) > 3:
        print(f"  ... and {len(contexts) - 3} more")

    print(f"\n{'='*60}")
    print("✓ All searches complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
