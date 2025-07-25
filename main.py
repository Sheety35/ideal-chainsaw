from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import requests, os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# For HTML templates and CSS
templates = Jinja2Templates(directory="templates")


# Azure config
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
dev_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
API_VERSION = "2024-02-01"
HEADERS = {
    "api-key": API_KEY,
    "Content-Type": "application/json"
}

@app.get("/", response_class=HTMLResponse)
def get_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/download/{image_id}")
def download_image(image_id: str, url: str):
    """Proxy download for Azure blob images"""
    try:
        # Fetch the image from Azure
        response = requests.get(url)
        response.raise_for_status()
        
        # Return the image with proper download headers
        return Response(
            content=response.content,
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename=ai-generated-{image_id}.png"
            }
        )
    except Exception as e:
        return Response(
            content=f"Download failed: {str(e)}",
            status_code=400
        )

@app.post("/process", response_class=HTMLResponse)
def generate_image(
    request: Request, 
    prompt: str = Form(...), 
    size: str = Form("1024x1024"),
    mode: str = Form("generate")
):
    try:
        url = f"{ENDPOINT}/openai/deployments/{dev_name}/images/generations?api-version={API_VERSION}"
        body = {
            "prompt": prompt,
            "size": size,
            "n": 1
        }

        response = requests.post(url, headers=HEADERS, json=body)
        print(f"Generation POST {url} response:", response.status_code)

        if response.status_code != 200:
            return templates.TemplateResponse("index.html", {
                "request": request,
                "error": f"Generation failed: {response.status_code} - {response.text}",
                "prompt": prompt,
                "size": size
            })

        result = response.json()
        image_url = result["data"][0]["url"]
        revised_prompt = result["data"][0].get("revised_prompt", prompt)
        
        # Generate a unique image ID for download
        import time
        image_id = str(int(time.time()))
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "image_url": image_url,
            "image_id": image_id,
            "prompt": revised_prompt,
            "size": size
        })
        
    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": f"Error: {str(e)}",
            "prompt": prompt,
            "size": size
        })

# Health check endpoint for Render
@app.get("/health")
def health_check():
    return {"status": "healthy"}
