# README

### 期中的 DEMO 我們用虛擬機模擬了：
- 網路的 bonding
- LVS/NAT + KeepAlived

### 這次的 DEMO 目標：
- 高可用 DNS 架構：透過 CoreDNS 架設 DNS Server 搭配健康檢查，確保服務的可用性。
- Nginx 負載平衡實作：使用 Nginx 反向代理（proxy）機制，將流量平均分配至後端伺服器，提升整體系統的效能與可靠性。
- 


## 架構圖

![image](https://hackmd.io/_uploads/Bkp3b-1mxx.png)

### 你需要的資源有
- 自己的 Domain Name
    - 我是去 [Namecheap](https://www.namecheap.com/?gad_source=1&gad_campaignid=11301910042&gbraid=0AAAAADzFe20XQgMQrhywrqM3nu8zaNt6G&gclid=Cj0KCQjwjJrCBhCXARIsAI5x66XO7v_X6oIwHCxBFd9HZ5AO39WEkpXo3wqQvt1j_d7RuEjJgUTxggYaAvdiEALw_wcB) 買的，最便宜的只要 37 塊台幣
- 自己的 DNS Server
    - 我是用 CoreDNS 架的
- 一個雲端服務供應商的帳號，還有多台虛擬機
    - 我是用 DigitalOcean 申請七台
        - DigitalOcean 申請帳號需要信用卡，[BT 的邀請連結](https://www.digitalocean.com/?refcode=7a14e0e84052&utm_campaign=Referral_Invite&utm_medium=Referral_Program&utm_source=CopyPaste)可以拿到點數，申請 [Github 的學生身分](https://education.github.com/pack)也可以拿到點數。
        - 這邊要注意一點：因為 DigitalOcean 有 Droplet 只能申請三台的限制，要寫信請他們把你的限制調高（我是說明自己正在做關於高可用性的期末報告，然後他們就把我的限制提高到十台了XD）。

## 詳細方法

### Domain name glue
- 其實是建議架好 DNS server 以後再做 glue 的動作啦，但因為他傳播出去需要一段時間，所以如果很確定自己的 DNS server 就是這台也可以先 glue
- 每個域名商的頁面都不太一樣，這邊是以 Namecheap 示範
- 先去你域名註冊商的頁面，找到你管理域名的地方
![image](https://hackmd.io/_uploads/rkcVuDHXxe.png)
- 去 Advanced DNS 頁面
![image](https://hackmd.io/_uploads/HyH4cDSXeg.png)
- 新增一個 Nameserver
![image](https://hackmd.io/_uploads/rJeR9vH7lg.png)
- 總共要加兩次，第一台選 ns1，第二台就選 ns2，然後把 IP 填進去
![image](https://hackmd.io/_uploads/rJLuivSmgg.png)
- 好了以後點 SEARCH 就可以看到你剛剛新增的兩個 IP
![image](https://hackmd.io/_uploads/SyYe3wSmle.png)
- 回到 Domain 把 NAMESERVERS 改成 Custom DNS，加你剛剛新增的那兩個 Nameserver
![image](https://hackmd.io/_uploads/BkcjnwBmeg.png)

- 好了就會跳出通知，提醒你需要兩天左右的時間才會正確的將所有查詢都導到你的 DNS server，然後就可以來架 DNS server 啦！




### DNS Server
![image](https://hackmd.io/_uploads/BJ2mG-1mxe.png)

- DNS sevrer 要有兩台，兩台的操作方式大致上都一樣。
- 創建一個資料夾（這邊建議名字就叫 CoreDNS 就好，然後放在根目錄下面，不然後續指令要改有點麻煩）
![image](https://hackmd.io/_uploads/r1SmVDSXgl.png)


- 首先講 Corefile，裡面的內容是 CoreDNS 的設定，內容如下：
    ```
    .:53 {
    bind 0.0.0.0 127.0.0.1
    cache 5
    reload 5s
    log
    file /zones/db.kunzo.space kunzo.space. {
        reload 5s
    }
    }
    ```
    
    - `.:53`：監聽所有 IPv4 跟 IPv6 的 53 port（因為 DNS 預設是會跑在這個 port）
    - `bind 0.0.0.0 127.0.0.1`：指定綁哪個 IP，這樣會讓 CoreDNS 綁在
        - 所有的 IPv4 網卡（讓外部的主機可以查這台 DNS）
        - 本機位址（內部測試用的，但如果是用 docker 其實不加也可以）
    - `cache 5`：DNS 快取 TTL 設定為 5 秒（為了要可以很快地看到轉換結果，如果接下來有想要正式使用的話，建議調到 30 或 60，避免帶給環境太大的負擔。
    - `reload 5s`：每五秒檢查設定檔有沒有變，會自動重載
    - `log`：啟用查詢紀錄，如果在運作過程中有什麼錯誤會比較好 debug
    - `file /zones/db.kunzo.space kunzo.space.`：用 file 外掛的方式載入 zone 檔，檔案是 /zones/db.kunzo.space，管理 kunzo.space. 的紀錄
    ::: info
    補充：為什麼要在 Domain name 後面再加一個 . ？
    - 代表 FQDN（Fully Qualified Domain Name，中文譯為完整網域名稱），避免系統幫你在後面補上上層字尾，變成像是 kunzo.space.com 之類的網域名稱
    :::
- 接著去到 zones 那個檔資料夾，裡面有一個 db.<你的 Domain name> 的檔案，github 裡面的我還沒放東西，但只要開始執行以後他就會出現以下的東西（以我的檔案做舉例）：
    ```
    $ORIGIN .
    $TTL 5      ; 1 day
    kunzo.space             IN SOA  ns1.kunzo.space. rachelsun5.gmail.com. (
                                    2025061033 ; serial
                                    5       ; retry (30 minutes)
                                    300    ; expire (2 weeks)
                                    5      ; minimum 
                                    )
    kunzo.space             IN NS      ns1.kunzo.space.
    kunzo.space             IN NS      ns2.kunzo.space.
    $ORIGIN kunzo.space.
    ns1                     IN A       209.97.161.115
    ns2                     IN A       159.203.21.136
    $TTL 5 ; 1 minute
    @                      IN A       146.190.147.94
    www                    IN A       146.190.147.94
    ```
    - serial：版本號，如果版本號有更新的話會更新整個 zone 檔。
    - retry：如果主機失聯的話，每幾秒鐘後再試一次（這邊設定 5 秒鐘，但建議設 3600）
    - expire：主機多久沒回應就放棄資料，這邊設 300 秒，但建議是 1209600（兩個禮拜）啦
    - TTL：快取時間，查詢結果會停留的時間，在這時間結束之前，再次查詢就不會再詢問上游，而上面 minimum 的部分只僅限查無結果的時間。
 - 接著要設定健康檢查的檔案
     - 放哪裡都可以，只是我放在 CoreDNS 的資料夾裡面，這樣比較好管理
     - 名字就叫 update_zone.py，或是你想叫別的名字也可以，但是要記好，等等會用到。
     - 裡面的內容會長這樣
     ```python=
    import os
    import requests
    import time
    from datetime import datetime

    # 伺服器清單（要健康檢查的 IP）
    servers = [
        "<你要健康檢查的 server IP 1>",
        "<你要健康檢查的 server IP 2>"
    ]

    # zone 檔路徑
    zone_file_path = "/CoreDNS/zones/db.<建議是你的 Domain name>"

    # SOA 設定，不用改
    soa_template = """$ORIGIN .
    $TTL 5      ; 1 day
    <你的 Domain name>             IN SOA  ns2.<你的 Domain name>. <你的電子信箱>. (
                                    {serial} ; serial
                                    10       ; refresh (1 hour)
                                    5       ; retry (30 minutes)
                                    300    ; expire (2 weeks)
                                    86400      ; minimum (1 day)
                                    )
    <你的 Domain name>             IN NS      ns1.<你的 Domain name>.
    <你的 Domain name>             IN NS      ns2.<你的 Domain name>.
    $ORIGIN <你的 Domain name>.
    ns1                     IN A       <你的 server IP>
    ns2                     IN A       <你的 server IP>
    $TTL 5 ; 1 minute
    """
    # 這邊是透過去找那個 server 的 /health 有沒有回傳 200
    def check_health(ip):
        try:
            url = f"http://{ip}/health"
            resp = requests.get(url, timeout=3)
            return resp.status_code == 200
        except:
            return False

    def generate_zone(healthy_ips):
        # 取得目前時間當 serial（格式：YYYYMMDDSS）（其實不用那麼快變換，這裡是為了讓它顯示得更快）
        serial = datetime.utcnow().strftime("%Y%m%d%S") 
        zone_content = soa_template.format(serial=serial)
        # 加入健康的 A 紀錄給根網域 @ 和 www，也可以看要加哪個自己選
        for ip in healthy_ips:
            zone_content += f"@                      IN A       {ip}\n"
        for ip in healthy_ips:
            zone_content += f"www                    IN A       {ip}\n"
        return zone_content

    def update_zone_file(content):
        with open(zone_file_path, "w") as f:
            f.write(content)
        os.utime(zone_file_path, None)

    def main():
        while True:
            healthy = []
            for ip in servers:
                if check_health(ip):
                    healthy.append(ip)
            print(f"Healthy servers: {healthy}")
            zone_text = generate_zone(healthy)
            update_zone_file(zone_text)
            time.sleep(10)

    if __name__ == "__main__":
        main()
     ```
     - 這邊要注意的一點就是 `serial = datetime.utcnow().strftime("%Y%m%d%S") ` 無論怎麼改都一定要是十位的數字，不然會報錯
     - 好了以後去設定 system 檔 
     - `cd /etc/systemd/system`
     - `sudo vim update_zone.service`
     - 貼上下面這些
     ```
     [Unit]
    Description=CoreDNS Zone Auto Update Service
    After=network.target

    [Service]
    ExecStart=/usr/bin/python3 /CoreDNS/scripts/update_zone.py
    User=root
    WorkingDirectory=/CoreDNS/scripts

    Restart=always
    RestartSec=5
    StandardOutput=journal
    StandardError=journal

    [Install]
    WantedBy=multi-user.target
     ```
     - Restart=always：這邊設定的是服務會自動重啟的部分，這樣開一次就可以不用每次開機還要重新跑
     
     - 好了就 reload，然後執行他
     - `sudo systemctl daemon-reload`
     - `sudo systemctl restart update_zone.service`
     - `sudo systemctl status update_zone.service`
     - 先看有沒有跑起來
     ![image](https://hackmd.io/_uploads/rJpuXwS7ge.png)
     - 再去看 zone 檔有沒有變了，目前會變這樣
     ![image](https://hackmd.io/_uploads/S1vj4PHXle.png)
     - 好了以後在 CoreDNS 資料夾裡面用 docker 部屬，這邊的 `--restart unless-stopped` 代表如果除了手動停止以外，其他情況都會自動重啟
     ```
     sudo docker run -d \
    --name coredns \
    --restart unless-stopped \
    -p 53:53/udp -p 53:53/tcp \
    -v /CoreDNS/Corefile:/Corefile \
    -v /CoreDNS/zones:/zones \
    coredns/coredns:latest \
    -conf /Corefile

     ```
     - 好了以後就可以去 `dig A ns1.<你的 Domain name>`（如果你設定的那台是 ns2 就找 ns2 的），然後就會看到你的 NS 的 IP 了
     ![image](https://hackmd.io/_uploads/SkgCJdBmxx.png)




## Nginx Load Balancing

![image](https://hackmd.io/_uploads/rk4eY3HXgg.png)


### 健康檢查的頁面
- 為了讓健康檢查可以找到 Client 的 health/ ，所以要先去建一個 /heakth 的頁面，要直接加在 default 也可以啦，只是這樣不太好分辨是哪裡出問題，所以就先分開
- `sudo vim /etc/nginx/sites-available/health`
- 貼上下面的設定
```
server {
    listen 80;
    server_name 146.190.147.94;

    location / {
        root /var/www/html;
        index index.html index.htm;
    }

    location = /health {
        return 200 "OK";
        add_header Content-Type text/plain;
    }
}
```

### 設定憑證跟負載平衡
- 目的是啟用 HTTPS 連線，以確保資料在傳輸過程中的安全性與加密保護。

- 用 Let's Encrypt 取得憑證，先安裝 Certbot
```
sudo apt update
sudo apt install certbot python3-certbot-nginx
```
- 生成 ssl 憑證
`sudo certbot --nginx -d <你的網域名稱>`
- 先備份一下
`sudo cp -r /etc/letsencrypt/live/<你的網域名稱> /etc/letsencrypt/live/<你的網域名稱>.backup
`
- 傳給 Server 1 跟 Server 2 
`sudo rsync -avz -e ssh /etc/letsencrypt/ <user>@<Server>:/tmp/letsencrypt/`
- 去 Server 把它移到 /etc，把 /tmp 裡的檔案同步過去
```
sudo mkdir /etc/letsencrypt
sudo rsync -a letsencrypt/ /etc/letsencrypt/
```
- 把擁有者設為 root，然後移除傳過去的那份
```
sudo chown -R root:root /etc/letsencrypt/
sudo rm -rf /tmp/letsencrypt/
```
- 去 Nginx 設定檔設定 proxy
```
# HTTP 自動跳轉到 HTTPS
server {
        listen 80 ;
        listen [::]:80 ;
        index index.html index.htm index.nginx-debian.html;

        server_name <你的網域名稱>;
        
        # 讓 http 重新導向到 https
        return 301 https://$host$request_uri;


}
# HTTPS + 負載平衡設定
upstream backend_servers {
    server <Server 1>;
    server <Server 2>;
}

server {
    listen 443 ssl;
    server_name <你的網域名稱>;


    ssl_certificate /etc/letsencrypt/live/<你的網域名稱>/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/<你的網域名稱>/privkey.pem;

    # 建議包含這兩行，強化 TLS 安全性
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # 負載平衡的代理設定
    location / {
        proxy_pass https://backend_servers;
        proxy_set_header Host <你的網域名稱>;
        proxy_ssl_server_name on;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```
- 好了以後就啟動 Nginx

### 後端 Client 設定



- Nginx 設定檔
```
server {
    if ($host = <你的網域名稱>) {
        return 301 https://$host$request_uri;
    }
    listen 80;
    listen [::]:80;
    server_name <你的網域名稱>;
    return 404;
}

server {
    root /var/www/html;
    index index.html index.htm;
    server_name <你的網域名稱>;

    location / {
        try_files $uri $uri/ =404;
    }

    ssl_certificate /etc/letsencrypt/live/<你的網域名稱>/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/<你的網域名稱>/privkey.pem;

    listen [::]:443 ssl ipv6only=on;
    listen 443 ssl;

    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}
```

- 可以去編輯他顯示的頁面，目前預設是 /var/www/html/index.htm
`sudo vim /var/www/html/index.htm`

- 好了以後就啟動 Nginx，去搜尋你的網域名稱就可以看到了
- 也可以把 DNS server 或是後端的 serveer 關掉，網頁還是不會斷線
- 我們的成品：[kunzo.space](https://kunzo.space/)


### Network Bonding for Linux :

前言:
其實剛開始做這個的目的是為了補充我們期中報告中提到的 故障轉移（Failover） ，希望透過實際操作，證明這不只是一個理論概念，而是可以實際應用在真實環境中的技術。剛好我對於 Link Aggregation 這塊也很好奇，就順勢結合一起實作了看看。

這篇會一步步記錄從 Switch 設定、虛擬機網卡橋接、到 Linux 上的 Bonding 設定，到最後由影片呈現故障轉移的結果。

順便提一下外話，在實作上 Switch 的部分原本打算用 RS232 to USB 再用 Putty 下指令的進行操作的，但後來確實找不到相關說明書，只好用 Web GUI 去設定。

特別感謝 [jiazheng](https://hackmd.io/@jiazheng) 學長在這部分提供了許多協助與建議，讓我能夠更順利完成整個測試流程。

### 環境、硬體需求
作業系統 : Windows 11
虛擬機架設 : VMware
網路線、網卡 : 2 張乙太網卡、 2 條網路線(有一條是企資網彥錚老師帶我們實作的，沒想到會在這時候派上用場)

![rkiGe5bXgg](https://github.com/user-attachments/assets/aac3e8f6-e0d3-45f4-82ea-e133ebea9891)

![image](https://hackmd.io/_uploads/SyN7l9-7gl.jpg)

Switch : 用到 [Moli](https://moli.rocks/) 裡面置放已久的 Zyxel GS2200-24 ，有支援 IEEE 802.3ad 協議
![image](https://hackmd.io/_uploads/SJZYtObmxl.jpg)
{%youtube OYuDm42lVqw %}
### 在 Switch 上設定 LACP
目標：
設定交換器的 Link Aggregation，把 port4 和 port6 聚合成一組 TrunkGroup（T1），讓 VMware 上的 Linux Bonding 模式和這組 Trunk 對接。


1. 開始 → 設定
![image](https://hackmd.io/_uploads/B1RJgaTGge.png)
2. 網路和網際網路 → 乙太網路
![image](https://hackmd.io/_uploads/HySRya6Mge.png)
3. (IP 指派) 編輯 → 手動
![image](https://hackmd.io/_uploads/Hy4fga6zxe.png)
4. (IPv4) 開啟 → 填相關資料 → 儲存
![image](https://hackmd.io/_uploads/B1cHpd-7gg.png)
    * IP 位址：填 192.168.1.100
    * 子網路遮罩：填單位網路遮罩，例：255.255.255.0
    * 閘道：填192.168.1.1
    * DNS 分為「慣用」和「其他」，慣用我是填中華電信的 168.95.1.1，其他則是填 Google 的 8.8.8.8
5. 設定好後可以去瀏覽器輸入 http://192.168.1.1 ， 帳號預設 admin 密碼預設是 1234
 ![image](https://hackmd.io/_uploads/B1__E6azge.png)
6. 進去後應該可以看到 Web 介面
![image](https://hackmd.io/_uploads/r11w2yCGll.png)
7. 在左邊欄位找到 Advanced Application → Link Aggreation
![image](https://hackmd.io/_uploads/SyvFEapfgl.png)
8. 在這裡我是把 port4 跟 port6 變成一個 TrunkGroup
![image](https://hackmd.io/_uploads/HyShh1Azxx.png)
9. 滑到底有個 Apply 點下去
 ![image](https://hackmd.io/_uploads/rJlaETTfll.png)
10. 之後回到畫面有上角有個 Save 點下去
![image](https://hackmd.io/_uploads/rkOaVa6zgx.png)
11. 可以看到有 Link Aggreation Status 底下是我們設定好的 T1 Group
![image](https://hackmd.io/_uploads/By2bTyRMlx.png)

到這邊 Switch 設定就結束了，剩下虛擬機上網卡 Bonding 設定
____

### VMware Bonding 設定
確認好上述步驟都做好後，需將兩張實體網卡都橋接（bridged）給 VM 使用

1. 在 VmWare 下的環境設定上方 VM → Setting 
![image](https://hackmd.io/_uploads/HyQRKTpGgx.png)
2. Network Adapter 改成 Bridged 並勾選 Replicate physical Network Connetcion State
![image](https://hackmd.io/_uploads/BJb7cTTGgl.png)
3. USB Controller → USB compatibility 從 USB3.1 改成 USB2.0
![image](https://hackmd.io/_uploads/SkQYZRpzgl.png)
4. 用 `lsusb` 這個指令在虛擬機上安裝 USB 驅動 

- 橋接完後把網卡從 Host 轉給 VM → Removable Devices → 你的網卡 → Connection(Disconnection from Host)
![image](https://hackmd.io/_uploads/S1fa6ppMgg.png)
- 順便看一下 Host 上裝置管理員有沒有把 2 張網卡轉過來
![image](https://hackmd.io/_uploads/r14_wJ0zlg.png)
- 虛擬機內部，用 `ip link show` 可以看到 `enx7cc...` 跟 `enx000...` 這兩張網卡
![image](https://hackmd.io/_uploads/HybHBYbmll.png)

5. 接下去把網卡做 bonding，用 `sudo vim /etc/netplan/01-netcfg.yaml`
    ```
    network:
      version: 2
      renderer: networkd
      ethernets:
        enx7cc2c643d78a: {} # 定義第一張實體網卡（MAC: 00:0e:c6:e6:9d:dc）
        enx000ec6e69ddc: {} # 定義第二張實體網卡（MAC: 7c:c2:c6:43:d7:8a）

      bonds:
        bond0:   # 建立一個邏輯網卡 bond0
          interfaces:
            - enx7cc2c643d78a
            - enx000ec6e69ddc
          parameters:
            mode: 802.3ad # 啟用 LACP( bonding mode 4)
            mii-monitor-interval: 100  # 每 100ms 檢查一次網卡連線狀態 
            transmit-hash-policy: layer2
            lacp-rate: fast
          dhcp4: no
          dhcp6: no
          addresses:
            - 192.168.1.100/24
          gateway4: 192.168.1.1
          nameservers:

    ```  
6. 好了之後用 `sudo netplan apply`
7. 再 `ip link show` 一次，看一下剛設定好的 `bond0` 這張網卡有沒有出現，並且 `state` 是 `up`
![image](https://hackmd.io/_uploads/HyRFLFW7xg.png)
_____

### 實際測試

1. 先把 `ens33 `這張網卡關掉，只留下要測試用的 2 張網卡做測試
 ` sudo ip link set ens33 down`
2. ping google 的 DNS 看看能不能上網 
 `ping 8.8.8.8`
3. 交互測試插拔網路線，看在一條網路線拔除的情況下是否還能上網
4. 影片
{%youtube 0lxmoCRJgEM %}

### 後來結合 Bonding 的發想
原本只打算在做完以上設定後就打算把這台 VM 晾在一邊了，但後來有試過 Ngrok 跟 WireGuard 這兩個軟體，發現 WireGuard 可以讓 DigitalOcean 上的 VM 反向代理本地這台 VM 讓它提供 Web Services 。那再結合 DigitalOcean 上的另外一台 VM 並反向代理其中的 2 個 Container 就可以順利完成我們所要的高可用跟負載平衡了。

大概架構如下:
![structure](https://hackmd.io/_uploads/BJ6S047Xex.png)
其中 Primary 跟 Secondary 的在做 Failover 是透過 Keepailved 來讓 VIP 做轉移，但有個淺在問題是當切換到 Secondary 後沒辦法去接手 Primary 後方的 Container。


### 透過 WireGuard 讓本地 VM 與 DO VM 處於相同 VPN
![user space (2)](https://hackmd.io/_uploads/ryr8oprmle.png)



第一台 DigitalOcean VM
1. 安裝 WireGuard：
 `sudo apt install wireguard -y`
2. 生成 WireGuard 金鑰對
    `wg genkey | tee do_private.key | wg pubkey > do_public.key`
3. 查看 Private Key（貼到 [Interface] 中）
    `cat do_private.key`
4. 查看 Public Key（提供給本地 VM）
     `cat do_public.key`

5. 編輯 WireGuard 設定檔，進去後可以看到 [Interface] 表示自己這台虛擬機
`sudo vim /etc/wireguard/wg0.conf`
    ```
    [Interface]
    PrivateKey = # 第三步驟產生的 private key
    Address = 10.100.0.1/24  # 本地 WireGuard 的IP ，設你要的就好
    ListenPort = 51820 # WireGuard 監聽的 port，預設通常是防火牆的 51820

    [Peer]
    PublicKey =  # 後端虛擬機產生的 public key
    AllowedIPs = 10.100.0.2/32  # 後端虛擬機 WireGuard 設定的IP 
    Endpoint =  X.X.X.X # 後端 VM 的IP
    PersistentKeepalive = 25
    ```
6. 開啟 WireGuard 跟 防火牆
`sudo wg-quick up wg0`
`sudo ufw allow 51820/udp`
7. IP forwarding 要打開
`sudo sysctl -w net.ipv4.ip_forward=1`


第二台後端 VM
1. 安裝 WireGuard：
 `sudo apt install wireguard -y`
2. 生成 WireGuard 金鑰對
    `wg genkey | tee do_private.key | wg pubkey > do_public.key`
3. 查看 Private Key（貼到 [Interface] 中）
    `cat do_private.key`
4. 查看 Public Key（提供給 DO VM）
     `cat do_public.key`
5. 編輯 WireGuard 設定檔
`sudo vim /etc/wireguard/wg0.conf`
    ```
    [Interface]
    Address = 10.100.0.2/24
    PrivateKey =  # 後端 VM 剛產生的 private key

    [Peer]
    PublicKey = # DO VM 的 public key
    Endpoint = X.X.X.X:51820 # 填 DO VM 的 IP , e.g. 
    AllowedIPs = 0.0.0.0/0
    PersistentKeepalive = 25
    ```
6. 開啟 WireGuard，當虛擬機關機時要重新打開
` sudo wg-quick up wg0`

測試有沒有成功
1. 從後端 VM ping DO VM
`ping 10.100.0.1`    
![image](https://hackmd.io/_uploads/BJAqiPQQxg.png)

2. 從 DO VM ping 回來
`ping 10.100.0.2`   
![image](https://hackmd.io/_uploads/ryqxhDXmel.png)

### 在後端 VM 中架設 Web Server 

1. 安裝 Nginx
  ` sudo apt install nginx -y`
2. 啟動 Nginx
`sudo systemctl start nginx`
`sudo systemctl enable nginx`
3. 修改 index.html 內容
 `sudo vim /var/www/html/index.html` 
    ```
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>Bond0 Web Server</title>
    </head>
    <body>
      <h1> bond0 Web Server - Backend's VM </h1>
      <p>Nginx on LACP VM</p>
    </body>
    </html>
    ```
4. 可以回到 DO VM 看一下有沒有成功
`curl http://10.100.0.2`
![image](https://hackmd.io/_uploads/S1PQMOQXll.png)
____

### 在第二台 DO VM 架設 Reverse Proxy 回應使用者請求
![user space](https://hackmd.io/_uploads/SkhEdd7mgx.png)

1. 安裝 Nginx 
  ` sudo apt install nginx -y`
2. 啟動 Nginx
`sudo systemctl start nginx`
`sudo systemctl enable nginx`
3. 安裝 Docker 
`curl -fsSL https://get.docker.com -o get-docker.sh`
`sudo sh ./get-docker.sh`
4. 看看 Docker 是否安裝成功
` sudo docker run hello-world`
5. 建立兩個 Docker container
- real1 container，監聽 port 8081
`docker run -d --name real1 -p 8081:80 nginx`
- 建立 real2 container，監聽 port 8082
`docker run -d --name real2 -p 8082:80 nginx`
6. 在 index.html 加上一些內容，方便辨識
- real1 顯示 "Hello from real1"
`docker exec real1 bash -c 'echo "Hello from real1" > /usr/share/nginx/html/index.html'`
- real2 顯示 "Hello from real2"
`docker exec real2 bash -c 'echo "Hello from real2" > /usr/share/nginx/html/index.html'`

7. 設定 revesre proxy
`sudo vim /etc/nginx/sites-available/reverse-proxy.conf`
    ```
    upstream backend {
        server localhost:8081;
        server localhost:8082;
    }



    server {
            listen 80 default_server;
            listen [::]:80 default_server;


            root /var/www/html;

            # Add index.php to the list if you are using PHP
            index index.html index.htm index.nginx-debian.html;

            server_name _;

            location / {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;    }


    }
    ```
8. 啟用設定
` sudo ln -s /etc/nginx/sites-available/reverse-proxy.conf /etc/nginx/sites-enabled/default.conf `
 
9. 重新載入 Nginx 套用設定
`sudo systemctl reload nginx`

10. 測試
`curl http://localhost`


### 用 KeepAlived 達成故障轉移

此處參考了 [jiazheng](https://hackmd.io/@jiazheng) 學長的[負載平衡和高度可用性](https://hackmd.io/@ncnu-opensource/book/https%3A%2F%2Fhackmd.io%2FpLrUczzjQ_CUhcnPX2Xwhw%3Fview)，但 DigitalOcean 上 Floating IP 已改名叫做 Reserved IP，申請部分可以查看[官方文件](https://docs.digitalocean.com/products/networking/reserved-ips/how-to/create/)還有 [DigitalOcean token](https://docs.digitalocean.com/reference/api/create-personal-access-token/) 也要記得申請。最後 KeepAlived 設定檔的地方也有做變動，留意一下。


1. 安裝 keepalived
`sudo apt install keepalived`
2. 接下來開始建立設定檔
`sudo vim /etc/keepalived/keepalived.conf`
    - Primary
    ```
        global_defs {
        script_user root
        enable_script_security
    }

    vrrp_script chk_nginx {
        script "/usr/bin/pgrep nginx"
        interval 2
    }

    vrrp_instance VI_1 {
        interface eth0 # 注意這邊要看有 public ip 的網卡
        state MASTER 
        priority 150
        virtual_router_id 33

        unicast_src_ip X.X.X.X # 自己這台虛擬機 ip
        unicast_peer {
            X.X.X.X # backup ip 
        }

        authentication {
            auth_type PASS
            auth_pass password
        }

        virtual_ipaddress {
            138.197.59.192/32 dev eth0 # 填申請下來的 reserved ip
        }

        track_script {
            chk_nginx
        }

        notify_master /etc/keepalived/master.sh # 後面會run一個master.sh腳本
    }
    ```
- Secondary 的地方

    ```
        global_defs {
        script_user root
        enable_script_security
    }

    vrrp_script chk_nginx {
        script "/usr/bin/pgrep nginx"
        interval 2
    }

    vrrp_instance VI_1 {
        interface eth0
        state BACKUP
        priority 50
        virtual_router_id 33
        unicast_src_ip 143.198.3.150
        unicast_peer {
            142.93.186.3
        }
        authentication {
            auth_type PASS
            auth_pass password
        }
        virtual_ipaddress {
            138.197.59.192/32 dev eth0
        }
        track_script {
            chk_nginx
        }
        notify_master /etc/keepalived/master.sh
    }
    ```

3. 下載 DigitalOcean 提供的 assign-ip 腳本
    ```
    cd /usr/local/bin
    sudo curl -LO http://do.co/assign-ip
    ```
    下載完要加上執行權限：
    `sudo chmod +x /usr/local/bin/assign-ip`
4. 建立當主機掛掉時需要執行的腳本
DO_TOKEN 變數要改成拿到的 API Token
IP 變數要改成拿到的 Reserved IP
`sudo vim /etc/keepalived/master.sh`

    ```
    #!/bin/bash
    export DO_TOKEN='' # ''裡面改成你申請下來的 token 
    IP='138.197.59.192' # 改成你申請下來的 reserved ip
    ID=$(curl -s http://169.254.169.254/metadata/v1/id)HAS_FLOATING_IP=$(curl -s http://169.254.169.254/metadata/v1/floating_ip/ipv4/active)

    if [ "$HAS_FLOATING_IP" = "false" ]; then
        n=0
        while [ $n -lt 10 ]
        do
            python3 /usr/local/bin/assign-ip $IP $ID && break
            n=$((n+1))
            sleep 3
        done
    fi
    ```
    :::info
    注意這裡要先有安裝 python3，不然腳本會 run 不起來
    ```
    sudo apt install python3 python3-pip -y
    pip3 install requests
    ```
    :::
    
5. 接下來讓 master.sh 可以被 keepalived 執行
`sudo chmod +x /etc/keepalived/master.sh`

6. 可以來啟動我們的 keepalived 了
`sudo systemctl restart keepalived` 
`sudo systemctl reload keepalived` 
7. 測試當 Master 關掉時(可能會等個幾秒 VIP 才會轉過來)
`sudo systemctl stop nginx`
`curl http://138.197.59.192`
![image](https://hackmd.io/_uploads/SJmWOaXQeg.png)
 是顯示出 Backup 後端 VM 的內容
8. Backup 可以搭配 journal 來看比較好 debug
`sudo journalctl -u keepalived -f`
9. 再把 Master 回復，看看結果
![image](https://hackmd.io/_uploads/S1nOOpX7xg.png)
![image](https://hackmd.io/_uploads/Skg5_am7lx.png)

{%youtube zv64v2An7gs %}

## 工作分配
- 孫睿君：高可用 DNS Server 實作、 Nginx 負載平衡實作。
- 羅智穎 : 處理 Switch 設定、 Linux Network Bonding 
## Refrence

DNS and Nginx Load Balancing
- [Configure Self-Hosted DNS Server: Step-by-Step Guide](https://hostedsoftware.org/blog/configure-self-hosted-dns-server-step-by-step-guide/)
- [BobyGamer](https://github.com/NCNU-OpenSource/BobyGamer)
- [Windows 11 中 IP 設定](https://chenmama.neocities.org/IP/11)
- [Netowork Bonding for Linux](https://chtseng.wordpress.com/2022/09/30/netowork-bonding-for-linux/)

