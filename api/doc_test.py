import requests
import ssl
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.exceptions import InsecureRequestWarning

# 禁用不安全请求的警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class LegacyHTTPAdapter(HTTPAdapter):
    """支持不安全TLS重新协商并禁用主机名验证的HTTP适配器"""

    def init_poolmanager(self, connections, maxsize, block=False):
        context = ssl.create_default_context()
        # 允许不安全的重新协商
        context.options |= 0x4  # OP_LEGACY_SERVER_CONNECT

        # 关键修复：禁用主机名验证
        context.check_hostname = False

        # 降低安全级别以支持旧版TLS
        context.set_ciphers('DEFAULT@SECLEVEL=1')

        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=context,
            assert_hostname=False  # 禁用主机名验证
        )


if __name__ == "__main__":
    file_path = "/Users/ycicic/Downloads/测试文件1.pdf"
    api_url = "https://47.109.146.94:8059/htjx-api/"
    print("开始读取文件")

    # 创建支持旧版TLS的会话
    session = requests.Session()
    session.mount('https://', LegacyHTTPAdapter())

    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        print("读取文件完成")

        files = {
            'file_bytes': ('uploaded_file.pdf', file_bytes, 'application/pdf')
        }

        data = {
            'not_save_img_link': 'true',
            'use_llm': 'false'
        }

        print("发送 POST 请求")
        # 注意：verify=False 仍然需要，但真正的禁用逻辑在适配器中
        response = session.post(api_url, files=files, data=data, timeout=30, verify=False)
        response.raise_for_status()

        print("接口响应：")
        print(f"状态码：{response.status_code}")
        print(f"响应内容：{response.json()}")

    except requests.exceptions.RequestException as e:
        print(f"请求失败：{e}")
    finally:
        session.close()
