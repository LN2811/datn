# Tich hop thanh toan MoMo

Tai lieu nay mo ta chuc nang thanh toan MoMo trong he thong DATN, de co the giai thich lai voi giang vien ve muc dich, luong xu ly, API, database va cac diem bao mat.

## 1. Muc tieu chuc nang

Chuc nang MoMo duoc dung cho man hinh nang cap goi dich vu.

Truoc khi tich hop MoMo, khi nguoi dung bam `Chon goi`, frontend goi thang API subscribe va goi duoc nang cap ngay. Cach nay khong co buoc thanh toan.

Sau khi tich hop MoMo, luong moi la:

1. Nguoi dung bam `Chon goi`.
2. Frontend yeu cau backend tao giao dich MoMo.
3. Backend tao don thanh toan, ky chu ky HMAC SHA256 va goi API MoMo sandbox.
4. MoMo tra ve `payUrl`.
5. Frontend chuyen nguoi dung sang trang thanh toan MoMo.
6. Sau khi thanh toan, MoMo goi `ipnUrl` ve backend.
7. Backend xac thuc chu ky IPN, kiem tra so tien va trang thai.
8. Neu hop le va thanh cong, backend moi kich hoat goi cho nguoi dung.

## 2. Cac bien cau hinh

Backend doc cau hinh MoMo tu file `.env`.

```env
MOMO_PARTNER_CODE=MOMO
MOMO_ACCESS_KEY=F8BBA842ECF85
MOMO_SECRET_KEY=...
MOMO_CREATE_ENDPOINT=https://test-payment.momo.vn/v2/gateway/api/create
MOMO_REDIRECT_URL=http://localhost:5173/payment/momo/result
BACKEND_PUBLIC_URL=https://your-ngrok-url.ngrok-free.app
```

Y nghia:

- `MOMO_PARTNER_CODE`: ma doi tac MoMo.
- `MOMO_ACCESS_KEY`: access key de tao chuoi ky.
- `MOMO_SECRET_KEY`: khoa bi mat de ky HMAC SHA256. Bien nay chi nam o backend, khong dua len frontend.
- `MOMO_CREATE_ENDPOINT`: endpoint tao giao dich MoMo. Moi truong test dung `https://test-payment.momo.vn/v2/gateway/api/create`.
- `MOMO_REDIRECT_URL`: URL MoMo redirect trinh duyet nguoi dung ve sau khi thanh toan.
- `BACKEND_PUBLIC_URL`: URL public cua backend, thuong lay tu ngrok khi test local.

Neu co `MOMO_IPN_URL` thi backend dung truc tiep bien nay. Neu khong co, backend tu tao:

```txt
{BACKEND_PUBLIC_URL}/payments/momo/ipn
```

Luu y quan trong: `MOMO_IPN_URL` khong duoc la `localhost`, vi server MoMo khong the goi vao may local. Khi test local can dung ngrok.

## 3. Cac file da tich hop

Backend:

- `backend/app/core/config.py`: khai bao cac bien `MOMO_*`.
- `backend/app/services/momo_payment.py`: xu ly tao thanh toan, ky request, verify IPN va cap nhat subscription.
- `backend/app/api/route/payments.py`: khai bao cac API thanh toan.
- `backend/app/api/main.py`: include router `/payments`.
- `backend/app/models/models.py`: co model `PaymentTransactions`.
- `backend/app/alembic/versions/4b8257b3ec8e_add_table_payment.py`: migration tao bang `payment_transactions`.

Frontend:

- `frontend/src/components/upgared/upgrade.tsx`: nut `Chon goi` goi API tao thanh toan MoMo va redirect sang `payUrl`.
- `frontend/src/pages/MomoPaymentResultPage.tsx`: trang hien thi ket qua/thong tin trang thai thanh toan.
- `frontend/src/App.tsx`: them route `/payment/momo/result`.

## 4. Database

Bang `payment_transactions` luu moi giao dich MoMo.

Mot so cot quan trong:

- `user_id`: nguoi dung thanh toan.
- `plan_id`: goi dich vu muon mua.
- `amount`: so tien can thanh toan.
- `currency`: don vi tien te, hien la `VND`.
- `payment_provider`: nha cung cap thanh toan, hien la `momo`.
- `order_id`: ma don hang gui sang MoMo.
- `request_id`: ma request gui sang MoMo.
- `provider_transaction_id`: ma giao dich MoMo tra ve sau thanh toan.
- `pay_url`: URL thanh toan MoMo.
- `status`: trang thai giao dich, vi du `pending`, `paid`, `failed`, `create_failed`.
- `result_code`: ma ket qua MoMo tra ve.
- `message`: thong diep MoMo hoac thong diep loi.
- `paid_at`: thoi diem thanh toan thanh cong.

Bang nay giup he thong doi soat thanh toan, tranh viec chi dua vao redirect URL.

## 5. API backend

### 5.1. Tao thanh toan

```txt
POST /payments/momo/create
```

Request body:

```json
{
  "plan_id": "uuid-cua-goi"
}
```

Xu ly:

1. Backend lay thong tin goi trong bang `pricing_plans`.
2. Neu goi khong ton tai hoac bi tat, tra loi loi.
3. Neu gia goi bang 0, backend subscribe truc tiep khong can MoMo.
4. Neu gia goi lon hon 0, backend tao `order_id`, `request_id`.
5. Backend tao chuoi `rawSignature`.
6. Backend ky HMAC SHA256 bang `MOMO_SECRET_KEY`.
7. Backend goi MoMo create API.
8. Neu MoMo tra `payUrl`, backend luu vao `payment_transactions` va tra ve frontend.

Response thanh cong voi goi co phi:

```json
{
  "payment_required": true,
  "order_id": "...",
  "request_id": "...",
  "pay_url": "https://test-payment.momo.vn/..."
}
```

### 5.2. IPN callback

```txt
POST /payments/momo/ipn
```

Day la endpoint de MoMo goi server-to-server sau khi giao dich co ket qua.

Xu ly:

1. Backend nhan payload tu MoMo.
2. Backend tao lai chuoi ky tu payload.
3. Backend ky HMAC SHA256 bang `MOMO_SECRET_KEY`.
4. Backend so sanh chu ky tu tinh voi `signature` MoMo gui len.
5. Neu chu ky sai, tu choi request.
6. Neu chu ky dung, tim giao dich theo `orderId` va `requestId`.
7. Neu `resultCode == 0` va `amount` khop voi giao dich, danh dau `paid`.
8. Sau do goi `PricingPlanService.subscribe_plan(...)` de nang cap goi cho user.

Ly do phai dung IPN: `redirectUrl` la luong qua trinh duyet nguoi dung, co the bi tat tab, reload hoac gia lap. IPN la callback server-to-server nen dang tin cay hon de xac nhan thanh toan.

### 5.3. Kiem tra trang thai giao dich

```txt
GET /payments/momo/status/{order_id}
```

Frontend dung API nay tren trang ket qua de kiem tra giao dich da `paid`, `pending` hay `failed`.

## 6. Chu ky HMAC SHA256

Khi tao payment, backend ky chuoi theo format MoMo:

```txt
accessKey=$accessKey&amount=$amount&extraData=$extraData&ipnUrl=$ipnUrl&orderId=$orderId&orderInfo=$orderInfo&partnerCode=$partnerCode&redirectUrl=$redirectUrl&requestId=$requestId&requestType=$requestType
```

Khi nhan IPN, backend ky lai payload theo format:

```txt
accessKey=$accessKey&amount=$amount&extraData=$extraData&message=$message&orderId=$orderId&orderInfo=$orderInfo&orderType=$orderType&partnerCode=$partnerCode&payType=$payType&requestId=$requestId&responseTime=$responseTime&resultCode=$resultCode&transId=$transId
```

Neu chu ky khong khop, backend khong cap nhat subscription.

Day la diem bao mat quan trong nhat cua tich hop MoMo.

## 7. Luong frontend

Tai trang nang cap goi:

1. Frontend goi `/pricing-plans` de lay danh sach goi.
2. Frontend goi `/pricing-plans/subscriptions/me/current` de biet goi hien tai.
3. Khi nguoi dung bam `Chon goi`, frontend goi:

```txt
POST /payments/momo/create
```

4. Neu backend tra `pay_url`, frontend chuyen trang:

```ts
window.location.href = response.data.pay_url
```

5. Sau khi thanh toan, MoMo redirect ve:

```txt
http://localhost:5173/payment/momo/result
```

6. Trang ket qua doc `orderId` tu URL va goi:

```txt
GET /payments/momo/status/{order_id}
```

## 8. Cach test local

1. Chay backend port `8000`.
2. Chay frontend port `5173`.
3. Chay ngrok:

```powershell
ngrok http 8000
```

4. Lay URL HTTPS cua ngrok va sua `.env`:

```env
BACKEND_PUBLIC_URL=https://abc.ngrok-free.app
```

Hoac:

```env
MOMO_IPN_URL=https://abc.ngrok-free.app/payments/momo/ipn
```

5. Restart backend.
6. Vao frontend, dang nhap, mo trang nang cap goi.
7. Bam `Chon goi`.
8. He thong redirect sang MoMo sandbox.
9. Thanh toan test.
10. Kiem tra backend log co request:

```txt
POST /payments/momo/ipn
```

11. Neu thanh cong, subscription cua user duoc cap nhat.

## 9. Cac loi thuong gap

### Loi 500 khi goi `/payments/momo/create`

Nguyen nhan thuong gap:

- Thieu `MOMO_SECRET_KEY`.
- `BACKEND_PUBLIC_URL` van la placeholder.
- `MOMO_IPN_URL` khong phai URL public.
- Backend chua restart sau khi sua `.env`.

### MoMo khong cap nhat goi sau thanh toan

Nguyen nhan thuong gap:

- Ngrok da tat hoac URL ngrok da doi.
- `MOMO_IPN_URL` dang tro ve URL cu.
- Backend khong chay port `8000`.
- Chu ky IPN khong hop le.
- So tien MoMo tra ve khong khop voi `payment_transactions.amount`.

### Redirect ve frontend nhung van pending

Co the IPN chua ve kip hoac MoMo goi IPN that bai. Trang result co co che poll status nhieu lan, nhung backend chi cap nhat `paid` khi IPN ve thanh cong.

## 10. Diem de giai thich voi giang vien

Co the trinh bay ngan gon nhu sau:

> Em tich hop MoMo theo mo hinh server-side. Frontend khong giu secret key va khong tu xac nhan thanh toan. Khi nguoi dung chon goi, backend tao giao dich, ky HMAC SHA256 va goi API MoMo de lay payUrl. Nguoi dung thanh toan tren MoMo. Sau do MoMo goi IPN ve backend. Backend verify chu ky, kiem tra ma giao dich va so tien. Chi khi IPN hop le va resultCode thanh cong thi he thong moi kich hoat goi dich vu cho user.

Nhung diem bao mat:

- Secret key chi nam o backend.
- Khong tin redirect URL de cap nhat goi.
- Tat ca IPN phai verify HMAC SHA256.
- So tien trong IPN phai khop voi giao dich da luu.
- Moi giao dich co `order_id` va `request_id` rieng.

## 11. Gioi han hien tai

- Dang dung MoMo sandbox/test endpoint.
- Chua co man hinh admin doi soat giao dich.
- Chua co API query transaction truc tiep tu MoMo khi IPN that bai.
- Neu ngrok URL thay doi thi phai sua `.env` va restart backend.

Nhung phan cot loi cua luong thanh toan da co: tao payment, redirect MoMo, nhan IPN, verify chu ky va kich hoat subscription.
