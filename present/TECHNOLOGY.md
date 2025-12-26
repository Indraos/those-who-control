# TECHNOLOGY.md - Present

## Understanding the AI Behind the Conversation

The "Present" installation uses conversational artificial intelligence to create an intimate dialogue that evolves over time. This document introduces the key technologies and concepts that make this experience possible.

## Search 
Indexing of the internet has been done for a long while, and everyone of us uses web search every day. We use two of them (Perplexity and Google) to find initial insights on you, and use human curation to change them. 

## A Large Language Model

We are using a General Pretrained Transformer. The "T" in GPT stands for **Transformer**, a breakthrough in AI architecture introduced in 2017. If you know the architecture, skip. Otherwise:

**Traditional approach:** Earlier AI read text sequentially, word by word, like you're reading this sentence from left to right.

**Transformer approach:** The transformer can "attend to" all words simultaneously, understanding how each word relates to every other word in context. When you write "The animal didn't cross the street because it was too tired," the transformer understands that "it" refers to "animal" (not "street") by analyzing all the relationships at once.

This architecture uses something called **attention mechanisms**—essentially, the AI learns to focus on the most relevant parts of the input when generating each word of its response. Just as you might reread an earlier sentence to understand a pronoun's referent, the transformer mathematically weighs which previous words matter most.

### Creating a GPT

**Training phase** (happens once, before installation):
1. The model reads billions of words from human writing
2. It learns to predict what word comes next in a sequence
3. Through this simple task repeated trillions of times, it internalizes grammar, facts, reasoning patterns, and conversational dynamics

**Generation phase** (what happens when you type):
1. Your message becomes a sequence of numbers (tokens) the AI can process
2. The model predicts the most likely next word based on everything said so far
3. That word gets added to the context, and it predicts the next word
4. This repeats until the response is complete

The model doesn't "think" or "understand" in a human sense—it's performing incredibly sophisticated statistical prediction. Yet the patterns it has learned are so rich that the output feels remarkably human.

## Streaming: Real-Time Generation

When you send a message, you see the AI's response appear word by word. This isn't a visual effect—it's the actual generation process made visible. The model generates one token (roughly a word or word-fragment) at a time. Instead of waiting for the complete response, our system displays each token immediately as it's generated. The technical term for this is **streaming API**.

We use a system prompt to steer the system's behavior. A **system prompt** is a set of instructions given to the language model that shapes how it responds. For this installation, we craft prompts that:

1. Establish the relational context (push the person to get to an insight about themselves)
2. Define the conversational arc (start gentle, gradually increase directness)
3. Set the goal (guide toward articulating one concrete change)
4. Maintain boundaries (be confrontational but not abusive)

The art of **prompt engineering**—crafting these instructions—is central to making AI systems do specific things reliably. A poorly written prompt might produce responses that are too timid, too aggressive, repetitive, or off-topic. A well-crafted prompt creates the experience you encounter in this installation.

## The Terminal Aesthetic: Interface as Medium

The green-on-black text interface isn't arbitrary nostalgia—it's a deliberate choice to evoke early personal computing (1970s-1980s), when interacting with a computer felt rare and significant. **DOS (Disk Operating System)** was the text-based interface most people used before graphical user interfaces (Windows, Mac) became standard. The aesthetic creates: