# Control

> "Who controls the past controls the future. Who controls the present controls the past."
>
> — George Orwell, *1984*

This installation explores memory and how technology changes it. Orwell's prescient warning about the manipulation of history speaks not only to totalitarian regimes, but to the subtle ways we reshape our own stories—through the images we choose to remember, the conversations we preserve, and the futures we imagine for ourselves.

In an age where our memories are increasingly mediated by technology, who truly controls our past? The algorithms that surface certain photos and bury others? The AI models that can seamlessly alter faces and scenes? Or do we retain agency over our own histories, even as the tools for rewriting them become ever more sophisticated?

This project examines three temporal lenses through which we construct and reconstruct ourselves:

## Preparation for the Event

### Equipment Requirements

**Hardware:**
- **Printed PDFs** (one copy each) - Generated documentation, title pages, QR codes
- **Kiosk computers** (as many as desired for `present/` and `future/`) Each with keyboard, mouse, and screen
- **Photo printer** (as many as desired for `future/`) photobooth output
  - USB-connected, CUPS-compatible
  - 4×6 photo paper recommended

**Software Setup:**
- Modal deployment for `past_images/` and `past_messages/` (web-based, no local hardware needed)
- Python environment for `present/` and `future/` on each kiosk

---

### Print Materials with Fading Memory Aesthetic

Generate PDF versions of all project documentation with a "fading memory" aesthetic—text that partially erases and degrades to reflect the theme of changing memory via `python prepare_materials.py`.

This creates PDFs in `print_output/` with fading effects. Words related to memory, identity, and transformation fade more heavily. Also automatically generates:
- Landscape title pages (96pt "those who control" + 72pt section titles: Future, Past Images, Past Messages, Present)
- QR codes for the Modal-deployed apps (past_messages and past_images)
- Typeform feedback form with QR code PDF for easy scanning
- A list of all available people for `present/`

To automatically send to your printer, use `python prepare_materials.py --send-to-printer`.
```

For setup, copy `.env.template` to `.env` and add your `TYPEFORM_TOKEN`, and run `pip install -r requirements.txt`.

## Structure

### `past/`
**The Rewriting of History**

Inspired by Stalin's systematic erasure of Trotsky and other purged officials from photographs, this explores how images—once considered immutable evidence of "what happened"—can be altered to rewrite history. When we can edit the past so seamlessly, what does memory mean? It also allows you to hallucinate continuations of past chats.

### `present/`
**The Transformative Conversation**

An AI-mediated dialogue that challenges you to articulate change. By conversing, you will identify how your public image differs from your own perception of the future.

### `future/`
**The Multiplicity of Possible Selves**

A photobooth that generates alternate versions of your present moment—the same people, the same faces, but in different scenes, different contexts, different futures. Which version is "real"? All of them. None of them. The future is not a single path but a superposition of possibilities.

## Philosophy

Memory is not retrieval—it is reconstruction. Each time we remember, we subtly alter the past. Each conversation shapes who we become. Each imagined future influences the choices we make today.

This project doesn't answer the question of who controls your past, present, and future. Instead, it asks you to sit with the discomfort of that uncertainty, and to consider: in a world where the past can be edited, the present can be generated, and the future can be simulated, what remains authentic?

Perhaps authenticity itself is the wrong frame. Perhaps what matters is not the objective truth of what happened or what will happen, but the meaning we choose to make from the infinite malleability of our stories.

## Installation

Each directory contains its own README with specific setup instructions.