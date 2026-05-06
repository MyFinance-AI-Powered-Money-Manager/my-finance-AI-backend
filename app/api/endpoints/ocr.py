import os
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile
from app.services.ocr_service import process_document, parse_line_items
from app.api.endpoints.predict import predictor

router = APIRouter()

@router.post("/ocr")
async def ocr_receipt(file: UploadFile = File(...)):

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    try:
        content = await file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read upload: {exc}")

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    suffix = os.path.splitext(file.filename)[1] or ".jpg"
    temp_path: str | None = None

    try:
        # On Windows, NamedTemporaryFile must be closed before another process can read it.
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            temp_path = tmp.name

        raw = process_document(temp_path)
        items = parse_line_items(raw)

        simplified_items: list[dict[str, float | str]] = []
        for item in items:
            name = item.get("name")
            total = item.get("total")
            if not name or total is None:
                continue
            try:
                total_value = float(total)
            except (TypeError, ValueError):
                continue

            simplified_items.append({"name": str(name), "total": total_value})

        if simplified_items:
            names = [item["name"] for item in simplified_items]
            df = predictor.predict_batch(names)
            predicted_categories = df.get("predicted_category")
            if predicted_categories is not None:
                for item, category in zip(simplified_items, predicted_categories.tolist()):
                    item["predicted_category"] = category

        return {
            "status": "success",
            "total_items": len(simplified_items),
            "items": simplified_items,
        }
    except RuntimeError as exc:
        # Typically missing VERYFI_* env vars.
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OCR failed: {exc}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
