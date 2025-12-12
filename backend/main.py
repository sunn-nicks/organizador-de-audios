# backend/main.py
import shutil
import zipfile
import os
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse
from tempfile import mkdtemp

from organizer import organize_folder  # função principal exportada do organizer.py

app = FastAPI(title="Audio Organizer API")

BASE = Path(__file__).parent
UPLOAD_DIR = BASE / "uploads"
WORK_DIR = BASE / "work"
PROCESSED_DIR = BASE / "processed"

for p in (UPLOAD_DIR, WORK_DIR, PROCESSED_DIR):
    p.mkdir(exist_ok=True)

@app.post("/process")
async def process(
    files: list[UploadFile] = File(...),
    n_words: int = Form(5),
    keep_prefix: str = Form("yes"),  # "yes" ou "no"
    keep_formats: str = Form(".wav,.m4a,.mp3")  # comma-separated extensions
):
    """
    Recebe arquivos (ou um ZIP), processa e retorna um ZIP com o resultado.
    Params:
      - n_words: quantas palavras extrair (1..5)
      - keep_prefix: 'yes' ou 'no' (mantém prefixo VA/001 etc)
      - keep_formats: csv dos formatos a manter (ex: .wav,.m4a)
    """
    # preparar dirs limpos
    for d in (UPLOAD_DIR, WORK_DIR, PROCESSED_DIR):
        for f in d.iterdir():
            try:
                if f.is_file():
                    f.unlink()
                else:
                    shutil.rmtree(f)
            except Exception:
                pass

    # salvar uploads
    saved = []
    for up in files:
        dest = UPLOAD_DIR / up.filename
        with open(dest, "wb") as out:
            shutil.copyfileobj(up.file, out)
        saved.append(dest)

    # se houve um único zip enviado, extrair; senao, copia todos para work
    try:
        # se um dos arquivos for .zip, extrai o primeiro zip; caso contrário trata todos como arquivos
        zip_sent = next((p for p in saved if p.suffix.lower() == ".zip"), None)
        if zip_sent:
            extract_dir = WORK_DIR / "input"
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_sent, 'r') as z:
                z.extractall(extract_dir)
            input_root = extract_dir
        else:
            input_root = WORK_DIR / "input"
            input_root.mkdir(parents=True, exist_ok=True)
            # copiar somente os arquivos de upload
            for s in saved:
                shutil.copy(s, input_root / s.name)

    except Exception as e:
        return JSONResponse({"error": f"Falha ao preparar arquivos: {e}"}, status_code=500)

    # parse keep formats
    formats = [ext.strip().lower() if ext.strip().startswith('.') else f".{ext.strip().lower()}" for ext in keep_formats.split(",") if ext.strip()]

    # executar organizador (a função fará todo o trabalho em uma pasta temporária)
    try:
        out_dir = PROCESSED_DIR / "result"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # chamar a função principal do organizer
        # options: n_words (1..5), keep_prefix (bool), formats (list)
        organize_folder(
            input_root,
            out_dir,
            n_words = max(1, min(5, int(n_words))),
            keep_prefix = (keep_prefix.lower() in ("yes","true","1")),
            keep_formats = formats
        )

    except Exception as e:
        return JSONResponse({"error": f"Erro procesando áudios: {e}"}, status_code=500)

    # zipar o resultado
    zip_path = PROCESSED_DIR / "organized_result.zip"
    try:
        if zip_path.exists():
            zip_path.unlink()
        shutil.make_archive(str(zip_path).replace(".zip",""), "zip", out_dir)
    except Exception as e:
        return JSONResponse({"error": f"Erro ao criar zip: {e}"}, status_code=500)

    return FileResponse(zip_path, media_type="application/zip", filename="organized_result.zip")
