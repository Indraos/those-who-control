# Past Images - AI Person Removal from Photos

Computational tool for removing specific people from photographs using AI segmentation and inpainting. Upload a reference image (person to remove) and target images (photos containing that person), and the system will automatically detect, segment, and erase them from each scene.

## Installation & Setup

### Prerequisites

- Python 3.10 or higher
- Modal account ([sign up free](https://modal.com))
- HuggingFace account with Stable Diffusion 3 access

### Installation Steps

1. Navigate to the `past_images/` directory:
```bash
cd past_images
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up HuggingFace access:
   - Create account at [huggingface.co](https://huggingface.co)
   - Accept SD3 license: [stabilityai/stable-diffusion-3-medium](https://huggingface.co/stabilityai/stable-diffusion-3-medium-diffusers)
   - Generate access token: [Settings → Tokens](https://huggingface.co/settings/tokens)

4. Configure Modal:
```bash
modal token new  # Authenticate with Modal
modal secret create huggingface-secret HF_TOKEN=your_hf_token_here
```

## Deploying to Modal

Deploy the application to Modal's serverless platform:

```bash
modal deploy main.py
```

The web interface will be available at:
```
https://<your-workspace>--past-images-web.modal.run
```

## Usage

1. **Upload Reference Image**
   - Photo clearly showing the person's face to be removed
   - Front-facing view recommended for best accuracy

2. **Upload Target Images**
   - One or more photos containing that person
   - Supports batch upload of multiple images

3. **Process**
   - Click "Process Images" button
   - Real-time progress bar shows current status
   - Processing takes ~20-35 seconds per image (batch mode)

4. **Download Results**
   - Individual download links for each processed image
   - Images show person seamlessly removed from scene

### Tips for Best Results

- **Reference image**: Clear, well-lit, front-facing portrait
- **Target images**: Person should be reasonably visible (not heavily occluded)
- **Batch size**: Upload 4+ images for optimal throughput
- **Quality**: Higher resolution input → better inpainting quality

## Troubleshooting

**Person not detected:**
- Ensure reference image has clear facial view
- Check target image has sufficient face visibility
- Try different reference photo with better lighting

**Inpainting artifacts:**
- Complex backgrounds may show seams
- Very large removed areas harder to fill convincingly
- Normal behavior for challenging scenes

**Slow processing:**
- Normal: 20-35s per image on A100 GPU
- First run may be slower (cold start, model loading)
- Batch processing is 2.5-3x faster than sequential

**Modal deployment fails:**
- Verify HuggingFace token is valid
- Check SD3 model license accepted
- Ensure Modal secret created correctly: `modal secret list`

## Pipeline Overview

**Processing Stack:**
1. **InsightFace** - Face detection and 512-dim embedding extraction
2. **MediaPipe** - 33-point body pose landmark detection
3. **SAM2 Base** - Batch segmentation using face + body keypoints
4. **Stable Diffusion 3** - High-quality batch inpainting

**Performance:**
- 20-35 seconds per image (A100 GPU, batch mode)
- 2.5-3x faster than sequential processing
- Processes 4 images simultaneously for optimal throughput