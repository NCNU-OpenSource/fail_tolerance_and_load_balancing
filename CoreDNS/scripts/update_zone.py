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