# Feature 004 — คู่มือเครื่อง AI แบบ Single-Node

นี่คือคู่มือปัจจุบันของ feature 004 เครื่อง Notebook/PC ที่ได้รับ IP
`161.200.90.4` เป็น server เพียงเครื่องเดียว และรัน ComfyUI, FastAPI,
Frontend, Caddy และงานบน RTX 5070 ทั้งหมด

## ขอบเขตที่ห้ามเปลี่ยน

```text
ผู้ใช้ -> HTTPS ชั่วคราว -> Cloudflare Quick Tunnel
-> cloudflared (ขาออก) -> Caddy 127.0.0.1:8080
-> Web 127.0.0.1:3000 / API 127.0.0.1:8000
-> ComfyUI 127.0.0.1:8188 -> RTX 5070
```

ห้ามเพิ่ม Edge Server, WireGuard, port forwarding, DNS สาธารณะ, custom
hostname หรือ inbound firewall rule IP นี้เป็นเพียง IP ของเครื่อง ไม่ใช่ URL
ของแอป FastAPI และ ComfyUI ต้องไม่รับ connection จาก Internet โดยตรง

## ตรวจสอบก่อนเปิด Quick Tunnel

```powershell
Get-Service Local3D-ComfyUI,Local3D-API,Local3D-Web,Local3D-Caddy
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/health_chain.ps1 -Json
```

ลำดับที่คาดหวังคือ ComfyUI → API → Web → Caddy และ listener ต้องเป็น
`127.0.0.1:8188`, `127.0.0.1:8000`, `127.0.0.1:3000`, `127.0.0.1:8080`
เท่านั้น หากพบ `0.0.0.0` หรือ IP ที่ได้รับมอบหมายให้หยุดทันที

ตรวจ Caddy ด้วย `API_UPSTREAM=http://127.0.0.1:8000`,
`WEB_UPSTREAM=http://127.0.0.1:3000` และทดสอบ `/`,
`/api/v1/health/live`, `/api/v1/health/ready`, `/api/v1/health/engine`
ผ่าน `http://127.0.0.1:8080`

## Quick Tunnel สำหรับทดสอบเท่านั้น

เมื่อ local chain พร้อมแล้วจึงรัน:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/start_quick_tunnel.ps1 -CloudflaredPath cloudflared
```

ใช้เฉพาะ URL สุ่ม `https://<random>.trycloudflare.com` ที่แสดงใน session นั้น
URL นี้เป็น public และชั่วคราว ไม่ใช่การยืนยันตัวตน ห้ามบันทึกลง Git ห้ามสร้าง
DNS ห้ามใช้ named tunnel และห้ามชี้ไปที่ port อื่นนอกจาก
`http://127.0.0.1:8080`

ตัว launcher จะแสดง `TEMPORARY NON-PRODUCTION URL` เพียงหนึ่ง URL ต่อ session
ให้ใช้ URL บรรทัดนี้เท่านั้น URL จากรอบก่อนอาจแสดง Cloudflare Error 1033 เมื่อ
connector เดิมหยุดทำงาน หากเปิด Tunnel จาก PowerShell แบบ Administrator แล้ว
หยุดจากหน้าต่างปกติไม่ได้ ให้รัน:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/stop_quick_tunnel.ps1 -Elevate
```

## การแก้ปัญหาและการ restart

อ่านผล `health_chain.ps1 -Json` แล้วแก้เฉพาะ layer ที่เสีย ห้าม resubmit งาน
ComfyUI ที่ไม่แน่ใจโดยอัตโนมัติ งานที่บันทึกแล้วต้องไม่ถูกแสดงว่าเสร็จสำเร็จ
จนกว่าจะตรวจ output ใหม่ Logs บันทึกได้เฉพาะ request ID, safe job ID,
transition, duration และ failure category ห้ามมี token, header, path ส่วนตัว,
engine ID, URL ชั่วคราว หรือข้อมูลผู้ใช้

การ reboot เป็นงานของ operator หลังเครื่องกลับมาต้องตรวจ service ทั้งสี่,
listener แบบ loopback, GPU, storage/workflow, การกู้ job และ listener boundary
ก่อนเริ่ม Quick Tunnel ใหม่ ห้ามถือว่าการ reboot ผ่านหากยังไม่ได้ reboot จริง

Custom hostname ใช้ได้เมื่อได้รับอนุญาตโดเมนอย่างชัดเจนเท่านั้น การซื้อโดเมน,
แก้ DNS และเพิ่ม server ไม่อยู่ในขอบเขตนี้
