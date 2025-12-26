# Present - Transformative Conversational Interface

A command-line conversational experience that guides users through a 5-minute transformative dialogue using OpenAI GPT-5. The system performs internet research on participants, then users select from those researched individuals to engage in increasingly direct reflection aimed at articulating one concrete change they will make in their life.

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- OpenAI API key
- SerpAPI key (for Google search)
- Perplexity AI API key (for research and validation)

### Installation Steps

1. Navigate to the `present/` directory:
```bash
cd present
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.template .env
```

4. Edit `.env` and add your API keys:
```
OPENAI_API_KEY=your_api_key_here
SERPAPI_KEY=your_serpapi_key_here
PERPLEXITY_API_KEY=your_perplexity_key_here
```

### Getting API Keys

You'll need API keys from three services:

1. **OpenAI** (GPT-5): Get a key from https://platform.openai.com/
   - Used for transformative conversations

2. **SerpAPI** (Google Search): Sign up at https://serpapi.com/
   - Free tier: 100 searches/month
   - Used to fetch Google search results

3. **Perplexity AI** (Research): Get a key from https://www.perplexity.ai/
   - Used to deep-dive and validate search results
   - Analyzes top results to extract verified information

## Step 1: Internet Research on Participants

The first step is to generate personalized context prompts by searching the internet for publicly available information about participants. The `search.py` script uses SerpAPI for Google search results and Perplexity AI for deep research and validation.

### How It Works

The search system performs automated internet research:
1. **Google Search** via SerpAPI to find top web results about each person
2. **Deep Research** via Perplexity AI to analyze and extract key facts
3. **Validation** to ensure results are about the correct person (not someone with a similar name)
4. **Summary Generation** to create concise, one-paragraph background contexts

### Configuring Search Parameters

The script creates `config.yaml` on first run with default search settings:

```yaml
search_settings:
  top_results_count: 10         # Number of Google results to analyze (5-10 recommended)
  max_perplexity_sources: 3     # Sources per result for validation (1-3 recommended)
  max_content_length: 1500      # Maximum characters per summary paragraph
  max_words_per_query: 250      # Max words in Perplexity queries
```

Edit these settings to control search depth and API usage costs.

### Running Internet Search

Provide a CSV file containing participant names:

```bash
python search.py path/to/participants.csv
```

**Required CSV Format:**
- Must include columns: `Name`, `Status`, `RSVP date`, `Is Plus One Of`
- Automatically filters out plus-ones (rows with "Is Plus One Of" populated or names ending in "'s +1")
- Only searches primary guests

**What Happens:**
1. ✓ Extracts primary guest names from CSV
2. ✓ For each person:
   - Searches Google via SerpAPI (1 API call per person)
   - Analyzes top 10 results via Perplexity AI (10 API calls per person)
   - Validates results against knowledge graph and reference information
   - Rejects results about different people with similar names
3. ✓ Generates `participant_background.yaml` with validated summaries
4. ✓ Each participant gets a one-paragraph background context

**Example output:**
```
Searching for: Jane Smith
[1/2] Fetching search results from SerpAPI...
  ✓ Found 10 results to analyze
[2/2] Performing deep Perplexity search on top 10 results...
  [1/10] Jane Smith - LinkedIn Profile... ✓ Validated
  [2/10] About Jane | Company Website... ✓ Validated
  [3/10] Jane Smith (actress) - Wikipedia... ⚠️ Rejected
  ...
  ✓ Completed: 7 validated results
```

### Search Output

**Generated file:**
- `participant_background.yaml` - Combined config with all participant contexts

**File structure:**
```yaml
system_prompt: "You are facilitating a transformative conversation..."
context:
  jane_smith:
    prompt: "Jane Smith is a software engineer at Google..."
  john_doe:
    prompt: "John Doe is a professor of biology at MIT..."
```

### Automatic Validation

The search system includes built-in validation to ensure accuracy:

- **Cross-reference validation**: Compares each result against Google's knowledge graph and top search snippets
- **Identity verification**: Rejects results about different people with similar names
- **Confidence filtering**: Marks results that can't be verified with sufficient confidence
- **Context consistency**: Only includes information that's consistent across multiple validated sources

**Validation markers:**
- ✓ Validated - Result confirmed to be about the correct person
- ⚠️ Rejected - Different person with same/similar name
- ⚠️ Cannot verify - Insufficient information to confirm identity

### Privacy & Ethics

**Important considerations:**
- Only searches publicly available information (Google search results)
- No social media scraping or private data access
- Participants should be informed if their public information is being used
- Generated contexts should be reviewed before use
- Consider obtaining consent for personalized experiences

## Step 2: Running Conversations with Participants

After completing the internet research (Step 1), you can now select from the researched participants to have transformative conversations.

### Basic Usage

```bash
python main.py <participant_name>
```

The participant name should match one of the people you researched in Step 1. The script automatically converts names to context keys (lowercase, spaces to underscores, apostrophes removed).

**Example:**
```bash
python main.py jane_smith
python main.py john_doe
```

### With DOS Terminal Aesthetic (macOS only)

For a retro terminal appearance:

```bash
./setup_terminal.sh <participant_name>
```

This will configure Terminal.app with green-on-black text and Courier font, then launch the conversation with the selected participant.

## Usage Flow

1. First, run internet research on participants (Step 1 above)
2. Select a participant from those researched
3. Run the application with the participant's name
4. Wait through the 5-second "Loading Your Past..." sequence
5. Engage in conversation when prompted
6. Type your responses and press Enter
7. The AI will guide you through ~5 minutes of dialogue using personalized context
8. Session ends when you articulate a concrete change or type 'exit'