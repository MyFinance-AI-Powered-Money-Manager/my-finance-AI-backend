# MyFinance AI Backend

Backend API untuk:
- Prediksi kategori produk (model Keras/TensorFlow)
- OCR struk via Veryfi + (opsional) auto-kategorisasi item
- AI Financial Insight bulanan via OpenAI

## Quickstart (Local)

### 1) Clone

```bash
git clone <repo-url>
cd my-finance-AI-backend
```

### 2) Buat virtualenv

Windows PowerShell:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3) Siapkan environment variables

Copy contoh env:

```bash
copy .env.example .env
```

Isi `.env` sesuai kebutuhan.

Minimal untuk endpoint yang ada:
- OCR (Veryfi): `VERYFI_CLIENT_ID`, `VERYFI_CLIENT_SECRET`, `VERYFI_USERNAME`, `VERYFI_API_KEY`
- AI Insight (OpenAI): `OPENAI_API_KEY` dan `INTERNAL_SERVICE_KEY`
- Opsional: `OPENAI_MODEL` (default: `gpt-4o-mini`)

### 4) Install dependencies

```bash
pip install -r requirements.txt
```

### 5) Run server

```bash
uvicorn app.main:app --reload
```

API base URL (default):

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Quickstart (Docker)

```bash
docker compose up --build
```

Pastikan file `.env` tersedia (lihat `docker-compose.yml` menggunakan `env_file: .env`).

## Base Path

Semua endpoint API ada di prefix:

```text
/api/v1
```

Contoh: `POST /api/v1/predict`

## Authentication / Headers

Hanya endpoint AI Insight yang membutuhkan header internal:

```text
x-internal-service-key: <INTERNAL_SERVICE_KEY>
```

Endpoint `predict` dan `ocr` tidak memakai auth.

## Endpoints

Di bawah ini contoh request dan response untuk masing-masing endpoint.

---

### 1) Health Root

**GET** `/`

Response (200):

```json
{
	"message": "Product Categorization API API is running.",
	"version": "1.0.0",
	"docs_url": "/docs"
}
```

---

### 2) Predict (Single)

**POST** `/api/v1/predict`

Request JSON:

```json
{
	"name": "indomie goreng 1 pcs"
}
```

Response (200) (contoh):

```json
{
	"product_name": "indomie goreng 1 pcs",
	"predicted_category": "FOOD",
	"confidence_pct": "93.21%",
	"top_k_predictions": [
		{
			"rank": 1,
			"category": "FOOD",
			"confidence": 0.9321,
			"percentage": "93.21%"
		},
		{
			"rank": 2,
			"category": "GROCERIES",
			"confidence": 0.041,
			"percentage": "4.10%"
		}
	]
}
```

Curl:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/predict" \
	-H "Content-Type: application/json" \
	-d "{\"name\":\"indomie goreng 1 pcs\"}"
```

---

### 3) Predict (Batch)

**POST** `/api/v1/predict-batch`

Request JSON:

```json
{
	"names": [
		"indomie goreng 1 pcs",
		"susu ultra 1L",
		"sabun mandi"
	]
}
```

Response (200) adalah array (contoh):

```json
[
	{
		"product_name": "indomie goreng 1 pcs",
		"predicted_category": "FOOD",
		"confidence_pct": "93.21%"
	},
	{
		"product_name": "susu ultra 1L",
		"predicted_category": "DAIRY",
		"confidence_pct": "88.05%"
	},
	{
		"product_name": "sabun mandi",
		"predicted_category": "PERSONAL_CARE",
		"confidence_pct": "90.10%"
	}
]
```

Curl:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/predict-batch" \
	-H "Content-Type: application/json" \
	-d "{\"names\":[\"indomie goreng 1 pcs\",\"susu ultra 1L\",\"sabun mandi\"]}"
```

---

### 4) OCR Receipt

**POST** `/api/v1/ocr`

Request: `multipart/form-data` (upload file)

Curl:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/ocr" \
	-H "accept: application/json" \
	-F "file=@./sample-receipt.jpg"
```

Response (200) (contoh):

```json
{
	"status": "success",
	"total_items": 2,
	"items": [
		{
			"name": "INDOMIE GORENG",
			"total": 7000,
			"predicted_category": "FOOD"
		},
		{
			"name": "AIR MINERAL",
			"total": 5000,
			"predicted_category": "DRINK"
		}
	]
}
```

Catatan:
- Jika OCR tidak menemukan item valid, `items` bisa kosong.
- Jika `predicted_category` tidak tersedia, item tetap dikembalikan tanpa field tersebut.

---

### 5) AI Insight Health

**GET** `/api/v1/ai/health`

Response (200) (contoh):

```json
{
	"status": "ok",
	"service": "ai-financial-insight",
	"model": "gpt-4o-mini"
}
```

---

### 6) AI Financial Insight (Monthly)

**POST** `/api/v1/ai/financial-insights/monthly`

Headers:

```text
x-internal-service-key: <INTERNAL_SERVICE_KEY>
Content-Type: application/json
```

Request JSON (contoh minimal yang valid):

```json
{
	"user_id": "user-123",
	"transactions": [
		{
			"id": "tx-1",
			"user_id": "user-123",
			"type": "income",
			"total_amount": 5000000,
			"category": "GAJI",
			"subcategory": "Gaji Utama",
			"created_at": "2026-05-02T10:00:00Z",
			"items": []
		},
		{
			"id": "tx-2",
			"user_id": "user-123",
			"type": "expense",
			"total_amount": 1200000,
			"category": "NEEDS",
			"subcategory": "Makan & Minum Harian",
			"created_at": "2026-05-03T10:00:00Z",
			"items": [
				{
					"id": "it-1",
					"transaction_id": "tx-2",
					"item_name": "Nasi Padang",
					"price": 30000
				}
			]
		}
	],
	"transaction_items": [],
	"budgets": [
		{
			"id": "budget-1",
			"user_id": "user-123",
			"limit_amount": 2500000,
			"month_period": "2026-05"
		}
	]
}
```

Response (200) (contoh):

```json
{
	"user_id": "user-123",
	"period": "2026-05",
	"ai_insight": "Pada bulan Mei 2026, kamu termasuk **hemat** bulan ini. Pengeluaranmu masih jauh lebih kecil dari pemasukan, pertahankan kebiasaan baik ini ya."
}
```

Curl:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/ai/financial-insights/monthly" \
	-H "Content-Type: application/json" \
	-H "x-internal-service-key: <INTERNAL_SERVICE_KEY>" \
	-d "{\"user_id\":\"user-123\",\"transactions\":[],\"transaction_items\":[],\"budgets\":[{\"id\":\"budget-1\",\"user_id\":\"user-123\",\"limit_amount\":2500000,\"month_period\":\"2026-05\"}]}"
```

Validasi penting:
- Period selalu diambil dari `budgets[].month_period` (format `YYYY-MM`).
- `transactions[].created_at` dipakai untuk filter transaksi yang masuk period tersebut.
- Satu payload hanya boleh berisi satu `user_id`.

## Troubleshooting

- Error OCR terkait env: pastikan semua `VERYFI_*` diisi.
- Error AI Insight: pastikan `OPENAI_API_KEY` dan `INTERNAL_SERVICE_KEY` diisi.
- Untuk detail error response, lihat body JSON dari FastAPI.
