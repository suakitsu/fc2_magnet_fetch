from __future__ import annotations

from configparser import RawConfigParser
from dataclasses import dataclass
from pathlib import Path


CONFIG_SECTION = "下载设置"
DEFAULT_CONFIG = """[下载设置]
Proxy = http://localhost:10808
Download_Path = ./Downloads/
Max_dl = 2
Max_retry = 3
Cookies =
fcu =
PHPSESSID =
"""


@dataclass
class AppConfig:
    base_dir: Path
    config_path: Path
    download_path: Path
    proxy: str
    max_dl: int
    max_retry: int
    cookies: str
    fcu: str
    phpsessid: str

    @property
    def proxy_enabled(self) -> bool:
        return self.proxy not in ("", "no", "否")

    @property
    def proxies(self) -> dict[str, str]:
        if not self.proxy_enabled:
            return {}
        return {"http": self.proxy, "https": self.proxy}


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def ensure_config_file(config_path: Path) -> None:
    if config_path.exists():
        return
    config_path.write_text(DEFAULT_CONFIG, encoding="utf-8-sig")


def load_config() -> AppConfig:
    base_dir = project_root()
    config_path = base_dir / "config.ini"
    ensure_config_file(config_path)

    parser = RawConfigParser()
    parser.read(config_path, encoding="utf-8-sig")

    def getv(key: str, fallback: str = "") -> str:
        try:
            return parser.get(CONFIG_SECTION, key)
        except Exception:
            return fallback

    proxy = getv("Proxy", "")
    dp = getv("Download_Path", "./Downloads/")
    max_dl = int(getv("Max_dl", "2") or "2")
    max_retry = int(getv("Max_retry", "3") or "3")
    cookies = getv("Cookies", "")
    fcu = getv("fcu", "")
    phpsessid = getv("PHPSESSID", "")

    download_path = Path(dp)
    if not download_path.is_absolute():
        dp_clean = dp.replace("./", "").replace(".\\", "").rstrip("/\\")
        download_path = base_dir / dp_clean
    download_path.mkdir(parents=True, exist_ok=True)

    return AppConfig(
        base_dir=base_dir,
        config_path=config_path,
        download_path=download_path,
        proxy=proxy,
        max_dl=max(1, max_dl),
        max_retry=max(1, max_retry),
        cookies=cookies,
        fcu=fcu,
        phpsessid=phpsessid,
    )


def save_cookie_to_config(fcu: str, phpsessid: str) -> None:
    cfg = load_config()
    parser = RawConfigParser()
    parser.read(cfg.config_path, encoding="utf-8-sig")
    if not parser.has_section(CONFIG_SECTION):
        parser.add_section(CONFIG_SECTION)
    parser.set(CONFIG_SECTION, "fcu", fcu.strip())
    parser.set(CONFIG_SECTION, "PHPSESSID", phpsessid.strip())
    with cfg.config_path.open("w", encoding="utf-8-sig") as f:
        parser.write(f)

