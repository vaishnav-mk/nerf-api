from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import uuid
import shutil
from pathlib import Path
import time 

app = FastAPI()

BASE_DIR = Path("uploaded_images")
BASE_DIR.mkdir(parents=True, exist_ok=True)

running_processes = {}

def process_images(uuid_str: str, folder_path: Path):
    time.sleep(10)
    
    allowed_extensions = {".jpg", ".jpeg", ".png"}
    
    images = [img for img in folder_path.iterdir() if img.suffix.lower() in allowed_extensions]
    print(f"Images: {images}")
    
    output_file = folder_path / "output.txt"
    with output_file.open("w") as f:
        for image in images:
            f.write(f"Processed image: {image.name}\n")
    
    running_processes.pop(uuid_str, None)
    

@app.post("/upload-images/")
async def upload_images(files: list[UploadFile], background_tasks: BackgroundTasks):
    
    unique_id = str(uuid.uuid4())
    upload_folder = BASE_DIR / unique_id
    upload_folder.mkdir(parents=True, exist_ok=True)

    
    for file in files:
        file_path = upload_folder / file.filename
        with file_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)

    
    background_tasks.add_task(process_images, unique_id, upload_folder)
    running_processes[unique_id] = "Processing"

    return JSONResponse(content={"uuid": unique_id})

@app.get("/status/{uuid_str}")
async def check_status(uuid_str: str, file_name: str = "output.glb"):
    folder_path = BASE_DIR / uuid_str
    output_file = folder_path / file_name
    
    if uuid_str in running_processes:
        return JSONResponse(content={"status": "Processing"})

    if output_file.exists():
        return FileResponse(output_file)

    raise HTTPException(status_code=404, detail="Output file not found")

@app.get("/running-processes/")
async def get_running_processes():
    return JSONResponse(content=running_processes)

@app.get("/processed-images/")
async def get_processed_images():
    processed_images = [str(file) for file in BASE_DIR.glob("**/output.glb")]
    return JSONResponse(content={"processed_images": processed_images})

@app.get("/")
async def health():
    return {"status": "ok", "running_processes": len(running_processes), "urls": [f"/status/{uuid_str}" for uuid_str in running_processes]}
