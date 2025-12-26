# TECHNOLOGY.md - Past Messages

Past Messages parses different formats of message logs, and continues them with generative modeling. 

### The Challenge of Format Diversity

Different messaging platforms export conversations in wildly different formats:

**WhatsApp (US):**
```
[1/15/25, 2:34:12 PM] Alice: Hey, how are you?
[1/15/25, 2:35:08 PM] Bob: I'm good, thanks!
```

**iMessage (PDF from macOS):**
```
Mon, Jan 15 at 2:34 PM
Hey, how are you?
                                     I'm good, thanks!
```
(Messages appear as left/right bubbles based on sender)

**Facebook Messenger (JSON):**
```json
{"timestamp_ms": 1705336452000, "sender_name": "Alice", "content": "Hey, how are you?"}
```

For text-based formats, this installation uses **regular expressions** (regex)—pattern-matching formulas that describe text structure.

Think of regex as a search language. Instead of searching for exact text like "Alice", you can search for patterns like "any name followed by a colon." For example:

```
Pattern: \[(\d{1,2}/\d{1,2}/\d{2,4}), (\d{1,2}:\d{2}:\d{2})\] ([^:]+): (.+)
Matches: [1/15/25, 2:34:12 PM] Alice: Hey, how are you?
Captures: Date="1/15/25", Time="2:34:12 PM", Sender="Alice", Message="Hey, how are you?"
```

The system tries multiple regex patterns until it finds one that matches, then applies that pattern to extract all messages.

### PDF Parsing: Layout-Aware Extraction

iMessage exports from macOS are PDFs, not text files. PDFs store text along with visual layout information (fonts, positions, sizes). For iMessage PDFs, the system uses **layout-aware parsing**: it identifies message bubbles by analyzing:
1. **Timestamp detection**: Centered text matching patterns like "Mon, Oct 27 at 10:36" or "Today 14:18"
2. **Horizontal positioning**: Messages on the left (x-coordinate < 30% of page width) are from "Them", messages on the right are from "You"
3. **Vertical grouping**: Text blocks close together vertically (within 15 pixels) are merged into multi-line messages

This is more complex than regex—it's analyzing the geometric structure of the page, not just text patterns. The parser uses the visual layout to determine who said what, since iMessage PDFs don't include explicit sender labels.

## Language Models: Understanding and Generation

Once messages are parsed, the AI must understand conversation dynamics and generate meaningful continuations. This uses a **large language model** (LLM). This uses a transformer architecture.

### The Transformer Architecture (Briefly)

GPT-5.1 is built on the **transformer**, the same architecture discussed in the Present installation. Here's what makes it powerful for conversation:

**Attention mechanisms** allow the model to:
- Understand which previous messages are relevant to the current exchange
- Recognize conversational threads (topic shifts, callbacks to earlier discussions)
- Maintain consistency across multiple speakers and long timespans

When generating "your" response, the model attends to all your previous messages, learning your patterns. When generating the other person's response, it attends to theirs. This creates stylistically distinct voices.

### How Conversation Continuation Works

**Step 1: Context Loading**
The system feeds GPT-5.1 your entire parsed conversation history (or the most recent exchanges if the conversation is extremely long).

**Step 2: Prompt Engineering**
A carefully crafted **system prompt** instructs the model on its task:

```
You are continuing a conversation between Alice and Bob.
Based on the conversation history, continue the dialogue by:
1. Surfacing past challenges and unresolved tensions
2. Asking difficult questions that were avoided
3. Bringing hidden patterns into awareness

You will alternate between speakers. When speaking as Alice, adopt her
conversational style. When speaking as Bob, adopt his style.

Generate 5-7 exchanges total.
```

This prompt is critical. Without it, the model might:
- Generate generic responses that don't match speaking styles
- Avoid difficult topics (models are trained to be helpful and harmless)
- Lose track of who's speaking

**Step 3: Iterative Generation**
The model generates one message at a time:

1. Generate Alice's next message
2. Add it to conversation history
3. Generate Bob's reply
4. Add it to history
5. Repeat 5-7 times

Each generation sees the full history including previously generated messages, maintaining coherence across the extended conversation.