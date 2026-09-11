# Proxy concepts and Mango74 routing

เอกสารนี้เก็บ mental model สำหรับวิเคราะห์เส้นทางของ Mango74 โดยไม่ผูกคำตอบไว้กับ
เครื่องมือชนิดใดชนิดหนึ่ง

## Forward Proxy กับ Reverse Proxy

Proxy คือตัวกลางระหว่าง client และ server แต่สองแบบนี้ปกป้องคนละฝั่ง

| ประเด็น | Forward Proxy | Reverse Proxy |
|---|---|---|
| อยู่ฝั่งใด | ฝั่ง client/ผู้ใช้งาน | ฝั่ง application/server |
| ทำหน้าที่แทนใคร | ทำ request แทน client | รับ request แทน backend |
| ซ่อนอะไร | ซ่อน client จาก server ปลายทาง | ซ่อน backend และพอร์ตภายในจาก client |
| งานที่พบบ่อย | กรองเว็บ, ควบคุม outbound, cache, privacy | TLS termination, routing, load balancing, rate limiting |
| ตัวอย่าง | corporate web proxy | Nginx หน้า FastAPI |

Nginx ในโปรเจกต์นี้เป็น **Reverse Proxy**: browser รู้จักเพียง
`mango74-api.mangosgo.com`; Nginx เป็นผู้เลือกว่าจะส่ง `/api/*` ไปที่ FastAPI
ใดและพอร์ตใด

## แยกปัญหาเป็นสองชั้น

สิ่งที่มักทำให้สับสนคือ **reachability** และ **HTTP routing** เป็นคนละปัญหา

1. Reachability: request จาก Cloudflare เดินทางถึงเครื่องที่รัน Nginx ได้อย่างไร
   เช่น public IP โดยตรง, NAT, private network หรือ Cloudflare Tunnel
2. HTTP routing: เมื่อ request ถึง Nginx แล้ว จะส่ง path ใดไป backend ใด
   เช่น `location /api/` และ `proxy_pass http://127.0.0.1:8000`

Reverse Proxy แก้ชั้นที่ 2 เป็นหลัก มันไม่ได้สร้างเส้นทางเครือข่ายไปยัง upstream
ที่เข้าไม่ถึง ส่วน Cloudflare Tunnel แก้ชั้นที่ 1 ด้วยการให้ connector เชื่อมออกจาก
Notebook ไป Cloudflare

ดังนั้น Tunnel ไม่จำเป็นเมื่อมี Public Origin ที่รับ Cloudflare บน `443` และ
Public Origin นั้นเข้าถึง FastAPI ได้จริง แต่ถ้าไม่มี public ingress, NAT หรือ
private route ที่ใช้งานได้ การเพิ่ม `proxy_pass` เพียงอย่างเดียวจะไม่ทำให้ request
ไปถึง Notebook

ตัวอย่าง DNAT/port-forward เช่น
`161.200.90.x:<public-port> -> 172.20.10.6:8080` จะถูกต้องก็ต่อเมื่อ gateway ที่
ถือ `161.200.90.x` มี route ถึง `172.20.10.6` และเป็นผู้ทำ NAT ให้ address นั้นจริง
หาก `172.20.10.6` มาจาก mobile hotspot คนละเครือข่าย gateway ของมหาวิทยาลัยจะ
ส่ง packet ไป address ดังกล่าวไม่ได้โดยอัตโนมัติ Reverse Proxy ไม่ได้แก้ข้อจำกัดนี้

## โมดูลของ Mango74

| โมดูล | หน้าที่ | ไม่ได้ทำอะไร |
|---|---|---|
| Frontend ที่ `/mango74/` | UI ใน browser และเรียก public API | ไม่ได้รัน AI และไม่ควรเรียก `localhost` ของ Notebook |
| DNS | บอกว่า hostname เริ่มต้นไปที่บริการใด | ไม่มีช่องกำหนด upstream port และไม่ทำ reverse proxy |
| Cloudflare proxy | รับ HTTPS จากผู้ใช้ ป้องกัน edge และเชื่อมต่อ origin | ไม่ได้รู้เองว่า FastAPI อยู่พอร์ตใด |
| Nginx | รับ hostname/path แล้วส่งต่อไป upstream | ติดต่อ upstream ที่ไม่มี route ให้ไม่ได้ |
| FastAPI | ตรวจ request จัดการงาน และคืนสถานะ/ผลลัพธ์ | ไม่ควรเปิดสู่ Internet โดยตรง |
| ComfyUI | รัน workflow การสร้าง 3D/AI | ไม่ใช่ public API สำหรับ browser |
| RTX 5070 | ประมวลผลงาน AI | ไม่เกี่ยวกับ DNS หรือ TLS |
| CORS | อนุญาต origin ของ browser ที่กำหนด | ไม่สร้าง DNS, route, NAT หรือ authentication |
| Cloudflare Tunnel | สร้าง outbound path จาก Notebook ไป Cloudflare | ไม่แทน FastAPI หรือการ route path ของ Nginx |

## กฎที่ใช้ตัดสินใจ

- การมี subdomain หมายความเพียงว่ามีชื่อเรียก ไม่ได้พิสูจน์ว่ามี backend ที่ใช้งานได้
- Ping ไป IP ของ Cloudflare พิสูจน์ได้เพียงว่า DNS/edge ตอบ ไม่ได้พิสูจน์ว่า edge
  ติดต่อ Notebook สำเร็จ
- Public Origin ต้องมี `443` ที่ Cloudflare เข้าถึงได้ มี TLS certificate ตรง hostname
  และมี route ถึง upstream
- ถ้า Nginx กับ FastAPI อยู่เครื่องเดียวกัน ให้ใช้ loopback เป็น upstream ซึ่งง่ายและ
  ลดพื้นที่โจมตีที่สุด
- ถ้า Nginx กับ FastAPI อยู่คนละเครื่อง ต้องใช้ IP ที่คงที่และเส้นทางที่พิสูจน์แล้ว
  ห้ามใช้ IP ของ mobile hotspot เป็น production upstream
- public egress IP ที่เว็บไซต์ตรวจ IP แสดง ไม่เท่ากับ public ingress IP และไม่ได้
  แปลว่าเครื่องรับ connection จาก Internet ที่ address นั้นได้
- ควรใช้ Cloudflare `Full (strict)` และแก้ certificate ที่ origin ไม่ควรลดความเข้มงวด
  เพื่อซ่อนปัญหา

## แหล่งอ้างอิง

- [Nginx HTTP proxy module](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [Cloudflare Full (strict)](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/)
- [Cloudflare Error 526](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-526/)
