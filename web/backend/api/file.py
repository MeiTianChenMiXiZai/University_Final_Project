import logging
from fastapi import APIRouter, UploadFile, Form
from fastapi.responses import JSONResponse, HTMLResponse
import os
import shutil
import time
from pathlib import Path
from urllib.parse import unquote
from docx2pdf import convert
import pandas as pd

from rag.data_devide import process_policy_file, load_existing_data, save_json, convert_all_docx_to_pdf
import mammoth

# 初始化日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "policy"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

### **📌 1️⃣ 上传文件**
@router.post("/upload/")
async def upload_file(file: UploadFile):
    try:
        from uuid import uuid4
        import re

        def clean_filename(name):
            return re.sub(r"[^\w\u4e00-\u9fa5.\-（）()【】 ]", "", name)

        original_name = file.filename
        logger.info(f"📥 接收到上传文件: {original_name}")

        file_ext = original_name.split(".")[-1].lower()

        if file_ext == "docx":
            base_name = clean_filename(original_name.rsplit(".", 1)[0])
            temp_name = f"{base_name}_{uuid4().hex[:6]}.docx"
            temp_path = UPLOAD_DIR / temp_name

            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            logger.info(f"💾 已保存为临时 Word 文件: {temp_path}")

            # 进度提示：Word 转换开始
            logger.info("⏳ Word 转 PDF 转换中...")

            try:
                convert(str(temp_path))
                logger.info(f"✅ Word 转 PDF 成功：{temp_path.with_suffix('.pdf')}")
            except Exception as e:
                logger.error(f"❌ Word 转换失败: {e}")
                return JSONResponse(content={"message": f"❌ Word 转换失败: {e}"}, status_code=500)

            final_pdf_path = UPLOAD_DIR / original_name.replace(".docx", ".pdf")
            temp_pdf_path = temp_path.with_suffix(".pdf")

            if temp_pdf_path.exists():
                temp_pdf_path.rename(final_pdf_path)
                logger.info(f"✅ PDF 已重命名为原始名: {final_pdf_path}")
            else:
                logger.warning("⚠️ PDF 文件未找到，转换失败")
                return JSONResponse(content={"message": "⚠️ PDF 文件未找到，转换失败"}, status_code=500)

            temp_path.unlink()
            logger.info(f"🧹 临时 Word 文件已删除")

            return JSONResponse(content={"message": f"✅ Word 文件已转换为 PDF 并上传完成", "status": "success"})

        else:
            save_path = UPLOAD_DIR / original_name
            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            logger.info(f"💾 非 Word 文件已保存: {save_path}")

            return JSONResponse(content={"message": f"✅ 文件 {original_name} 上传完成", "status": "success"})

    except Exception as e:
        logger.exception(f"❌ 上传失败: {e}")
        return JSONResponse(content={"message": f"❌ 上传失败: {e}"}, status_code=500)



### **📌 2️⃣ 获取文件列表**
@router.get("/file-list/")
async def list_uploaded_files():
    """返回已上传的文件列表"""
    try:
        data = load_existing_data()
        file_list_html = ""

        for file in os.listdir(UPLOAD_DIR):
            file_path = UPLOAD_DIR / file
            file_size = round(os.path.getsize(file_path) / 1024 / 1024, 2)
            upload_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(file_path.stat().st_mtime))
            status = "已解析" if file in data else "未解析"

            file_list_html += f"""
            <tr class="border-b border-gray-200">
                <td class="py-3 px-6">{file}</td>
                <td class="py-3 px-6">{file_size} MB</td>
                <td class="py-3 px-6">{upload_time}</td>
                <td class="py-3 px-6">
                    <span class="px-2 py-1 text-xs font-semibold rounded {'bg-green-200' if status == '已解析' else 'bg-red-200'}">
                        {status}
                    </span>
                </td>
                <td class="py-3 px-6">
                    <button onclick="openDocumentViewer(this.getAttribute('data-filename'))" 
                        data-filename="{file}"
                            class='bg-gray-500 text-white px-2 py-1 text-xs rounded'>
                        查看
                    </button>

                    <button hx-delete='/delete-file/{file}' hx-target="#file-list" class='bg-red-500 text-white px-2 py-1 text-xs rounded'>删除</button>
                </td>
            </tr>
            """

        # ✅ **在返回的 HTML 中插入 JavaScript 代码**
        file_list_html += """
        <script>
            function openDocumentViewer(filename) {
                console.log("📄 请求查看文件: ", filename);

                // 显示模态窗口
                document.getElementById('document-modal').classList.remove('hidden');
                document.getElementById('document-viewer').innerHTML = "<p class='text-gray-500'>加载中...</p>";

                // 发送请求加载文件
                fetch(`/view-file/${encodeURIComponent(filename)}`)
                    .then(response => response.text())
                    .then(html => {
                        document.getElementById('document-viewer').innerHTML = html;
                    })
                    .catch(error => {
                        document.getElementById('document-viewer').innerHTML = `<p class="text-red-500">❌ 加载失败: ${error.message}</p>`;
                    });
            }

            function closeDocumentViewer() {
                document.getElementById('document-modal').classList.add('hidden');
            }
        </script>
        """

        logger.info("📃 文件列表已刷新")
        return HTMLResponse(content=file_list_html)

    except Exception as e:
        logger.error(f"❌ 获取文件列表失败: {str(e)}")
        return JSONResponse(content={"message": f"❌ 获取文件列表失败: {str(e)}", "status": "error"}, status_code=500)


### **📌 3️⃣ 删除文件**
@router.delete("/delete-file/{filename}")
async def delete_file(filename: str):
    """删除文件，并从 JSON 解析数据中删除"""
    try:
        file_path = UPLOAD_DIR / unquote(filename)

        if file_path.exists():
            file_path.unlink()
            logger.info(f"🗑️ 文件 {filename} 已删除")
        else:
            logger.warning(f"⚠️ 文件 {filename} 不存在")

        # ✅ 确保解析数据也被删除
        data = load_existing_data()
        if filename in data:
            del data[filename]
            save_json(data)
            logger.info(f"🗑️ 解析数据 {filename} 已删除")

        # ✅ 返回新的文件列表
        file_list_html = await list_uploaded_files()
        return HTMLResponse(content=file_list_html.body.decode("utf-8"))

    except Exception as e:
        logger.error(f"❌ 删除文件失败: {str(e)}")
        return JSONResponse(content={"message": f"❌ 删除文件失败: {str(e)}", "status": "error"}, status_code=500)

@router.post("/parse-all/")
async def parse_all_files():
    """解析所有未解析的文件"""
    try:
        data = load_existing_data()
        parsed_count = 0

        for file in os.listdir(UPLOAD_DIR):
            if file in data:
                continue  # 已解析跳过

            file_path = UPLOAD_DIR / file
            parsed = process_policy_file(str(file_path))
            if parsed:
                data[file] = parsed
                parsed_count += 1
                logger.info(f"✅ 已解析文件：{file}")
            else:
                logger.warning(f"⚠️ 文件 {file} 解析失败")

        save_json(data)

        return JSONResponse(content={"message": f"✅ 已成功解析 {parsed_count} 个文件", "status": "success"})

    except Exception as e:
        logger.error(f"❌ 批量解析失败: {str(e)}")
        return JSONResponse(content={"message": f"❌ 批量解析失败: {str(e)}", "status": "error"}, status_code=500)



@router.get("/view-file/{filename}")
async def view_file(filename: str):
    try:
        decoded_filename = unquote(filename)
        file_path = UPLOAD_DIR / decoded_filename

        if not file_path.exists():
            logger.warning(f"⚠️ 文件不存在: {file_path}")
            return JSONResponse(content={"detail": "Not Found"}, status_code=404)

        if file_path.suffix.lower() == ".pdf":
            logger.info(f"📄 加载 PDF: {decoded_filename}")
            return HTMLResponse(content=f"<iframe src='/static-files/{decoded_filename}' width='100%' height='600px' style='border:none;'></iframe>")

        return HTMLResponse(content="<div class='text-gray-500 text-sm'>暂不支持该格式的预览，敬请期待后续更新。</div>")

    except Exception as e:
        logger.error(f"❌ 读取文件失败: {str(e)}")
        return JSONResponse(content={"detail": f"❌ 读取文件失败: {str(e)}"}, status_code=500)


