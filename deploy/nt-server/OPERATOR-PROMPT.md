# Mango74 — prompt สำหรับรอบ deploy ถัดไป

สองส่วน: ส่วนแรกส่งให้ผู้ดูแล NT Server รันบน SSH ส่วนที่สองใช้เปิด session ใหม่
กับ AI เพื่อทำงานต่อ

---

## 1) ส่งให้ผู้ดูแล NT Server (คัดลอกทั้งบล็อก)

> **เรื่อง: เปิด route `/mango74` บน www.mangosgo.com — รอบแก้ไข**
>
> รอบที่แล้วล้มเหลวเพราะเราแก้ผิด server block ครับ ตอนนี้ `nginx -t` แจ้ง
> **duplicate `www.mangosgo.com` server name** อยู่แล้ว แปลว่ามี server block ชื่อ
> เดียวกันมากกว่าหนึ่งอัน Nginx ใช้อันที่โหลดก่อนและ **ไม่สนใจ** อันที่เหลือ
> เราไปเพิ่ม `include` ในอันที่ถูกข้าม config จึงถูกต้องตามไวยากรณ์แต่ไม่มีผลใด ๆ
> (`/mango74` ยังเป็น `404` ส่วน `/` กับ `/verse` เท่าเดิมเป๊ะ)
>
> รอบนี้ผมส่งสคริปต์ที่อ่าน config รวมจริง (`nginx -T`) แล้วบอกว่า block ไหนคือ
> ตัวที่ทำงานจริง พร้อมไฟล์และเลขบรรทัด รบกวนรันตามลำดับนี้ครับ
>
> **ขั้นที่ 1 — ตรวจไฟล์ที่อัปโหลด (อ่านอย่างเดียว)**
>
> ```bash
> sha256sum ~/mango74-vhost.py ~/mango74-static.conf
> ```
>
> ต้องได้ตรงนี้:
> `769e3f836f993353ad0874f4a0044eb8d61f4f4609e05f6e2f6965aed9a6c7bc  mango74-vhost.py`
> `1d75836affbe0b4843364eeae5cb4b6c1486e360e5ae2240ed8f1a72c0dc936a  mango74-static.conf`
> ถ้าไม่ตรง **หยุด** แล้วแจ้งกลับครับ
>
> **ขั้นที่ 2 — วินิจฉัย (ไม่แก้ไขอะไรทั้งสิ้น)**
>
> ```bash
> sudo python3 ~/mango74-vhost.py diagnose
> ```
>
> รบกวนส่งผลลัพธ์ทั้งหมดกลับมาครับ สคริปต์ปิดบัง IP ให้แล้ว
>
> **ขั้นที่ 3 — ดูแผนก่อนแก้จริง (ยังไม่เขียนไฟล์)**
>
> ```bash
> sudo python3 ~/mango74-vhost.py activate --snippet ~/mango74-static.conf
> ```
>
> **ขั้นที่ 4 — แก้จริง**
>
> ```bash
> sudo python3 ~/mango74-vhost.py activate --snippet ~/mango74-static.conf --apply
> ```
>
> สคริปต์จะสำรองทุกไฟล์ที่แตะไว้ที่ `/var/backups/mango74/<เวลา>/` รัน `nginx -t`
> ก่อน แล้วใช้ `systemctl reload nginx` (ไม่ stop) จากนั้นตรวจว่า
> `/mango74` = 308, `/mango74/` = 200, ไฟล์ asset = 200 และ `/` กับ `/verse`
> **ต้องเท่าเดิมทุกประการ** ถ้าข้อใดไม่ผ่าน มันจะคืนค่า config เดิมและ reload
> กลับให้อัตโนมัติ บรรทัดสุดท้ายที่ขึ้นต้นด้วย `PASS:` เท่านั้นคือสำเร็จ
>
> ถ้าต้องการย้อนกลับภายหลัง:
>
> ```bash
> sudo python3 ~/mango74-vhost.py rollback --backup-dir /var/backups/mango74/<เวลา>
> ```
>
> **ขอให้หยุดและแจ้งกลับทันที** ถ้าขั้นที่ 2 บอกว่าไม่พบ TLS server block ที่ตรงกับ
> host นี้ (แปลว่า TLS ไม่ได้จบที่เครื่องนี้) หรือ block ที่ทำงานจริงอยู่ในไฟล์ที่
> ทีมอื่นดูแล — กรณีนั้นต้องขออนุมัติก่อนแก้ครับ

---

## 2) เปิด session ใหม่กับ AI ด้วย prompt นี้

> ต่อจากงาน feature 005 ใน repo `3D-Generate-by-AI-Local` branch `main`
>
> สถานะ: frontend release `472d988b` วางไว้ที่ `/var/www/mango74-releases/472d988b`
> บน NT Server แล้ว และ `/var/www/mango74` ชี้ไปที่ release นั้น แต่ route
> `/mango74` ยังไม่เปิด สาเหตุคือ Nginx มี server block ชื่อ `www.mangosgo.com`
> ซ้ำกัน และรอบที่แล้วเราเพิ่ม `include` ลงใน block ที่ถูก Nginx ข้าม
>
> เครื่องมือที่เตรียมไว้แล้ว: `deploy/nt-server/mango74-vhost.py`
> (subcommand `diagnose` / `activate` / `rollback`),
> snippet `deploy/nt-server/mango74-static.conf`,
> ขั้นตอน `docs/runbooks/mango74-vhost-activation.md`
>
> ผู้ดูแล NT รันเองผ่าน SSH เท่านั้น — ห้าม AI ต่อเข้า NT Server และห้ามบันทึก
> token, credential, IP ภายใน หรือข้อมูลผู้ใช้ลง `evidence/`
>
> งานที่ต้องทำ: อ่านผล `diagnose` ที่ผู้ดูแลส่งกลับมา ยืนยันว่า block ไหนคือตัวที่
> ทำงานจริง ตัดสินใจว่าจะใช้ `--targets all-exact` หรือ `effective` แล้วบันทึกผล
> before/after ลง `evidence/feature-005/nt-frontend-deployment.md` ตามรูปแบบเดิม
> ถ้าผ่านแล้วค่อยไปต่อที่ named Cloudflare Tunnel ของ `mango74-api.mangosgo.com`
> ซึ่งเป็นการเปลี่ยนแปลงคนละชุด
