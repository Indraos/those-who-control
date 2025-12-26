# Future - AI Photobooth with Scene Transformation

A web-based photobooth that captures your photo and generates alternate versions across different life scenarios using OpenAI gpt-image-1. The system preserves your identity while transforming the context: beach vacation, wedding, family restaurant, funeral. Includes optional CUPS printing for physical photo output.

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- Webcam (built-in or USB)
- OpenAI API key
- (Optional) USB printer configured via CUPS for physical prints

### Installation Steps

1. Navigate to the `future/` directory:
```bash
cd future
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.template .env
```

4. Edit `.env` with your settings:
```
OPENAI_API_KEY=your_api_key_here
PRINTER_NAME=Your_Printer_Name  # Optional: for printing
MEDIA_SIZE=Custom.4x6in          # Optional: print media size
BASE_URL=http://0.0.0.0:8000     # Server URL
```

### Optional: Printer Setup

If you want physical prints, configure CUPS printer:

1. Find your printer name:
```bash
lpstat -p -d
```

2. Add the printer name to `.env`:
```
PRINTER_NAME=Canon_SELPHY_CP1500
```

## Running the Application

Start the server:
```bash
python main.py
```

The server runs on `http://0.0.0.0:8000` by default (configurable via `.env`).

Open a web browser and navigate to:
```
http://localhost:8000
```

## Usage Flow

1. **Capture Photo**: Click "Capture" button to take photo with webcam
2. **Generate Scenes**: Click "Generate" to create 4 scene variations (20-40 seconds)
3. **View Results**: Original + 4 transformed images display on screen
4. **Print** (optional): Click "Print" on specific images to send to CUPS printer

### Generated Scenes

The default configuration generates four life scenarios:
- **Beach Vacation**: Tropical leisure setting
- **Wedding**: Formal celebration scene
- **Old Restaurant**: Family gathering context
- **Funeral**: Memorial service setting

All scenes preserve your facial features and identity while transforming the background and context.

## Troubleshooting

**Error: "OPENAI_API_KEY not found"**
- Ensure `.env` file exists with valid API key
- Check file is in the `future/` directory

**Webcam not working:**
- Grant browser permission when prompted
- Check camera is not in use by another application
- Try different browser (Chrome/Firefox recommended)

**Slow generation:**
- Normal: Each scene takes 5-10 seconds
- Total generation time: 20-40 seconds for 4 scenes

**Printing fails:**
- Verify printer is connected and powered on
- Check CUPS configuration: `lpstat -p -d`
- Ensure `PRINTER_NAME` in `.env` matches CUPS printer name

## Customization

Edit `config.yml` to modify scene prompts:

```yaml
scenes:
  beach:
    label: "Beach Vacation"
    prompt: "Your custom prompt here..."
```

**Prompt Tips:**
- Emphasize identity preservation: "Keep the person's face exactly the same"
- Specify context details: lighting, setting, mood
- Use "photorealistic" for natural-looking results

## Security Notes

For public installations:
- Images stored in `generated/` directory
- Files deleted automatically after 7 days (configure cleanup script)
- Path validation prevents directory traversal attacks
- CORS enabled for kiosk-style deployment
