# Runbook: Mango74 public-origin reverse proxy

**Owner:** Project owner + authorized Cloudflare/origin administrators | **Frequency:** As needed  
**Last Updated:** 2026-09-11 | **Last Run:** Not run

## Purpose

เปิด `mango74-api.mangosgo.com` ผ่าน Cloudflare และ Nginx Public Origin โดยไม่ใช้
Cloudflare Tunnel เมื่อ network path ที่จำเป็นผ่านการพิสูจน์แล้ว Runbook นี้เริ่มจาก
read-only discovery และหยุดทันทีเมื่อยังไม่ทราบ origin

## Prerequisites

- [ ] สถาปัตยกรรม Public-Origin ได้รับอนุมัติแทนข้อกำหนด Tunnel ปัจจุบัน
- [ ] เจ้าของ zone ยืนยัน type/content และ rollback value ของ record `mango74-api`
- [ ] ระบุเครื่อง origin, OS, ผู้ดูแล และ management path แล้ว
- [ ] ยืนยันว่า origin รับ Cloudflare TCP `443` แบบ assign, route หรือ NAT อย่างใดอย่างหนึ่ง
- [ ] origin ติดต่อ upstream ของ Notebook ได้ด้วย address:port ที่คงที่
- [ ] local API chain ตอบ `200`
- [ ] มี certificate/key ที่ตรง `mango74-api.mangosgo.com` ผ่านช่องทางปลอดภัย
- [ ] มี backup ของ active Nginx config และระบุ rollback owner แล้ว

## Procedure

### Step 1: Capture current public behavior

จากเครื่องผู้ทดสอบ:

```powershell
Resolve-DnsName mango74-api.mangosgo.com -Type A
curl.exe -i https://mango74-api.mangosgo.com/api/v1/health/live
```

**Expected result:** บันทึก DNS edge answers และ HTTP status ปัจจุบันโดยไม่บันทึก
credential ค่า Cloudflare anycast ที่เห็นไม่ใช่ origin IP

**If it fails:** ถ้า hostname ไม่ resolve ให้เจ้าของ zone ตรวจ record ก่อน ห้ามเดา IP

### Step 2: Identify the actual origin

เจ้าของ Cloudflare เปิด DNS record `mango74-api` และแจ้งเฉพาะ type/content/proxy
status จากนั้นผู้ดูแลเครื่อง target ตรวจ listener และ effective configuration

Notebook/Windows:

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Format-Table InterfaceAlias,IPAddress,PrefixLength

Get-NetTCPConnection -State Listen -LocalPort 443 -ErrorAction SilentlyContinue
Get-CimInstance Win32_Service -Filter "Name='Local3D-Nginx'" |
  Select-Object Name,State,StartName,PathName

Find-NetRoute -RemoteIPAddress 161.200.90.3
Find-NetRoute -RemoteIPAddress 161.200.90.4
```

Ubuntu origin:

```bash
ip -brief address
sudo ss -ltnp 'sport = :443'
sudo nginx -T
```

**Expected result:** ระบุได้ว่า origin เป็น Notebook เอง (Path A) หรือเครื่องอื่น
(Path B), process ใดถือ `443` และ config จริงอยู่ไฟล์ใด

ถ้า `Find-NetRoute` เลือก default gateway แปลเพียงว่า address เป็น remote destination
จาก Notebook ไม่ได้ระบุว่า router/firewall ตัวใดของมหาวิทยาลัยเป็นเจ้าของ public IP
ข้อมูลนั้นต้องตรวจจาก Cloudflare origin record และระบบ IPAM/NAT ของ Network Admin

**If it fails:** หยุดและขอผู้ดูแล origin; ห้ามติดตั้ง Nginx ตัวที่สองหรือแก้ vhost
ที่เดาเอง

อย่าสับสน public egress กับ public ingress: address ที่บริการตรวจ IP แสดงเพียงบอก
ว่า outbound traffic ออก NAT จุดใด ไม่ได้พิสูจน์ว่า address นั้น bind อยู่บน Notebook
หรือรับ port-forward กลับมาได้

### Step 3: Prove the upstream before exposing it

Path A — Nginx และ FastAPI อยู่บน Notebook เดียวกัน:

```powershell
curl.exe -i http://127.0.0.1:8000/api/v1/health/live
curl.exe -i http://127.0.0.1:8080/api/v1/health/live `
  -H "Host: mango74-api.mangosgo.com"
```

Path B — รันจาก Public Origin โดยแทนค่าด้วย stable private address ที่ได้รับอนุมัติ:

```bash
curl -i --connect-timeout 5 \
  -H 'Host: mango74-api.mangosgo.com' \
  http://<APPROVED_NOTEBOOK_ADDRESS>:8080/api/v1/health/live
```

**Expected result:** `200` และ body ระบุสถานะพร้อม โดยไม่มี internal detail

**If it fails:** แก้ private route/VPN/listener/firewall ก่อน Nginx Public Origin
ห้ามใช้ `172.20.10.6` หรือ address hotspot อื่นเป็น production upstream

### Step 4: Prepare the exact Nginx virtual host

เลือก upstream เพียงหนึ่งแบบ:

- Path A: `127.0.0.1:8000`
- Path B: `<APPROVED_NOTEBOOK_ADDRESS>:8080`

นำ server block ต่อไปนี้ไปปรับในไฟล์ active ที่พบจาก Step 2 อย่า copy certificate
หรือ private key เข้า repository

```nginx
upstream mango74_api_backend {
    server <SELECTED_UPSTREAM>;
    keepalive 8;
}

server {
    listen <LOCAL_ORIGIN_ADDRESS>:443 ssl;
    server_name mango74-api.mangosgo.com;

    ssl_certificate     <ORIGIN_CERTIFICATE_PATH>;
    ssl_certificate_key <ORIGIN_PRIVATE_KEY_PATH>;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:Mango74TLS:10m;
    ssl_session_timeout 1d;

    server_tokens off;
    client_max_body_size 10m;
    client_body_timeout 30s;

    location = / {
        return 404;
    }

    location ^~ /api/ {
        proxy_pass http://mango74_api_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Connection "";
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location / {
        return 404;
    }
}
```

`<LOCAL_ORIGIN_ADDRESS>` ต้องเป็น address ที่มีอยู่บนเครื่อง Nginx จริง หาก public
IP ทำ NAT อยู่ที่ firewall ให้ใช้ local address ที่ NAT ส่งเข้ามา ไม่ใช่ public IP
ที่ไม่ได้ bind บนเครื่อง

**Expected result:** vhost รับเฉพาะ hostname และ `/api/*`; FastAPI/ComfyUI ยังไม่
เปิด public listener

**If it fails:** คืนไฟล์ backup และตรวจ duplicate `server_name`, port ownership,
certificate path และ upstream reachability

### Step 5: Validate and reload without stopping Nginx

Ubuntu:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Windows ให้ใช้ executable/prefix/config ที่แสดงใน service `PathName`; ตัวอย่างจาก
runtime ปัจจุบัน:

```powershell
& 'C:\ProgramData\Local3D\nginx\nginx.exe' `
  -p 'C:\ProgramData\Local3D\nginx' `
  -c 'C:\ProgramData\Local3D\nginx\nginx.conf' -t
```

หลัง validation ผ่าน ให้ผู้ดูแล reload ด้วยกลไกเดียวกับ service ที่ติดตั้งจริง
ห้าม stop production Nginx เพื่อทดลอง

**Expected result:** syntax test ผ่านและ process เดิม reload configuration สำเร็จ

**If it fails:** อย่า reload; คืน config backup แล้วทดสอบอีกครั้ง

### Step 6: Validate origin TLS and local routing

จาก origin ให้ใช้ local address ที่ listener bind อยู่:

```bash
openssl s_client \
  -connect <LOCAL_ORIGIN_ADDRESS>:443 \
  -servername mango74-api.mangosgo.com </dev/null

curl -k -i \
  --resolve mango74-api.mangosgo.com:443:<LOCAL_ORIGIN_ADDRESS> \
  https://mango74-api.mangosgo.com/api/v1/health/live
```

`curl -k` ใช้เฉพาะทดสอบ local routing เพราะ Cloudflare Origin CA อาจไม่อยู่ใน
public trust store; การยอมรับ production certificate ให้ตัดสินจาก Cloudflare
Full (strict) และการตรวจ certificate chain/SAN แยกต่างหาก

**Expected result:** certificate ไม่หมดอายุและครอบคลุม hostname; local health ตอบ
`200`

**If it fails:** แก้ certificate chain/SAN หรือ vhost ก่อนแตะ DNS

### Step 7: Apply Cloudflare and firewall boundary

เจ้าของ zone คง record `mango74-api` เป็น **Proxied** และชี้ target ที่ยืนยันแล้ว
พร้อมคง SSL/TLS mode เป็น **Full (strict)** ผู้ดูแล network อนุญาต origin TCP `443`
จาก [Cloudflare IP ranges](https://www.cloudflare.com/ips/) ตาม policy ปัจจุบัน
และไม่เปิด `8000`, `8080`, `8188` หรือ management ports สู่ Internet

**Expected result:** Cloudflare ติดต่อ origin TLS ได้ โดย backend ports ยังเป็น private

**If it fails:** ห้ามลดเป็น Flexible หรือเปิด backend ports เพื่อแก้ลัด

### Step 8: Verify end to end

จาก independent network:

```bash
curl -i https://mango74-api.mangosgo.com/api/v1/health/live

curl -i -X OPTIONS \
  https://mango74-api.mangosgo.com/api/v1/jobs \
  -H 'Origin: https://www.mangosgo.com' \
  -H 'Access-Control-Request-Method: POST'
```

เปิด `https://www.mangosgo.com/mango74/` และทดสอบ create, status, cancel, preview
และ download ด้วยงานทดสอบที่อนุมัติ

**Expected result:** health `200`, CORS อนุญาต exact production origin และ browser
ใช้ AI ได้ผ่าน public API URL เดิม

**If it fails:** ใช้ตาราง Troubleshooting ก่อน rollback

## Verification

- [ ] public health ตอบ `200` แทน `526`
- [ ] certificate origin ผ่าน Full (strict)
- [ ] exact production CORS origin ผ่าน; origin อื่นไม่ผ่าน
- [ ] real AI job ครบวงจรและไม่เผย internal address
- [ ] ไม่มี public application response บน `8000`, `8080`, `8188`
- [ ] unrelated routes ของ `www.mangosgo.com` ไม่เปลี่ยน
- [ ] reload/restart recovery คืนบริการที่ URL เดิม

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `526` | origin certificate ไม่ผ่าน Full (strict) | ตรวจ expiry, SAN, chain, vhost และ certificate ที่ listener `443` เสิร์ฟจริง |
| `522`/`523` | Cloudflare ไป origin ไม่ได้หรือ route ผิด | ตรวจ DNS target, NAT/route, listener และ firewall `443` |
| `502` | Nginx ถึง upstream ไม่ได้ | ทดสอบ Step 3 จากเครื่อง Nginx และแก้ private route/listener |
| local `200`, public `526` | local route ถูกแต่ origin TLS ผิด | แก้ certificate/chain/SNI; ไม่ลด SSL mode |
| health `200`, browser CORS error | FastAPI allowlist/preflight ไม่ตรง | ตรวจ exact origin `https://www.mangosgo.com` และ required headers/methods |
| ping ผ่านแต่ HTTPS พัง | ping ตอบจาก Cloudflare edge | วินิจฉัย origin ด้วย HTTP status ไม่ใช่ ping |

## Rollback

1. คืน active Nginx files จาก backup ที่บันทึกไว้
2. รัน `nginx -t` แล้ว reload ด้วยกลไกเดิม
3. ถ้า DNS ถูกเปลี่ยน ให้เจ้าของ zone คืนค่า record/target เดิมจาก rollback record
4. ตรวจว่า path อื่นของ `www.mangosgo.com` ไม่เปลี่ยน
5. ถ้าจะกลับไป Tunnel ให้ทำเฉพาะเมื่อ route เดิมยังได้รับอนุมัติและ credential ไม่รั่ว

## Escalation

| Situation | Contact | Method |
|---|---|---|
| ไม่ทราบ DNS target/rollback | `mangosgo.com` Cloudflare owner | approved secure channel |
| ไม่ทราบว่า public IP assign/route/NAT อย่างไร | University Network Admin | change/request channel |
| ไม่ทราบ process ที่ถือ `443` หรือ active Nginx file | Origin/NT administrator | SSH or console session run by administrator |
| local AI chain ไม่ตอบ | Mango74 backend operator | local service runbook |
| ต้องเปลี่ยน architecture จาก Tunnel | Project owner | approve constitution/spec amendment |

## History

| Date | Run By | Notes |
|---|---|---|
| 2026-09-11 | Codex + operator | Initial proposal; discovery not yet run on the authorized Public Origin |
