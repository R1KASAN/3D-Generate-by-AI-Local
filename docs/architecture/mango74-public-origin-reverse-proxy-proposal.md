# Mango74 public-origin reverse-proxy proposal

**Status:** Proposed; not yet approved or activated  
**Last updated:** 2026-09-11

## Purpose

ทดสอบแนวคิดของผู้ดูแลว่า AI Notebook สามารถเป็น server ได้โดยตรง และใช้ Nginx
Reverse Proxy แทนการบังคับใช้ Cloudflare Tunnel โดยยังคง public contract เดิม:

- Frontend: `https://www.mangosgo.com/mango74/`
- API: `https://mango74-api.mangosgo.com/api/*`

ข้อเสนอนี้ไม่อนุญาตให้แก้ DNS, firewall, TLS หรือ live Nginx จนกว่าจะระบุ Public
Origin และเส้นทางถึง Notebook ได้จากหลักฐานจริง

## Core decision

Cloudflare Tunnel และ Nginx ไม่ได้ทำหน้าที่เดียวกัน:

- Public IP/NAT/private route/Tunnel สร้าง **network reachability**
- Nginx ทำ **HTTP reverse proxy and routing** หลัง request มาถึงเครื่องแล้ว

วิธีที่สั้นที่สุดคือ Path A หากคำกล่าวว่า "Notebook คือ server" หมายถึง Notebook
เป็น Public Origin จริง

### Path A — Notebook is the Public Origin

```text
Browser
  -> mango74-api.mangosgo.com
  -> Cloudflare proxy
  -> confirmed Public IP/NAT :443
  -> Nginx on AI Notebook
  -> FastAPI 127.0.0.1:8000
  -> ComfyUI 127.0.0.1:8188
  -> RTX 5070
```

Path A ใช้ได้เมื่อครบทุกข้อ:

1. DNS record ปัจจุบันชี้ Public IP ที่จัดสรรให้ Notebook หรือ NAT มาที่ Notebook
2. Cloudflare เข้าถึง TCP `443` ของ origin ได้
3. Nginx ที่ origin มี certificate สำหรับ `mango74-api.mangosgo.com`
4. Nginx ส่ง `/api/*` ไป FastAPI ผ่าน loopback ได้
5. Notebook อยู่ในตำแหน่งเครือข่ายที่ทำให้ IP/route นั้นคงที่ตลอดเวลาที่ให้บริการ

### Path B — A separate machine is the Public Origin

```text
Browser
  -> mango74-api.mangosgo.com
  -> Cloudflare proxy
  -> confirmed Public Origin :443
  -> Nginx on Public Origin
  -> proven stable private path
  -> Nginx 8080 or FastAPI 8000 on AI Notebook
```

Path B ต้องมี private route ที่ Public Origin เริ่มเชื่อมต่อไป Notebook ได้และต้องใช้
address ที่คงที่ เช่น approved routed VLAN หรือ point-to-point VPN address การมี
FortiClient VPN ฝั่ง Notebook เพียงอย่างเดียวไม่พิสูจน์ว่า server อีกฝั่งสามารถเริ่ม
connection กลับเข้ามาได้

## Evidence observed on 2026-09-11

| Observation | Meaning |
|---|---|
| Notebook เคยมี `172.20.10.6/28` บน hotspot และล่าสุดมี `10.203.66.232/16` บน Wi-Fi | private address เปลี่ยนตามเครือข่าย จึงใช้เป็น production target โดยไม่จอง/route ไม่ได้ |
| เว็บไซต์ตรวจ IP สามแห่งแสดง egress `161.200.189.83` ล่าสุด | เป็น NAT/egress observation ไม่ใช่หลักฐานว่า address bind บน Notebook หรือรับ inbound ได้ |
| ไม่พบ `161.200.90.3` หรือ `161.200.90.4` บน adapter ของ Notebook | Path A ยังไม่ผ่านเงื่อนไขขณะตรวจ |
| route lookup ของ `.3` และ `.4` ออกจาก Notebook ผ่าน default gateway `10.203.255.254` | ทั้งสอง address เป็น remote destination จากมุมมอง Notebook ไม่ใช่ local interface |
| Runtime Nginx config ผ่าน `nginx -t`, ฟัง `127.0.0.1:8080` และ proxy `/api/` ไป `127.0.0.1:8000`; ไม่พบ listener `443` | Reverse Proxy ภายในพร้อมแล้ว แต่ Public-Origin ingress/TLS ยังไม่มี |
| `mango74-api.mangosgo.com` resolve เป็น Cloudflare anycast | DNS proxy/edge มีอยู่แล้ว แต่ไม่เปิดเผย origin |
| public health endpoint ตอบ `526` | Cloudflare ตรวจ certificate ของ origin ไม่ผ่านใน Full (strict) |

`526` เป็นเบาะแสสำคัญว่าไม่ควรเริ่มจากการสร้าง subdomain ใหม่ แต่ควรให้เจ้าของ zone
ระบุ record/origin ปัจจุบัน และตรวจ certificate/virtual host บน origin นั้นก่อน
อย่างไรก็ตาม `526` ไม่ได้พิสูจน์ว่า origin นั้นคือ Notebook เครื่องนี้

Mapping แบบ `161.200.90.x:<public-port> -> 172.20.10.6:8080` ใช้ได้เฉพาะเมื่อ
gateway ที่ถือ public IP เป็น gateway/NAT ของ Notebook หรือมี explicit route ถึง
private subnet นั้น ค่า `172.20.10.6` ที่มาจาก hotspot คนละ gateway ไม่ใช่ target
ที่ university firewall จะ forward ถึงได้เอง และเมื่อ Notebook เปลี่ยนเครือข่ายค่า
ดังกล่าวก็หายไป

Public DNS lookup จากภายนอกไม่สามารถบอกได้ว่า Cloudflare record ชี้ router/firewall
ตัวใด เพราะ Proxied record คืน Cloudflare anycast address การหาอุปกรณ์จริงต้องเริ่ม
จากค่า origin ใน Cloudflare Dashboard แล้วให้ Network Admin ตรวจ IPAM, route,
ARP/VIP และ NAT policy ของ address นั้น

## Information required from the owner

ขอข้อมูลที่ไม่ใช่ความลับเพียงห้ารายการ:

1. record `mango74-api` เป็น A, AAAA หรือ CNAME และค่า origin/target ปัจจุบันคืออะไร
2. เครื่องหรือ firewall ใดเป็นเจ้าของ target นั้น
3. ใครมีสิทธิ์ดู `nginx -T`, listener `443` และ certificate บน origin
4. ถ้า origin ไม่ใช่ Notebook จะใช้ IP:port ใดที่ origin ติดต่อ Notebook ได้จริง
5. `443` มาถึงเครื่องโดย assign ตรง, route หรือ NAT และใครดูแล firewall rule

ไม่ต้องขอ Cloudflare password, Connector Token หรือ TLS private key ทางแชต

## Decision table

| Result of discovery | Decision |
|---|---|
| Public target ผูก/NAT มาที่ Notebook และ `443` เปิดตามสิทธิ์ | ใช้ Path A; Tunnel ไม่จำเป็น |
| Public target อยู่ NT/edge และมี stable private route ไป Notebook | ใช้ Path B หลังอนุมัติการเปลี่ยนขอบเขต NT/edge |
| Public target อยู่เครื่องอื่นแต่ไม่มี route ไป Notebook | Reverse Proxy อย่างเดียวใช้ไม่ได้; สร้าง private path หรือใช้ Tunnel |
| Notebook ได้เพียง hotspot/CGNAT address | ใช้ direct Public-Origin ไม่ได้จากเครือข่ายนั้น |
| ไม่ทราบ DNS target หรือ origin owner | หยุดก่อนแก้ config เพราะยังระบุเครื่องปลายทางไม่ได้ |

## Security and operations

- Internet ต้องเข้าถึงเฉพาะ origin `443`; ห้ามเปิด `8000`, `8080` หรือ `8188`
- จำกัด origin `443` ให้ Cloudflare source ranges เมื่อ network policy รองรับ
- ใช้ TLS 1.2/1.3 และ certificate ที่ตรง hostname; คง Cloudflare `Full (strict)`
- สำรอง active Nginx configuration และ certificate references ก่อนเปลี่ยน
- รัน `nginx -t` ก่อน reload และ rollback เฉพาะ virtual host ของ Mango74
- CORS อนุญาต exact browser origin `https://www.mangosgo.com`; CORS ไม่ใช่ network
  access control หรือ authentication
- log ต้องไม่บันทึก job token, secret, request body, local filesystem path หรือ AI input

## Governance impact

Constitution v5.0.0 และ Feature 005 ปัจจุบันกำหนด named Cloudflare Tunnel เป็น
production path การเลือก Path A หรือ Path B จึงเป็น architecture change ต้องได้รับ
การอนุมัติและปรับ constitution/spec/plan/tasks ก่อนประกาศว่า production cutover
เสร็จแล้ว เอกสารนี้เป็น proposal และ evidence plan ไม่ใช่การอนุมัติโดยปริยาย

Migration คือพิสูจน์ origin -> สำรอง -> ติดตั้ง TLS/vhost -> ทดสอบ local origin ->
ทดสอบ Cloudflare -> ทดสอบ browser จริง ส่วน rollback คือคืน Nginx/DNS เดิมและเปิด
Tunnel path เดิมเฉพาะเมื่อเจ้าของอนุมัติให้เป็น fallback

## Acceptance criteria

- `https://mango74-api.mangosgo.com/api/v1/health/live` ตอบ `200`
- preflight จาก `https://www.mangosgo.com` ผ่าน แต่ origin อื่นถูกปฏิเสธ
- browser สร้างงาน ดูสถานะ ยกเลิก preview และ download ผ่าน public API เดียวกัน
- public scan ไม่พบ application response บน `8000`, `8080` หรือ `8188`
- restart Nginx/FastAPI/ComfyUI แล้ว URL เดิมกลับมาโดยไม่เปลี่ยน frontend build
- rollback ไม่กระทบ path อื่นของ `www.mangosgo.com`

ดูขั้นตอนปฏิบัติที่
[`docs/runbooks/mango74-public-origin-reverse-proxy.md`](../runbooks/mango74-public-origin-reverse-proxy.md)
และ mental model ที่
[`docs/reference/proxy-concepts-and-mango74-routing.md`](../reference/proxy-concepts-and-mango74-routing.md)
