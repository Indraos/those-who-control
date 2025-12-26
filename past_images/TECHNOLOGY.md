# TECHNOLOGY.md - Past Images

## Understanding the AI That Removes People from Photos

The "Past Images" installation uses computer vision and generative AI to identify and remove a specific person from your photographs. This document introduces the key technologies that make computational seeing and image manipulation possible.

## Computer Vision: Teaching Machines to See

**Computer vision** is the field of AI that enables machines to extract meaning from images. While you instantly recognize a face or read text in a photo, computers see only millions of numbers representing pixel colors. Computer vision algorithms learn to find patterns in those numbers that correspond to objects, people, and scenes.

This installation uses multiple computer vision systems working together:
1. **Face recognition** to identify who to remove
2. **Body pose detection** to locate the person even when their face isn't visible
3. **Segmentation** to trace the exact outline of the person
4. **Inpainting** to fill the empty space convincingly

Each of these is a distinct AI challenge. Let's explore them.

## Face Recognition: Finding Your Person

### Step 1: Detecting Faces

Before identifying who someone is, the system must find faces in the image. This installation uses **InsightFace**, a neural network trained on millions of faces to detect facial regions regardless of angle, lighting, or partial occlusion.

The network scans the image and outputs bounding boxes: "There's a face here at coordinates (x, y) with width w and height h."

### Step 2: Face Embeddings

Once faces are found, the system needs to determine if each face matches your reference person. It does this through **face embeddings**—numerical fingerprints of identity.

**How embeddings work:**
- The neural network converts each face into a list of 512 numbers (a 512-dimensional vector)
- These numbers capture identity-defining features in abstract mathematical space
- Faces of the same person produce similar number patterns, even across age, expression, or lighting
- Faces of different people produce different patterns

Think of it like a barcode, but instead of representing a product ID, it represents the unique geometry and features of a face.

### Step 3: Matching by Similarity

To determine if two faces show the same person, the system calculates **cosine similarity**—a mathematical measure of how close two vectors are in 512-dimensional space.

- Similarity of 1.0: Identical faces
- Similarity of 0.8-1.0: Very likely the same person
- Similarity of 0.4-0.7: Possibly the same person (different ages, angles)
- Similarity below 0.4: Different people

This installation uses a threshold of 0.4, balancing false positives (removing strangers who look similar) against false negatives (missing your person at unusual angles).

## Pose Estimation: When Faces Aren't Enough

Sometimes the person you're removing has their back to the camera, is looking down, or is partially obscured. Face detection misses these cases.

**Pose estimation** uses a neural network to identify body landmarks—33 key points like shoulders, elbows, hips, knees, and ankles. Think of it as the system drawing a stick figure skeleton over each person.

This installation uses **MediaPipe Pose**, Google's body detection AI, which identifies these landmarks even when faces aren't visible. By combining face matches with body positions, the system catches more instances of your person.

## Segmentation: Tracing the Outline

Once the system knows which person to remove, it needs to trace their exact outline—every pixel that belongs to them, including hair, clothing, and shadows.

## Inpainting: Filling the Gap

With a mask defining what to remove, the final challenge is filling that space convincingly. This is **inpainting**—a term from art restoration, where damaged paintings are carefully filled in to match surrounding areas.

## What the AI Sees vs. What You See

It's worth reflecting on what "seeing" means for these systems:

**You see**: A person, memories, relationships, emotional context

**The AI sees**:
- Face detector: Patterns in pixel values matching human face geometry
- Pose estimator: Configurations of lines and joints matching human skeletons
- SAM2: Boundaries where statistical properties of pixels change
- SD3: Probability distributions over what pixels should exist in empty space

The AI has no concept of "person," "removal," or "past." It performs sophisticated pattern matching and statistical generation. The meaning—the transformation of your personal history—exists entirely in your interpretation.

## Limitations and Artifacts

Even cutting-edge AI has limits:

**When the system struggles:**
- Mirrors and reflections (might miss or create odd duplicates)
- Severe occlusion (person mostly hidden behind objects)
- Low resolution or blurry images (less information for neural networks)
- Unusual poses or angles (outside the training data distribution)
- Group photos with people close together (hard to separate)

**Visible artifacts:**
- Slightly blurred or "soft" areas where inpainting occurred
- Occasionally implausible background details
- Lighting mismatches if the person's shadow was complex
- Repeated patterns if the AI "hallucinates" wrong context

These imperfections aren't bugs—they're inherent to statistical learning systems working with limited information.

## Reflection: Computational Memory Editing

This installation uses AI technologies developed for practical purposes—face recognition for security, segmentation for medical imaging, inpainting for photo editing. Applied to personal photos, they become tools for rewriting visual history.

Consider the implications:

- What does it mean when AI can remove someone from existence in images?
- How does computational seeing differ from human memory?
- Are the imperfections (artifacts, errors) a failure or a honest representation of how memory actually works—incomplete, reconstructed, imperfect?

The technology enables the art, but the art asks you to reflect on the technology's role in shaping identity, memory, and history. Neural networks don't understand what they're doing when they remove someone from your photos. That understanding—and its emotional weight—belongs to you alone.
