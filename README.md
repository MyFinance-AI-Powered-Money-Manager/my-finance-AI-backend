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
  "user_id": "user-004",
  "transactions": [
    {
      "id": "trx-301",
      "user_id": "user-004",
      "wallet_id": "wallet-001",
      "type": "income",
      "total_amount": 7000000,
      "category": "GAJI",
      "subcategory": "Gaji Utama",
      "deskripsi": "Gaji bulanan",
      "transfer_id": null,
      "created_at": "2026-08-01T08:00:00.000Z",
      "items": []
    },
    {
      "id": "trx-302",
      "user_id": "user-004",
      "wallet_id": "wallet-001",
      "type": "expense",
      "total_amount": 2200000,
      "category": "NEEDS",
      "subcategory": "Sewa & Tempat Tinggal",
      "deskripsi": "Bayar kos bulanan dan iuran lingkungan",
      "transfer_id": null,
      "created_at": "2026-08-02T09:00:00.000Z",
      "items": []
    },
    {
      "id": "trx-303",
      "user_id": "user-004",
      "wallet_id": "wallet-001",
      "type": "expense",
      "total_amount": 950000,
      "category": "NEEDS",
      "subcategory": "Belanja Bulanan",
      "deskripsi": "Belanja kebutuhan dapur dan rumah",
      "transfer_id": null,
      "created_at": "2026-08-03T17:30:00.000Z",
      "items": []
    },
    {
      "id": "trx-304",
      "user_id": "user-004",
      "wallet_id": "wallet-001",
      "type": "expense",
      "total_amount": 780000,
      "category": "NEEDS",
      "subcategory": "Transportasi",
      "deskripsi": "Transport harian untuk kerja",
      "transfer_id": null,
      "created_at": "2026-08-05T07:45:00.000Z",
      "items": []
    },
    {
      "id": "trx-305",
      "user_id": "user-004",
      "wallet_id": "wallet-001",
      "type": "expense",
      "total_amount": 650000,
      "category": "NEEDS",
      "subcategory": "Tagihan & Kewajiban",
      "deskripsi": "Bayar listrik, air, dan internet",
      "transfer_id": null,
      "created_at": "2026-08-07T10:15:00.000Z",
      "items": []
    },
    {
      "id": "trx-306",
      "user_id": "user-004",
      "wallet_id": "wallet-001",
      "type": "expense",
      "total_amount": 1200000,
      "category": "NEEDS",
      "subcategory": "Kesehatan",
      "deskripsi": "Kontrol kesehatan dan beli obat",
      "transfer_id": null,
      "created_at": "2026-08-09T14:20:00.000Z",
      "items": []
    },
    {
      "id": "trx-307",
      "user_id": "user-004",
      "wallet_id": "wallet-001",
      "type": "expense",
      "total_amount": 900000,
      "category": "NEEDS",
      "subcategory": "Keluarga",
      "deskripsi": "Kirim uang untuk kebutuhan keluarga",
      "transfer_id": null,
      "created_at": "2026-08-12T11:00:00.000Z",
      "items": []
    },
    {
      "id": "trx-308",
      "user_id": "user-004",
      "wallet_id": "wallet-001",
      "type": "expense",
      "total_amount": 500000,
      "category": "NEEDS",
      "subcategory": "Pendidikan & Kerja",
      "deskripsi": "Beli buku dan perlengkapan kerja",
      "transfer_id": null,
      "created_at": "2026-08-15T16:40:00.000Z",
      "items": []
    },
    {
      "id": "trx-309",
      "user_id": "user-004",
      "wallet_id": "wallet-001",
      "type": "expense",
      "total_amount": 450000,
      "category": "NEEDS",
      "subcategory": "Asuransi",
      "deskripsi": "Bayar premi asuransi bulanan",
      "transfer_id": null,
      "created_at": "2026-08-18T09:10:00.000Z",
      "items": []
    },
    {
      "id": "trx-310",
      "user_id": "user-004",
      "wallet_id": "wallet-001",
      "type": "expense",
      "total_amount": 350000,
      "category": "WANTS",
      "subcategory": "Jajan & Nongkrong",
      "deskripsi": "Jajan ringan dan kopi",
      "transfer_id": null,
      "created_at": "2026-08-21T19:00:00.000Z",
      "items": []
    },
    {
      "id": "trx-311",
      "user_id": "user-004",
      "wallet_id": "wallet-001",
      "type": "expense",
      "total_amount": 300000,
      "category": "OTHER",
      "subcategory": "Lain-lain & Darurat",
      "deskripsi": "Biaya tidak terduga",
      "transfer_id": null,
      "created_at": "2026-08-25T13:30:00.000Z",
      "items": []
    }
  ],
  "transaction_items": [
    {
      "id": "item-301",
      "transaction_id": "trx-302",
      "item_name": "Kos Bulanan",
      "price": 2000000,
      "category": "NEEDS",
      "subcategory": "Sewa & Tempat Tinggal"
    },
    {
      "id": "item-302",
      "transaction_id": "trx-302",
      "item_name": "Iuran Lingkungan",
      "price": 200000,
      "category": "NEEDS",
      "subcategory": "Sewa & Tempat Tinggal"
    },
    {
      "id": "item-303",
      "transaction_id": "trx-303",
      "item_name": "Beras dan Telur",
      "price": 280000,
      "category": "NEEDS",
      "subcategory": "Belanja Bulanan"
    },
    {
      "id": "item-304",
      "transaction_id": "trx-303",
      "item_name": "Sayur, Lauk, dan Bumbu",
      "price": 370000,
      "category": "NEEDS",
      "subcategory": "Belanja Bulanan"
    },
    {
      "id": "item-305",
      "transaction_id": "trx-303",
      "item_name": "Sabun, Deterjen, dan Tisu",
      "price": 300000,
      "category": "NEEDS",
      "subcategory": "Belanja Bulanan"
    },
    {
      "id": "item-306",
      "transaction_id": "trx-304",
      "item_name": "Bensin",
      "price": 420000,
      "category": "NEEDS",
      "subcategory": "Transportasi"
    },
    {
      "id": "item-307",
      "transaction_id": "trx-304",
      "item_name": "Parkir dan Tol",
      "price": 210000,
      "category": "NEEDS",
      "subcategory": "Transportasi"
    },
    {
      "id": "item-308",
      "transaction_id": "trx-304",
      "item_name": "Ojek Online Saat Mendesak",
      "price": 150000,
      "category": "NEEDS",
      "subcategory": "Transportasi"
    },
    {
      "id": "item-309",
      "transaction_id": "trx-305",
      "item_name": "Listrik",
      "price": 250000,
      "category": "NEEDS",
      "subcategory": "Tagihan & Kewajiban"
    },
    {
      "id": "item-310",
      "transaction_id": "trx-305",
      "item_name": "Air",
      "price": 100000,
      "category": "NEEDS",
      "subcategory": "Tagihan & Kewajiban"
    },
    {
      "id": "item-311",
      "transaction_id": "trx-305",
      "item_name": "Internet Rumah",
      "price": 300000,
      "category": "NEEDS",
      "subcategory": "Tagihan & Kewajiban"
    },
    {
      "id": "item-312",
      "transaction_id": "trx-306",
      "item_name": "Konsultasi Dokter",
      "price": 500000,
      "category": "NEEDS",
      "subcategory": "Kesehatan"
    },
    {
      "id": "item-313",
      "transaction_id": "trx-306",
      "item_name": "Obat dan Vitamin",
      "price": 450000,
      "category": "NEEDS",
      "subcategory": "Kesehatan"
    },
    {
      "id": "item-314",
      "transaction_id": "trx-306",
      "item_name": "Tes Laboratorium",
      "price": 250000,
      "category": "NEEDS",
      "subcategory": "Kesehatan"
    },
    {
      "id": "item-315",
      "transaction_id": "trx-307",
      "item_name": "Bantuan Orang Tua",
      "price": 900000,
      "category": "NEEDS",
      "subcategory": "Keluarga"
    },
    {
      "id": "item-316",
      "transaction_id": "trx-308",
      "item_name": "Buku Referensi",
      "price": 220000,
      "category": "NEEDS",
      "subcategory": "Pendidikan & Kerja"
    },
    {
      "id": "item-317",
      "transaction_id": "trx-308",
      "item_name": "Alat Tulis dan Perlengkapan Kerja",
      "price": 280000,
      "category": "NEEDS",
      "subcategory": "Pendidikan & Kerja"
    },
    {
      "id": "item-318",
      "transaction_id": "trx-309",
      "item_name": "Premi Asuransi",
      "price": 450000,
      "category": "NEEDS",
      "subcategory": "Asuransi"
    },
    {
      "id": "item-319",
      "transaction_id": "trx-310",
      "item_name": "Kopi dan Snack",
      "price": 350000,
      "category": "WANTS",
      "subcategory": "Jajan & Nongkrong"
    },
    {
      "id": "item-320",
      "transaction_id": "trx-311",
      "item_name": "Biaya Tidak Terduga",
      "price": 300000,
      "category": "OTHER",
      "subcategory": "Lain-lain & Darurat"
    }
  ],
  "budgets": [
    {
      "id": "budget-301",
      "user_id": "user-004",
      "limit_amount": 6000000,
      "month_period": "2026-08"
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
