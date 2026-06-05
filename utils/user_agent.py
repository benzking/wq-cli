#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User-Agent 生成器
按市场份额权重分配浏览器类型，动态版本号，真实 OS 变体。
移植自 we-mp-rss (driver/user_agent.py)。
"""
import random

__all__ = ["random_ua", "UserAgentGenerator"]


class UserAgentGenerator:
    """生成符合真实市场分布的 User-Agent 字符串"""

    def __init__(self):
        self.mobile_browser_weights = {
            'chrome': 0.45, 'safari': 0.30, 'firefox': 0.10,
            'edge': 0.08, 'opera': 0.05, 'qq': 0.02,
        }
        self.desktop_browser_weights = {
            'chrome': 0.65, 'edge': 0.12, 'firefox': 0.08,
            'safari': 0.08, 'opera': 0.05, 'qq': 0.02,
        }

    def get_realistic_user_agent(self, mobile_mode: bool = False) -> str:
        if mobile_mode:
            return self._generate_mobile_ua()
        return self._generate_desktop_ua()

    def _generate_mobile_ua(self) -> str:
        browser_type = random.choices(
            list(self.mobile_browser_weights.keys()),
            weights=list(self.mobile_browser_weights.values()),
        )[0]
        return {
            'chrome': self._generate_chrome_mobile_ua,
            'safari': self._generate_safari_mobile_ua,
            'firefox': self._generate_firefox_mobile_ua,
            'edge': self._generate_edge_mobile_ua,
            'opera': self._generate_opera_mobile_ua,
            'qq': self._generate_qq_mobile_ua,
        }[browser_type]()

    def _generate_desktop_ua(self) -> str:
        browser_type = random.choices(
            list(self.desktop_browser_weights.keys()),
            weights=list(self.desktop_browser_weights.values()),
        )[0]
        return {
            'chrome': self._generate_chrome_desktop_ua,
            'edge': self._generate_edge_desktop_ua,
            'firefox': self._generate_firefox_desktop_ua,
            'safari': self._generate_safari_desktop_ua,
            'opera': self._generate_opera_desktop_ua,
            'qq': self._generate_qq_desktop_ua,
        }[browser_type]()

    # ========== 版本号 ==========

    def _get_chrome_version(self) -> str:
        return f"{random.randint(110, 125)}.{random.randint(0, 9)}.{random.randint(4000, 6500)}.{random.randint(0, 200)}"

    def _get_firefox_version(self) -> str:
        return str(random.randint(110, 125))

    def _get_safari_version(self) -> str:
        return f"{random.randint(15, 17)}.{random.randint(0, 6)}"

    def _get_edge_version(self) -> str:
        return f"{random.randint(110, 125)}.{random.randint(0, 9)}.{random.randint(1000, 2500)}.{random.randint(0, 100)}"

    def _get_opera_version(self) -> str:
        major = random.randint(90, 110)
        return f"{major}.{random.randint(0, 9)}.{random.randint(4000, 5500)}.{major - 13}"

    # ========== OS 版本 ==========

    def _get_android_version(self) -> str:
        return random.choices(
            ['10', '11', '12', '13', '14'],
            weights=[0.15, 0.20, 0.30, 0.25, 0.10]
        )[0]

    def _get_ios_version(self) -> str:
        return random.choices(
            ['15_0', '15_5', '16_0', '16_5', '17_0', '17_2', '17_4'],
            weights=[0.10, 0.15, 0.15, 0.20, 0.20, 0.15, 0.05]
        )[0]

    def _get_windows_version(self) -> str:
        versions = [
            ('Windows NT 10.0; Win64; x64', 0.70),
            ('Windows NT 10.0; WOW64', 0.15),
            ('Windows NT 6.3; Win64; x64', 0.08),
            ('Windows NT 6.1; Win64; x64', 0.05),
            ('Windows NT 11.0; Win64; x64', 0.02),
        ]
        return random.choices([v[0] for v in versions], weights=[v[1] for v in versions])[0]

    def _get_macos_version(self) -> str:
        versions = [
            ('10_15_7', 0.25), ('11_0', 0.15), ('12_0', 0.20),
            ('13_0', 0.25), ('14_0', 0.15),
        ]
        return random.choices([v[0] for v in versions], weights=[v[1] for v in versions])[0]

    def _get_linux_distro(self) -> str:
        return random.choice([
            'X11; Linux x86_64', 'X11; Ubuntu; Linux x86_64',
            'X11; Fedora; Linux x86_64', 'X11; Arch Linux; Linux x86_64',
        ])

    # ========== 设备型号 ==========

    def _get_android_device(self) -> str:
        return random.choice([
            'SM-G991B', 'SM-G998B', 'SM-S908B', 'SM-S918B',
            'Mi 10', 'Mi 11', 'Mi 12', 'Mi 13',
            'ELE-AL00', 'ANA-AL00',
            'OPPO A5', 'OPPO Reno6', 'Vivo X70', 'Vivo X80',
            'Pixel 5', 'Pixel 6', 'Pixel 7', 'Pixel 8',
            'OnePlus 8', 'OnePlus 9', 'OnePlus 10 Pro',
        ])

    # ========== 桌面端 UA ==========

    def _generate_chrome_desktop_ua(self) -> str:
        chrome_ver = self._get_chrome_version()
        os_str = random.choices(
            [self._get_windows_version(),
             f"Macintosh; Intel Mac OS X {self._get_macos_version()}",
             self._get_linux_distro()],
            weights=[0.75, 0.15, 0.10],
        )[0]
        return f"Mozilla/5.0 ({os_str}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36"

    def _generate_edge_desktop_ua(self) -> str:
        edge_ver = self._get_edge_version()
        chrome_ver = self._get_chrome_version()
        return f"Mozilla/5.0 ({self._get_windows_version()}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36 Edg/{edge_ver}"

    def _generate_firefox_desktop_ua(self) -> str:
        firefox_ver = self._get_firefox_version()
        os_str = random.choices(
            [self._get_windows_version(),
             f"Macintosh; Intel Mac OS X {self._get_macos_version()}",
             self._get_linux_distro()],
            weights=[0.60, 0.25, 0.15],
        )[0]
        return f"Mozilla/5.0 ({os_str}; rv:{firefox_ver}.0) Gecko/20100101 Firefox/{firefox_ver}.0"

    def _generate_safari_desktop_ua(self) -> str:
        return f"Mozilla/5.0 (Macintosh; Intel Mac OS X {self._get_macos_version()}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{self._get_safari_version()} Safari/605.1.15"

    def _generate_opera_desktop_ua(self) -> str:
        opera_ver = self._get_opera_version()
        chrome_ver = self._get_chrome_version()
        os_str = random.choices(
            [self._get_windows_version(),
             f"Macintosh; Intel Mac OS X {self._get_macos_version()}",
             self._get_linux_distro()],
            weights=[0.70, 0.20, 0.10],
        )[0]
        return f"Mozilla/5.0 ({os_str}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36 OPR/{opera_ver}"

    def _generate_qq_desktop_ua(self) -> str:
        chrome_ver = self._get_chrome_version()
        qq_ver = f"{random.randint(13, 15)}.{random.randint(0, 5)}.{random.randint(5000, 5500)}"
        return f"Mozilla/5.0 ({self._get_windows_version()}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36 QQBrowser/{qq_ver}"

    # ========== 移动端 UA ==========

    def _generate_chrome_mobile_ua(self) -> str:
        return f"Mozilla/5.0 (Linux; Android {self._get_android_version()}; {self._get_android_device()}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{self._get_chrome_version()} Mobile Safari/537.36"

    def _generate_safari_mobile_ua(self) -> str:
        return f"Mozilla/5.0 (iPhone; CPU iPhone OS {self._get_ios_version()} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{self._get_safari_version()} Mobile/15E148 Safari/604.1"

    def _generate_firefox_mobile_ua(self) -> str:
        return f"Mozilla/5.0 (Android {self._get_android_version()}; Mobile; rv:{self._get_firefox_version()}.0) Gecko/{self._get_firefox_version()}.0 Firefox/{self._get_firefox_version()}.0"

    def _generate_edge_mobile_ua(self) -> str:
        return f"Mozilla/5.0 (Linux; Android {self._get_android_version()}; {self._get_android_device()}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{self._get_chrome_version()} Mobile Safari/537.36 EdgA/{self._get_edge_version()}"

    def _generate_opera_mobile_ua(self) -> str:
        return f"Mozilla/5.0 (Linux; Android {self._get_android_version()}; {self._get_android_device()}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{self._get_chrome_version()} Mobile Safari/537.36 OPR/{self._get_opera_version()}"

    def _generate_qq_mobile_ua(self) -> str:
        qq_ver = f"{random.randint(13, 15)}.{random.randint(0, 5)}.{random.randint(3000, 3500)}"
        return f"Mozilla/5.0 (Linux; Android {self._get_android_version()}; {self._get_android_device()}) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/{self._get_chrome_version()} MQQBrowser/{qq_ver} Mobile Safari/537.36"


_generator = UserAgentGenerator()


def random_ua() -> str:
    """返回一条随机桌面端 UA（按市场份额权重 + 动态版本 + OS 变体）"""
    return _generator.get_realistic_user_agent(mobile_mode=False)
