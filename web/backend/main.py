from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from pathlib import Path
import shutil
from fastapi.staticfiles import StaticFiles
from web.backend.api import chat, file
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi.responses import FileResponse
import os

app = FastAPI()

# ✅ 挂载上传目录的静态访问（用于 PDF iframe 展示）
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "data" / "policy"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static-files", StaticFiles(directory=UPLOAD_DIR), name="static-files")

# 确保 OCR 结果目录被挂载为静态文件
OCR_RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "ocr_results"
OCR_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# 挂载 OCR 文件目录，映射为 /static-ocr-files 路径
app.mount("/static-ocr-files", StaticFiles(directory=OCR_RESULTS_DIR), name="static-ocr-files")


# ✅ 模板渲染
templates = Jinja2Templates(directory="web/frontend/templates")

# ✅ API 路由
app.include_router(chat.router)
app.include_router(file.router)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("base.html", {"request": request})

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/files", response_class=HTMLResponse)
async def file_page(request: Request):
    return templates.TemplateResponse("file_manager.html", {"request": request})
