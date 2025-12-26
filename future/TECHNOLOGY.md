# TECHNOLOGY.md - Future

## Understanding the AI That Transforms Your Image

The "Future" installation uses generative AI to transport you into imagined scenes—a beach vacation, a wedding, a funeral—while preserving your identity. This document introduces the technologies that enable machines to create and manipulate photorealistic images.

## Image-to-Image Generation: Reimagining Photos

Unlike text-to-image generation (which creates pictures from descriptions), this installation uses **image-to-image transformation**—taking your photo and reimagining it in a new context while maintaining your recognizable appearance.

This is a fundamentally different challenge than the "Past Images" installation:
- **Past Images** removes someone and fills the gap (inpainting)
- **Future** transforms the entire scene around you while preserving your identity

Think of it as computational costume design for entire environments.

## Generative AI for Images: How Machines Create Pictures

### The Evolution of Image Generation

**Traditional computer graphics** (video games, animated films) creates images through explicit modeling—artists design 3D objects, position lights, define materials. The computer renders exactly what was programmed.

**Generative AI** learns to create images by studying millions of examples, extracting patterns about what images "should" look like. It can then generate new images that follow those patterns without anyone explicitly programming every detail.

This represents a fundamentally different approach: from *instructed creation* to *learned generation*.

## GPT-Image-1: OpenAI's Image Generation Model

This installation uses **gpt-image-1**, OpenAI's latest image generation model that specializes in **identity preservation**—keeping you recognizable across transformations.

### What Makes gpt-image-1 Special

**Multimodal understanding**: Unlike models that only process images, gpt-image-1 integrates vision and language processing. When you provide:
- Input: Your photo
- Prompt: "Transform this person into a beach vacation scene"

The model simultaneously:
1. Analyzes your visual features (face, body, clothing)
2. Understands the semantic meaning of "beach vacation scene"
3. Generates a new image that satisfies both constraints

**Identity anchoring**: The model has been specifically trained to maintain facial features and body structure across transformations. Earlier models would often morph faces when changing scenes—gpt-image-1 treats identity as a constraint, not a suggestion.

### How It Differs from DALL-E and Midjourney

| Model | Primary Use | Limitation for This Installation |
|-------|-------------|----------------------------------|
| **DALL-E 3** | Text-to-image creation | Doesn't have image editing capabilities; generates from scratch |
| **Midjourney** | Artistic image generation | No official API; primarily web-based; less precise identity preservation |
| **Stable Diffusion** | Open-source generation | Requires self-hosting; slower; less consistent with identity preservation |
| **gpt-image-1** | Image editing with text guidance | Perfect fit: API available, fast, preserves identity well |

## The Technology Behind Generation: Diffusion Models

While gpt-image-1's exact architecture is proprietary, it likely builds on **diffusion models**—the current state-of-the-art for image generation.

### How Diffusion Models Work

Imagine teaching someone to draw by showing them photographs gradually fading into static noise, then teaching them to reverse the process.

**Training phase:**

1. **Forward diffusion**: Take a photo and progressively add random noise over many steps until it's pure static
   ```
   Clear photo → Slightly noisy → Very noisy → Pure static
   ```

2. **Learning to reverse**: Train a neural network to predict and remove the noise at each step
   ```
   Pure static → Less noisy → Clearer → Original photo
   ```

After training on millions of images, the model learns what "removing noise to reveal a coherent image" looks like.

**Generation phase:**

1. Start with random noise
2. The model gradually "denoises" it, guided by your text prompt and reference image
3. Each denoising step moves closer to a coherent image matching your description
4. After 30-50 steps, you have a photorealistic result

This process is called **iterative refinement**—the image emerges gradually, like a Polaroid developing.