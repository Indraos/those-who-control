# Past Messages - AI Conversation Continuation

Upload a messenger chat export and GPT-5.1 will continue the conversation for 5-7 exchanges, using a transformative prompt that surfaces difficult truths and unresolved tensions. Supports WhatsApp, iMessage, Signal, Facebook Messenger, and WeChat formats.

## Installation & Setup

### Prerequisites

- Python 3.10 or higher
- Modal account ([sign up free](https://modal.com))
- OpenAI API key with GPT-5.1 access

### Installation Steps

1. Navigate to the `past_messages/` directory:
```bash
cd past_messages
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure Modal:
```bash
modal token new  # Authenticate with Modal
modal secret create openai-secret OPENAI_API_KEY=your_openai_key_here
```

## Deploying to Modal

Deploy the application to Modal's serverless platform:

```bash
modal deploy main.py
```

The web interface will be available at:
```
https://<your-workspace>--past-messages-web.modal.run
```

## Supported Platforms

| Platform | Export Format | How to Export |
|----------|--------------|---------------|
| **WhatsApp** | `.txt` | Open chat → ⋮ → More → Export chat (without media), which will download a `.txt` file. |
| **iMessage** | `.pdf` | macOS Messages app → Select conversation, scroll up as far as you want → File → Print → Save as PDF |
| **Facebook Messenger** | `.json` | [Go here](https://accountscenter.facebook.com/info_and_permissions/dyi/) request a `json` output of as much content as you want. In the extracted folder, go to `your_facebook_activity/messages/inbox/[person_name]` and download `messages_1.json`.

## Usage

1. **Upload Chat Export**
   - Click "Choose File" and select your exported chat file
   - System auto-detects format (WhatsApp, iMessage, Signal, etc.)

2. **Generate Continuation**
   - Click "Generate Continuation"
   - GPT-5.1 analyzes the last 50 messages
   - Generates 5-7 exchanges continuing the conversation
   - Processing takes 10-30 seconds

3. **Download Result**
   - HTML file contains original messages + AI continuation
   - AI messages visually marked with blue border and "AI" label
   - Self-contained file (can be opened in any browser)

## Features

**Transformative Prompt:**
- Surfaces unresolved tensions and difficult conversations
- Brings hidden patterns to awareness
- Guides toward vulnerability and honesty
- Focuses on growth and insight

**Multi-Format Support:**
- Auto-detection of messenger platform
- Handles various date/time formats
- Filters media placeholders (`[image omitted]`)
- Preserves multi-line messages

**HTML Export:**
- Chat bubble interface (similar to messaging apps)
- Clear visual distinction between original and AI messages
- Responsive design for mobile/desktop viewing
- No external dependencies (inline CSS)

## Troubleshooting

**"Could not detect message format":**
- Ensure file is exported correctly from messaging app
- Check file encoding is UTF-8
- Verify format matches supported platforms listed above

**"No messages found in file":**
- File may be empty or corrupted
- Re-export from messaging app
- Ensure export includes actual message content (not just media)

**Generation takes too long:**
- Normal: 10-30 seconds for 5-7 exchanges
- Large chat histories (1000+ messages) may take longer
- System uses last 50 messages only to maintain speed

**Modal deployment fails:**
- Verify Modal authentication: `modal token new`
- Check secret created: `modal secret list`
- View logs: `modal app logs past-messages`

## Configuration

Edit `config.yml` to customize AI behavior:

```yaml
system_prompt: |
  Your custom prompt here...

exchanges: 6          # Number of back-and-forth exchanges
temperature: 0.8      # Creativity level (0.0-1.0)
max_tokens: 2000      # Maximum length per exchange
```

## Security & Privacy

- Messages processed in-memory only during session
- Generated HTML deleted after 7 days
- No user accounts or persistent data storage
- Chat content sent to OpenAI API (see OpenAI privacy policy)
- No analytics or tracking
