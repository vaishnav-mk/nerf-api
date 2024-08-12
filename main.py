from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import shutil
import os
import subprocess
from pathlib import Path
import time 

app = FastAPI()

BASE_DIR = Path("uploaded_images")
BASE_DIR.mkdir(parents=True, exist_ok=True)

running_processes = {}

def postprocess_obj(obj_file: Path, input_file: Path, output_file: Path):
    print(f"Converting {input_file} to {output_file}")
    try:
        subprocess.run([f"gltfpack -i {input_file} -o {output_file}"], shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Error converting {input_file} to gltf: {e}")
    else:
        print("Conversion complete")

def process_images(uuid_str: str, folder_path: Path):
    time.sleep(10)
    
    allowed_extensions = {".jpg", ".jpeg", ".png"}
    
    images = [img for img in folder_path.iterdir() if img.suffix.lower() in allowed_extensions]
    
    source_output_folder = Path("./output")
    destination_output_folder = folder_path / "output"
    
    os.makedirs(destination_output_folder, exist_ok=True)
    
    for file in source_output_folder.iterdir():
        if file.is_file():
            shutil.copy(file, destination_output_folder / file.name)
            
    obj_file = next((f for f in destination_output_folder.iterdir() if f.suffix.lower() == ".obj"), None)
    
    if obj_file:
        output_file = destination_output_folder / f"{obj_file.stem}.glb"
        postprocess_obj(obj_file, obj_file, output_file)    
    running_processes.pop(uuid_str, None)
    

@app.post("/upload-images/")
async def upload_images(files: list[UploadFile], unique_id: str, background_tasks: BackgroundTasks):
    
    upload_folder = BASE_DIR / unique_id
    upload_folder.mkdir(parents=True, exist_ok=True)
    
    print("unique_id", unique_id)

    
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
    