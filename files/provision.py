#!/usr/bin/env python3
import base64
import copy
import http.client
import http.cookiejar
import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request


def env_str(name, default=""):
    val = os.getenv(name)
    return val.strip() if val is not None and val.strip() != "" else default


def env_int(name, default):
    val = os.getenv(name)
    return int(val.strip()) if val is not None and val.strip() != "" else default


def env_float(name, default):
    val = os.getenv(name)
    return float(val.strip()) if val is not None and val.strip() != "" else default


def env_bool(name, default):
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default):
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return list(default)
    return [item.strip() for item in val.split(",") if item.strip()]


# ==============================================================================
# CONFIGURAÇÕES CARREGADAS VIA VARIÁVEIS DE AMBIENTE (.env)
# ==============================================================================
PUID = env_int("PUID", 1000)
PGID = env_int("PGID", 1000)

QBIT_HOST = env_str("QBIT_HOST", "gluetun")
QBIT_NETWORK_INTERFACE = env_str(
    "QBIT_NETWORK_INTERFACE",
    "tun0" if QBIT_HOST == "gluetun" else "",
)

PROWLARR_API_KEY = env_str("PROWLARR_API_KEY", "99887766554433221100ffeeddccbbaa")
RADARR_API_KEY = env_str("RADARR_API_KEY", "a1b2c3d4e5f60718293a4b5c6d7e8f90")
SONARR_API_KEY = env_str("SONARR_API_KEY", "11223344556677889900aabbccddeeff")
BAZARR_API_KEY = env_str("BAZARR_API_KEY", "b1a2z3a4r5r60718293a4b5c6d7e8f90")

PROWLARR_BASE_URL = "http://prowlarr:9696/prowlarr"
RADARR_BASE_URL = "http://radarr:7878/radarr"
SONARR_BASE_URL = "http://sonarr:8989/sonarr"
BAZARR_URL = "http://bazarr:6767/bazarr"

SERVICES = {
    "prowlarr": (PROWLARR_BASE_URL, "v1", PROWLARR_API_KEY),
    "radarr": (RADARR_BASE_URL, "v3", RADARR_API_KEY),
    "sonarr": (SONARR_BASE_URL, "v3", SONARR_API_KEY),
}
DOWNLOAD_CLIENTS = {
    "qbittorrent": f"http://{QBIT_HOST}:8080",
}

PROWLARR_INDEXERS = env_list("PROWLARR_INDEXERS", ["YTS", "Knaben", "The Pirate Bay", "RuTor"])
PROWLARR_MIN_SEEDERS = env_int("PROWLARR_MIN_SEEDERS", 2)
AUDIO_ORIGINAL_ONLY = env_bool("AUDIO_ORIGINAL_ONLY", True)

RADARR_MAX_SIZE_MB_MIN = env_float("RADARR_MAX_SIZE_MB_MIN", 48.0)
SONARR_MAX_SIZE_MB_MIN = env_float("SONARR_MAX_SIZE_MB_MIN", 48.0)

BAZARR_LANGUAGES = env_list("BAZARR_LANGUAGES", ["pb", "en"])
BAZARR_PROFILE_NAME = env_str("BAZARR_PROFILE_NAME", "pt-BR + EN")
BAZARR_ALLOW_HI = env_str("BAZARR_ALLOW_HI", "Include")
BAZARR_MIN_SCORE_MOVIE = env_int("BAZARR_MIN_SCORE_MOVIE", 60)
BAZARR_MIN_SCORE_SERIES = env_int("BAZARR_MIN_SCORE_SERIES", 70)
BAZARR_AUTO_SYNC = env_bool("BAZARR_AUTO_SYNC", True)
BAZARR_DEFAULT_PROVIDERS = env_list(
    "BAZARR_DEFAULT_PROVIDERS",
    ["embeddedsubtitles", "yifysubtitles", "tvsubtitles", "podnapisi", "gestdown"],
)
OPENSUBTITLES_USER = env_str("OPENSUBTITLES_USER", "")
OPENSUBTITLES_PASS = env_str("OPENSUBTITLES_PASS", "")
SUBSOURCE_API_KEY = env_str("SUBSOURCE_API_KEY", "")

JF_USER = env_str("JELLYFIN_ADMIN_USER", "admin")
JF_PASS = env_str("JELLYFIN_ADMIN_PASS", "admin")
JF_SERVER_NAME = env_str("JELLYFIN_SERVER_NAME", "Jellyfin")
JF_UI_CULTURE = env_str("JELLYFIN_UI_CULTURE", "en-US")
JF_METADATA_COUNTRY = env_str("JELLYFIN_METADATA_COUNTRY", "US")
JF_METADATA_LANG = env_str("JELLYFIN_METADATA_LANG", "en")
JF_MONITOR_DELAY = env_int("JELLYFIN_MONITOR_DELAY", 10)
JF_HWACCEL = env_str("JELLYFIN_HWACCEL", "rkmpp").lower()

APP_HOST = env_str("APP_HOST", "flix.home.ensilva.cc")
ARR_ADMIN_USER = env_str("ARR_ADMIN_USER", JF_USER)
ARR_ADMIN_PASS = env_str("ARR_ADMIN_PASS", JF_PASS)
BAZARR_ADMIN_USER = env_str("BAZARR_ADMIN_USER", ARR_ADMIN_USER)
BAZARR_ADMIN_PASS = env_str("BAZARR_ADMIN_PASS", ARR_ADMIN_PASS)

QBIT_ADMIN_USER = env_str("QBIT_ADMIN_USER", ARR_ADMIN_USER)
QBIT_ADMIN_PASS = env_str("QBIT_ADMIN_PASS", ARR_ADMIN_PASS)
QBIT_AUTH_SUBNET_WHITELIST = env_str("QBIT_AUTH_SUBNET_WHITELIST", "172.28.0.0/24")

SEERR_URL = "http://seerr:5055"
SEERR_PROFILE_ID = env_int("SEERR_DEFAULT_PROFILE_ID", 4)
SEERR_PROFILE_NAME = env_str("SEERR_DEFAULT_PROFILE_NAME", "HD-1080p")


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, sock_path="/var/run/docker.sock"):
        super().__init__("localhost")
        self.sock_path = sock_path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.sock_path)


def docker_exec(container, cmd):
    payload = json.dumps({
        "AttachStdout": True,
        "AttachStderr": True,
        "Tty": True,
        "Cmd": cmd,
    })
    conn = UnixHTTPConnection()
    conn.request("POST", f"/containers/{container}/exec", body=payload, headers={"Content-Type": "application/json"})
    res = conn.getresponse()
    data = json.loads(res.read().decode("utf-8"))
    conn.close()
    if res.status != 201:
        raise RuntimeError(f"Falha ao criar exec no container {container}: {data}")

    exec_id = data["Id"]
    conn2 = UnixHTTPConnection()
    conn2.request("POST", f"/exec/{exec_id}/start", body=json.dumps({"Detach": False, "Tty": True}), headers={"Content-Type": "application/json"})
    res2 = conn2.getresponse()
    output = res2.read().decode("utf-8", errors="replace")
    conn2.close()
    return output


def jf_api(method, path, payload=None, token=None):
    auth_header = 'MediaBrowser Client="Provisioner", Device="Linux", DeviceId="jellyfin-provision-1", Version="1.0.0"'
    if token:
        auth_header += f', Token="{token}"'

    cmd = [
        "curl", "-sS", "-w", "\n%{http_code}",
        "-X", method, f"http://127.0.0.1:8096{path}",
        "-H", "Content-Type: application/json",
        "-H", f"Authorization: {auth_header}",
    ]
    if payload is not None:
        cmd.extend(["-d", json.dumps(payload)])

    raw = docker_exec("jellyfin", cmd)
    lines = raw.strip().splitlines()
    if not lines or not lines[-1].isdigit():
        raise RuntimeError(f"Resposta inesperada do Jellyfin ({method} {path}): {raw}")

    http_code = int(lines[-1])
    body = "\n".join(lines[:-1])
    if http_code < 200 or http_code >= 300:
        raise RuntimeError(f"[ERRO HTTP {http_code}] Jellyfin {method} {path} -> {body}")

    return json.loads(body) if body.strip() else None


def req(base_url, api_ver, api_key, path, method="GET", payload=None):
    url = f"{base_url}/api/{api_ver}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"[ERRO HTTP {e.code}] {method} {url} -> {err_body}")
        raise


def qbit_req(path, method="GET", form_fields=None):
    base = DOWNLOAD_CLIENTS["qbittorrent"]
    url = f"{base}/api/v2{path}"
    headers = {
        "Referer": base,
        "Origin": base,
    }
    data = None
    if form_fields is not None:
        data = urllib.parse.urlencode(form_fields).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body.strip() else None
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"[ERRO HTTP {e.code}] qBittorrent {method} {url} -> {err_body}")
        raise


def bazarr_req(path, method="GET", form_fields=None):
    url = f"{BAZARR_URL}/api{path}"
    headers = {"X-API-KEY": BAZARR_API_KEY}
    data = None
    if form_fields is not None:
        data = urllib.parse.urlencode(form_fields, doseq=True).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"[ERRO HTTP {e.code}] Bazarr {method} {url} -> {err_body}")
        raise


def wait_ready():
    for name, (url, ver, key) in SERVICES.items():
        for _ in range(60):
            try:
                req(url, ver, key, "/system/status")
                print(f"[OK] {name} pronto ({url}).")
                break
            except Exception:
                time.sleep(2)
        else:
            raise RuntimeError(f"Timeout aguardando {name} em {url}")

    for name, url in DOWNLOAD_CLIENTS.items():
        for _ in range(45):
            try:
                urllib.request.urlopen(url, timeout=5)
                print(f"[OK] {name} pronto em {url}.")
                break
            except urllib.error.HTTPError:
                print(f"[OK] {name} pronto em {url}.")
                break
            except Exception:
                time.sleep(2)
        else:
            raise RuntimeError(f"Timeout aguardando {name} em {url}")

    for _ in range(30):
        try:
            bazarr_req("/system/status")
            print(f"[OK] bazarr pronto ({BAZARR_URL}).")
            break
        except Exception:
            time.sleep(2)
    else:
        raise RuntimeError(f"Timeout aguardando bazarr em {BAZARR_URL}")

    for _ in range(30):
        try:
            jf_api("GET", "/System/Info/Public")
            print("[OK] jellyfin pronto.")
            break
        except Exception:
            time.sleep(2)
    else:
        raise RuntimeError("Timeout aguardando jellyfin")

    for _ in range(30):
        try:
            urllib.request.urlopen(f"{SEERR_URL}/api/v1/status", timeout=5)
            print("[OK] seerr pronto.")
            break
        except Exception:
            time.sleep(2)
    else:
        raise RuntimeError("Timeout aguardando seerr")


def setup_qbittorrent():
    prefs = qbit_req("/app/preferences") or {}
    current_iface = prefs.get("current_network_interface", "")
    current_iface_name = prefs.get("current_interface_name", "")
    label = QBIT_NETWORK_INTERFACE or "Any (todas as interfaces)"

    updates = {
        "current_network_interface": QBIT_NETWORK_INTERFACE,
        "current_interface_name": QBIT_NETWORK_INTERFACE,
        "auto_tmm_enabled": True,
        "bypass_auth_subnet_whitelist_enabled": True,
        "bypass_auth_subnet_whitelist": QBIT_AUTH_SUBNET_WHITELIST,
    }
    if QBIT_ADMIN_USER and QBIT_ADMIN_PASS:
        if len(QBIT_ADMIN_PASS) >= 6:
            updates["web_ui_username"] = QBIT_ADMIN_USER
            updates["web_ui_password"] = QBIT_ADMIN_PASS
        else:
            print("[WARN] QBIT_ADMIN_PASS deve ter pelo menos 6 caracteres; credenciais WebUI não alteradas.")

    qbit_req("/app/setPreferences", "POST", {"json": json.dumps(updates)})
    print(f"[OK] qBittorrent configurado (interface={label}, usuário='{QBIT_ADMIN_USER}', whitelist='{QBIT_AUTH_SUBNET_WHITELIST}').")


def ensure_root_folder(base_url, ver, key, folder_path):
    existing = req(base_url, ver, key, "/rootfolder")
    if any(rf["path"] == folder_path for rf in existing):
        print(f"[SKIP] Root folder já existe: {folder_path}")
        return
    req(base_url, ver, key, "/rootfolder", "POST", {"path": folder_path})
    print(f"[OK] Root folder criada: {folder_path}")


def enable_renaming(base_url, ver, key, field_name):
    cfg = req(base_url, ver, key, "/config/naming")
    if not cfg.get(field_name):
        cfg[field_name] = True
        req(base_url, ver, key, f"/config/naming/{cfg['id']}", "PUT", cfg)
        print(f"[OK] Renomeação ativada ({field_name}).")


def ensure_download_clients(base_url, ver, key, category):
    existing_list = req(base_url, ver, key, "/downloadclient") or []
    existing_map = {c["name"]: c for c in existing_list}
    schemas = req(base_url, ver, key, "/downloadclient/schema")

    clients = [
        ("qBittorrent", "QBittorrent", {"host": QBIT_HOST, "port": 8080, "movieCategory": category, "tvCategory": category}),
    ]

    for display_name, impl, overrides in clients:
        if display_name in existing_map:
            current = existing_map[display_name]
            changed = False
            for f in current.get("fields", []):
                if f["name"] in overrides and f.get("value") != overrides[f["name"]]:
                    f["value"] = overrides[f["name"]]
                    changed = True
            if changed:
                req(base_url, ver, key, f"/downloadclient/{current['id']}?forceSave=true", "PUT", current)
                print(f"[OK] Download client atualizado: {display_name} -> host={QBIT_HOST} ({category})")
            else:
                print(f"[SKIP] Download client já está atualizado: {display_name} ({QBIT_HOST})")
            continue

        tmpl = next(s for s in schemas if s["implementation"] == impl)
        tmpl["name"] = display_name
        tmpl["enable"] = True
        tmpl["priority"] = 1
        for f in tmpl["fields"]:
            if f["name"] in overrides:
                f["value"] = overrides[f["name"]]
        req(base_url, ver, key, "/downloadclient?forceSave=true", "POST", tmpl)
        print(f"[OK] Download client registrado: {display_name} -> host={QBIT_HOST} ({category})")


def _build_cf_spec(schemas, impl_name, spec_name, value, negate=False, required=False):
    tmpl = copy.deepcopy(next(s for s in schemas if s["implementation"] == impl_name))
    tmpl["name"] = spec_name
    tmpl["negate"] = negate
    tmpl["required"] = required
    for f in tmpl.get("fields", []):
        if f.get("name") == "value":
            f["value"] = value
    return tmpl


def ensure_original_audio_only(base_url, ver, key, service_name):
    if not AUDIO_ORIGINAL_ONLY:
        print(f"[SKIP] Filtro de áudio original desativado (AUDIO_ORIGINAL_ONLY=false) no {service_name}.")
        return

    schemas = req(base_url, ver, key, "/customformat/schema") or []
    lang_schema = next((s for s in schemas if s["implementation"] == "LanguageSpecification"), None)
    if not lang_schema:
        print(f"[WARN] LanguageSpecification não encontrada no schema do {service_name}.")
        return

    original_lang_id = -2
    for f in lang_schema.get("fields", []):
        if f.get("name") == "value":
            for opt in f.get("selectOptions", []):
                if str(opt.get("name", "")).strip().lower() == "original":
                    original_lang_id = opt["value"]
                    break

    desired_cfs = [
        {
            "name": "Original Audio",
            "includeCustomFormatWhenRenaming": False,
            "specifications": [
                _build_cf_spec(schemas, "LanguageSpecification", "Original Language", original_lang_id, negate=False, required=True),
            ],
        },
        {
            "name": "Dubbed / Non-Original Audio",
            "includeCustomFormatWhenRenaming": False,
            "specifications": [
                _build_cf_spec(schemas, "LanguageSpecification", "Not Original Language", original_lang_id, negate=True, required=False),
                _build_cf_spec(schemas, "ReleaseTitleSpecification", "Dubbed or Dual Title", r"\b(DUBLADO|DUBBED|DUB|DUAL)\b", negate=False, required=False),
            ],
        },
    ]

    existing_cfs = {cf["name"]: cf for cf in (req(base_url, ver, key, "/customformat") or [])}
    cf_ids = {}

    for desired in desired_cfs:
        name = desired["name"]
        if name in existing_cfs:
            current = existing_cfs[name]
            desired_with_id = dict(desired, id=current["id"])
            req(base_url, ver, key, f"/customformat/{current['id']}", "PUT", desired_with_id)
            cf_ids[name] = current["id"]
        else:
            created = req(base_url, ver, key, "/customformat", "POST", desired)
            cf_ids[name] = created["id"]

    target_scores = {
        cf_ids["Original Audio"]: 1000,
        cf_ids["Dubbed / Non-Original Audio"]: -10000,
    }

    profiles = req(base_url, ver, key, "/qualityprofile") or []
    updated_profiles = 0
    for prof in profiles:
        changed = False
        if isinstance(prof.get("language"), dict) and prof["language"].get("id") != original_lang_id:
            prof["language"] = {"id": original_lang_id, "name": "Original"}
            changed = True

        if prof.get("minFormatScore", 0) < 0:
            prof["minFormatScore"] = 0
            changed = True

        items = prof.get("formatItems") or []
        seen_ids = set()
        for item in items:
            fid = item.get("format")
            if fid in target_scores:
                seen_ids.add(fid)
                if item.get("score") != target_scores[fid]:
                    item["score"] = target_scores[fid]
                    changed = True

        for cf_name, fid in cf_ids.items():
            if fid not in seen_ids:
                items.append({"format": fid, "name": cf_name, "score": target_scores[fid]})
                changed = True

        if changed:
            prof["formatItems"] = items
            req(base_url, ver, key, f"/qualityprofile/{prof['id']}", "PUT", prof)
            updated_profiles += 1

    if updated_profiles:
        print(f"[OK] Áudio original obrigatório aplicado em {updated_profiles} perfis do {service_name} (Original=+1000, Dublado/Não-Original=-10000).")
    else:
        print(f"[SKIP] Regra de áudio original já configurada nos perfis do {service_name}.")


def ensure_max_size_limit(base_url, ver, key, max_mb_per_min, service_name):
    definitions = req(base_url, ver, key, "/qualitydefinition") or []
    updated = 0
    for item in definitions:
        changed = False
        if item.get("maxSize") is None or item["maxSize"] > max_mb_per_min:
            item["maxSize"] = max_mb_per_min
            changed = True
        if item.get("preferredSize") is not None and item["preferredSize"] > max_mb_per_min:
            item["preferredSize"] = max_mb_per_min
            changed = True
        if item.get("minSize") is not None and item["minSize"] > max_mb_per_min:
            item["minSize"] = 0
            changed = True
        if changed:
            req(base_url, ver, key, f"/qualitydefinition/{item['id']}", "PUT", item)
            updated += 1
    if updated:
        print(f"[OK] Limite máximo atualizado em {updated} perfis de qualidade do {service_name} (<= {max_mb_per_min} MB/min).")
    else:
        print(f"[SKIP] Limite de tamanho já configurado no {service_name} (<= {max_mb_per_min} MB/min).")


def ensure_prowlarr_apps():
    base_url, ver, key = SERVICES["prowlarr"]
    existing_list = req(base_url, ver, key, "/applications") or []
    existing_map = {a["name"]: a for a in existing_list}
    schemas = req(base_url, ver, key, "/applications/schema")

    apps = [
        ("Radarr", "Radarr", RADARR_BASE_URL, RADARR_API_KEY),
        ("Sonarr", "Sonarr", SONARR_BASE_URL, SONARR_API_KEY),
    ]

    for display_name, impl, app_url, app_key in apps:
        desired_fields = {
            "prowlarrUrl": PROWLARR_BASE_URL,
            "baseUrl": app_url,
            "apiKey": app_key,
        }
        if display_name in existing_map:
            current = existing_map[display_name]
            changed = False
            for f in current.get("fields", []):
                if f["name"] in desired_fields and f.get("value") != desired_fields[f["name"]]:
                    f["value"] = desired_fields[f["name"]]
                    changed = True
            if changed:
                req(base_url, ver, key, f"/applications/{current['id']}?forceSave=true", "PUT", current)
                print(f"[OK] Aplicação atualizada no Prowlarr: {display_name} -> {app_url}")
            else:
                print(f"[SKIP] Aplicação já está atualizada no Prowlarr: {display_name} ({app_url})")
            continue

        tmpl = next(s for s in schemas if s["implementation"] == impl)
        tmpl["name"] = display_name
        tmpl["syncLevel"] = "fullSync"
        for f in tmpl["fields"]:
            if f["name"] in desired_fields:
                f["value"] = desired_fields[f["name"]]
        req(base_url, ver, key, "/applications?forceSave=true", "POST", tmpl)
        print(f"[OK] Aplicação vinculada ao Prowlarr: {display_name} -> {app_url}")


def ensure_prowlarr_indexers():
    base_url, ver, key = SERVICES["prowlarr"]
    existing = {i["name"].lower() for i in req(base_url, ver, key, "/indexer")}
    schemas = req(base_url, ver, key, "/indexer/schema")

    added = False
    for target in PROWLARR_INDEXERS:
        if target.lower() in existing:
            print(f"[SKIP] Indexador já existe no Prowlarr: {target}")
            continue
        tmpl = next((s for s in schemas if s.get("name", "").lower() == target.lower()), None)
        if not tmpl:
            print(f"[WARN] Template de indexador não encontrado: {target}")
            continue
        tmpl["enable"] = True
        tmpl["appProfileId"] = 1
        tmpl["priority"] = 25
        for f in tmpl.get("fields", []):
            if f.get("name") == "torrentBaseSettings.minimumSeeders":
                f["value"] = PROWLARR_MIN_SEEDERS
        try:
            req(base_url, ver, key, "/indexer?forceSave=true", "POST", tmpl)
            print(f"[OK] Indexador adicionado ao Prowlarr: {target} (minSeeders={PROWLARR_MIN_SEEDERS})")
            added = True
        except urllib.error.HTTPError:
            print(f"[WARN] Não foi possível validar {target} agora; pulando para continuar o provisionamento.")

    if added or existing:
        req(base_url, ver, key, "/command", "POST", {"name": "ApplicationIndexerSync"})
        print("[OK] Sincronização de indexadores disparada para Radarr e Sonarr.")


def setup_bazarr():
    profiles = bazarr_req("/system/languages/profiles") or []
    target_langs = set(BAZARR_LANGUAGES)
    has_profile = any(
        p.get("name") == BAZARR_PROFILE_NAME
        and {item.get("language") for item in p.get("items", [])} >= target_langs
        and all(item.get("hi") == BAZARR_ALLOW_HI for item in p.get("items", []))
        and p.get("cutoff") is None
        for p in profiles
    )

    if has_profile:
        print(f"[SKIP] Perfil de legendas '{BAZARR_PROFILE_NAME}' já existe no Bazarr.")
    else:
        items = [
            {
                "id": idx,
                "language": lang,
                "audio_exclude": "False",
                "hi": BAZARR_ALLOW_HI,
                "forced": "False",
            }
            for idx, lang in enumerate(BAZARR_LANGUAGES, start=1)
        ]
        profile_payload = json.dumps([
            {
                "profileId": 1,
                "name": BAZARR_PROFILE_NAME,
                "cutoff": None,
                "items": items,
                "mustContain": [],
                "mustNotContain": [],
                "originalFormat": False,
            }
        ])

        settings_fields = [("languages-enabled", lang) for lang in BAZARR_LANGUAGES]
        settings_fields.extend([
            ("languages-profiles", profile_payload),
            ("settings-general-serie_default_enabled", "true"),
            ("settings-general-serie_default_profile", "1"),
            ("settings-general-movie_default_enabled", "true"),
            ("settings-general-movie_default_profile", "1"),
        ])
        bazarr_req("/system/settings", "POST", settings_fields)
        print(f"[OK] Perfil de legendas '{BAZARR_PROFILE_NAME}' ({','.join(BAZARR_LANGUAGES)}) criado no Bazarr.")

    # Garante que filmes e séries já sincronizados anteriormente também recebam o perfil 1
    try:
        movies_resp = bazarr_req("/movies") or {}
        for m in movies_resp.get("data", []):
            if m.get("profileId") != 1 and m.get("radarrId") is not None:
                bazarr_req("/movies", "POST", [("radarrid", m["radarrId"]), ("profileid", 1)])
        series_resp = bazarr_req("/series") or {}
        for s in series_resp.get("data", []):
            if s.get("profileId") != 1 and s.get("sonarrSeriesId") is not None:
                bazarr_req("/series", "POST", [("seriesid", s["sonarrSeriesId"]), ("profileid", 1)])
    except Exception as e:
        print(f"[WARN] Não foi possível atualizar perfil de itens existentes no Bazarr: {e}")

    current_settings = bazarr_req("/system/settings") or {}
    auth_cfg = current_settings.get("auth", {})
    general_cfg = current_settings.get("general", {})
    radarr_cfg = current_settings.get("radarr", {})
    sonarr_cfg = current_settings.get("sonarr", {})
    current_providers = general_cfg.get("enabled_providers", [])
    current_os_user = current_settings.get("opensubtitlescom", {}).get("username", "")
    current_subsource_key = current_settings.get("subsource", {}).get("apikey", "")

    providers = list(BAZARR_DEFAULT_PROVIDERS)
    form_fields = [
        ("settings-general-base_url", "/bazarr"),
        ("settings-radarr-base_url", "/radarr"),
        ("settings-sonarr-base_url", "/sonarr"),
        ("settings-general-minimum_score_movie", str(BAZARR_MIN_SCORE_MOVIE)),
        ("settings-general-minimum_score", str(BAZARR_MIN_SCORE_SERIES)),
        ("settings-general-auto_sync", "true" if BAZARR_AUTO_SYNC else "false"),
    ]

    auth_ready = True
    if BAZARR_ADMIN_USER and BAZARR_ADMIN_PASS:
        form_fields.extend([
            ("settings-auth-type", "form"),
            ("settings-auth-username", BAZARR_ADMIN_USER),
            ("settings-auth-password", BAZARR_ADMIN_PASS),
        ])
        login_ok = False
        if str(auth_cfg.get("type", "")).lower() == "form" and auth_cfg.get("username") == BAZARR_ADMIN_USER:
            try:
                cj = http.cookiejar.CookieJar()
                opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
                login_data = urllib.parse.urlencode({
                    "username": BAZARR_ADMIN_USER,
                    "password": BAZARR_ADMIN_PASS,
                }).encode("utf-8")
                login_req = urllib.request.Request(f"{BAZARR_URL}/login", data=login_data, method="POST")
                with opener.open(login_req, timeout=10) as resp:
                    login_ok = not resp.geturl().rstrip("/").endswith("/login")
            except Exception:
                login_ok = False
        auth_ready = login_ok

    if OPENSUBTITLES_USER and OPENSUBTITLES_PASS:
        if "opensubtitlescom" not in providers:
            providers.append("opensubtitlescom")
        form_fields.extend([
            ("settings-opensubtitlescom-username", OPENSUBTITLES_USER),
            ("settings-opensubtitlescom-password", OPENSUBTITLES_PASS),
        ])

    if SUBSOURCE_API_KEY:
        if "subsource" not in providers:
            providers.append("subsource")
        form_fields.append(("settings-subsource-apikey", SUBSOURCE_API_KEY))

    already_configured = (
        auth_ready
        and set(providers) <= set(current_providers)
        and general_cfg.get("base_url") == "/bazarr"
        and radarr_cfg.get("base_url") == "/radarr"
        and sonarr_cfg.get("base_url") == "/sonarr"
        and int(general_cfg.get("minimum_score_movie", 0)) == BAZARR_MIN_SCORE_MOVIE
        and int(general_cfg.get("minimum_score", 0)) == BAZARR_MIN_SCORE_SERIES
        and bool(general_cfg.get("auto_sync", False)) is BAZARR_AUTO_SYNC
        and (not (OPENSUBTITLES_USER and OPENSUBTITLES_PASS) or current_os_user == OPENSUBTITLES_USER)
        and (not SUBSOURCE_API_KEY or current_subsource_key == SUBSOURCE_API_KEY)
    )

    if already_configured:
        print("[SKIP] Autenticação (form), provedores, subpaths (/bazarr, /radarr, /sonarr) e score mínimo já configurados no Bazarr.")
        return

    for p in providers:
        form_fields.append(("settings-general-enabled_providers", p))

    bazarr_req("/system/settings", "POST", form_fields)
    auth_msg = f", auth=form ('{BAZARR_ADMIN_USER}')" if (BAZARR_ADMIN_USER and BAZARR_ADMIN_PASS) else ""
    print(f"[OK] Bazarr configurado: subpaths (/bazarr, /radarr, /sonarr){auth_msg}, provedores {providers}, score {BAZARR_MIN_SCORE_MOVIE}%/{BAZARR_MIN_SCORE_SERIES}%.")


def ensure_arr_auth(base_url, ver, key, service_name):
    if not ARR_ADMIN_USER or not ARR_ADMIN_PASS:
        print(f"[SKIP] Credenciais administrativas não definidas para {service_name}.")
        return

    cfg = req(base_url, ver, key, "/config/host")
    if not cfg:
        print(f"[WARN] Não foi possível obter /config/host em {service_name}.")
        return

    required_hosts = [APP_HOST, "prowlarr", "radarr", "sonarr", "localhost", "127.0.0.1"]
    existing_hosts = [
        h.strip()
        for h in (cfg.get("allowedHosts") or "").split(",")
        if h.strip() and h.strip() != "*"
    ]
    merged_hosts = list(dict.fromkeys(existing_hosts + required_hosts))

    cfg["authenticationMethod"] = "forms"
    cfg["authenticationRequired"] = "disabledForLocalAddresses"
    cfg["allowedHosts"] = ",".join(merged_hosts)
    cfg["username"] = ARR_ADMIN_USER
    cfg["password"] = ARR_ADMIN_PASS
    cfg["passwordConfirmation"] = ARR_ADMIN_PASS

    req(base_url, ver, key, f"/config/host/{cfg['id']}", "PUT", cfg)
    print(f"[OK] Usuário administrativo '{ARR_ADMIN_USER}' configurado em {service_name} (AllowedHosts={cfg['allowedHosts']}).")


def configure_jellyfin_transcoding(token):
    if not JF_HWACCEL or JF_HWACCEL in {"none", "false", "0"}:
        return

    try:
        enc_cfg = jf_api("GET", "/System/Configuration/encoding", token=token) or {}
        if JF_HWACCEL == "rkmpp":
            target_codecs = ["h264", "hevc", "mpeg2video", "vp9", "av1", "hevc10bit", "vp910bit"]
            changed = False

            if enc_cfg.get("HardwareAccelerationType") != "rkmpp":
                enc_cfg["HardwareAccelerationType"] = "rkmpp"
                changed = True
            if not enc_cfg.get("EnableHardwareEncoding", False):
                enc_cfg["EnableHardwareEncoding"] = True
                changed = True
            if "AllowHevcEncoding" in enc_cfg and not enc_cfg["AllowHevcEncoding"]:
                enc_cfg["AllowHevcEncoding"] = True
                changed = True
            if "EnableToneMapping" in enc_cfg and not enc_cfg["EnableToneMapping"]:
                enc_cfg["EnableToneMapping"] = True
                changed = True

            current_codecs = enc_cfg.get("HardwareDecodingCodecs") or []
            if set(target_codecs) - set(current_codecs):
                enc_cfg["HardwareDecodingCodecs"] = list(dict.fromkeys(current_codecs + target_codecs))
                changed = True

            if changed:
                jf_api("POST", "/System/Configuration/encoding", payload=enc_cfg, token=token)
                print("[OK] Aceleração de hardware Rockchip MPP (rkmpp) ativada no Jellyfin.")
            else:
                print("[SKIP] Aceleração de hardware Rockchip MPP (rkmpp) já ativa no Jellyfin.")
    except Exception as e:
        print(f"[WARN] Não foi possível configurar transcodificação por hardware ({JF_HWACCEL}): {e}")


def setup_jellyfin():
    info = jf_api("GET", "/System/Info/Public")
    if not info.get("StartupWizardCompleted", False):
        jf_api("POST", "/Startup/Configuration", {
            "UICulture": JF_UI_CULTURE,
            "MetadataCountryCode": JF_METADATA_COUNTRY,
            "PreferredMetadataLanguage": JF_METADATA_LANG,
        })
        jf_api("GET", "/Startup/FirstUser")
        jf_api("POST", "/Startup/User", {"Name": JF_USER, "Password": JF_PASS})
        jf_api("POST", "/Startup/RemoteAccess", {
            "EnableRemoteAccess": True,
            "EnableAutomaticPortMapping": False,
        })
        jf_api("POST", "/Startup/Complete")
        print(f"[OK] Assistente inicial do Jellyfin concluído (usuário: {JF_USER}).")
        time.sleep(1)
    else:
        print("[SKIP] Assistente inicial do Jellyfin já foi concluído.")

    try:
        auth = jf_api("POST", "/Users/AuthenticateByName", {"Username": JF_USER, "Pw": JF_PASS})
    except RuntimeError as e:
        if "[ERRO HTTP 401]" in str(e) and JF_PASS != "admin":
            auth = jf_api("POST", "/Users/AuthenticateByName", {"Username": JF_USER, "Pw": "admin"})
            user_id = auth["User"]["Id"]
            jf_api(
                "POST",
                f"/Users/{user_id}/Password",
                {"CurrentPw": "admin", "NewPw": JF_PASS},
                token=auth["AccessToken"],
            )
            print(f"[OK] Senha do usuário '{JF_USER}' atualizada no Jellyfin.")
            auth = jf_api("POST", "/Users/AuthenticateByName", {"Username": JF_USER, "Pw": JF_PASS})
        else:
            raise
    token = auth["AccessToken"]

    sys_cfg = jf_api("GET", "/System/Configuration", token=token)
    sys_cfg["ServerName"] = JF_SERVER_NAME
    sys_cfg["UICulture"] = JF_UI_CULTURE
    sys_cfg["MetadataCountryCode"] = JF_METADATA_COUNTRY
    sys_cfg["PreferredMetadataLanguage"] = JF_METADATA_LANG
    sys_cfg["LibraryMonitorDelay"] = JF_MONITOR_DELAY
    jf_api("POST", "/System/Configuration", payload=sys_cfg, token=token)

    configure_jellyfin_transcoding(token)

    folders = jf_api("GET", "/Library/VirtualFolders", token=token)
    existing_paths = {loc for f in folders for loc in f.get("Locations", [])}

    libraries = [
        ("Movies", "movies", "/data/media/movies"),
        ("TV Shows", "tvshows", "/data/media/tv"),
    ]

    for lib_name, col_type, lib_path in libraries:
        if lib_path in existing_paths:
            print(f"[SKIP] Biblioteca Jellyfin já existe: {lib_name} ({lib_path})")
            continue
        query = f"name={urllib.parse.quote(lib_name)}&collectionType={col_type}&paths={urllib.parse.quote(lib_path, safe='')}&refreshLibrary=true"
        jf_api("POST", f"/Library/VirtualFolders?{query}", payload={
            "LibraryOptions": {
                "EnableRealtimeMonitor": True,
                "PreferredMetadataLanguage": JF_METADATA_LANG,
                "MetadataCountryCode": JF_METADATA_COUNTRY,
                "PathInfos": [{"Path": lib_path}],
            }
        }, token=token)
        print(f"[OK] Biblioteca Jellyfin criada: {lib_name} ({lib_path})")

    keys_resp = jf_api("GET", "/Auth/Keys", token=token) or {}
    for item in keys_resp.get("Items", []):
        if item.get("AppName") == "ArrStack":
            return item["AccessToken"]

    jf_api("POST", "/Auth/Keys?app=ArrStack", token=token)
    keys_resp = jf_api("GET", "/Auth/Keys", token=token) or {}
    for item in keys_resp.get("Items", []):
        if item.get("AppName") == "ArrStack":
            return item["AccessToken"]
    raise RuntimeError("Não foi possível gerar a API Key do Jellyfin.")


def write_jellyfin_refresh_script(container_name, jf_apikey):
    auth_header = (
        'MediaBrowser Client="ArrStack", Device="Docker", '
        f'DeviceId="arr-refresh-1", Version="1.0.0", Token="{jf_apikey}"'
    )
    script_content = (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f'curl -fsS -X POST "http://jellyfin:8096/Library/Refresh" -H \'Authorization: {auth_header}\'\n'
    )
    b64 = base64.b64encode(script_content.encode("utf-8")).decode("ascii")
    docker_exec(
        container_name,
        [
            "sh",
            "-c",
            f"echo '{b64}' | base64 -d > /config/refresh_jellyfin.sh && chmod +x /config/refresh_jellyfin.sh && chown {PUID}:{PGID} /config/refresh_jellyfin.sh",
        ],
    )
    print(f"[OK] Script /config/refresh_jellyfin.sh atualizado em {container_name}.")


def ensure_jellyfin_connect(base_url, ver, key, jf_apikey, service_name):
    container_name = service_name.lower()
    write_jellyfin_refresh_script(container_name, jf_apikey)

    existing_list = req(base_url, ver, key, "/notification") or []
    schemas = req(base_url, ver, key, "/notification/schema")

    # 1. Notificação nativa MediaBrowser (Jellyfin)
    existing_jf = next((n for n in existing_list if n["name"] == "Jellyfin"), None)
    if existing_jf:
        existing_jf["onDownload"] = True
        existing_jf["onUpgrade"] = True
        existing_jf["onRename"] = True
        for f in existing_jf.get("fields", []):
            if f["name"] == "apiKey":
                f["value"] = jf_apikey
            elif f["name"] == "updateLibrary":
                f["value"] = True
            elif f["name"] == "host":
                f["value"] = "jellyfin"
            elif f["name"] == "port":
                f["value"] = 8096
        req(base_url, ver, key, f"/notification/{existing_jf['id']}?forceSave=true", "PUT", existing_jf)
        print(f"[OK] Conexão nativa Jellyfin atualizada em {service_name}.")
    else:
        tmpl = next(s for s in schemas if s["implementation"] == "MediaBrowser")
        tmpl["name"] = "Jellyfin"
        for event_flag in [
            "onDownload",
            "onUpgrade",
            "onRename",
            "onMovieDelete",
            "onMovieFileDelete",
            "onSeriesDelete",
            "onEpisodeFileDelete",
        ]:
            if event_flag in tmpl:
                tmpl[event_flag] = True

        overrides = {
            "host": "jellyfin",
            "port": 8096,
            "useSsl": False,
            "apiKey": jf_apikey,
            "updateLibrary": True,
            "notify": False,
        }
        for f in tmpl["fields"]:
            if f["name"] in overrides:
                f["value"] = overrides[f["name"]]

        req(base_url, ver, key, "/notification?forceSave=true", "POST", tmpl)
        print(f"[OK] Conexão nativa Jellyfin registrada em {service_name}.")

    # 2. Custom Script para disparar varredura completa (/Library/Refresh) na importação
    script_name = "Jellyfin Library Scan"
    script_path = "/config/refresh_jellyfin.sh"
    existing_script = next((n for n in existing_list if n["name"] == script_name), None)

    active_events = {
        "onDownload",
        "onUpgrade",
        "onRename",
        "onMovieDelete",
        "onMovieFileDelete",
        "onMovieFileDeleteForUpgrade",
        "onSeriesDelete",
        "onEpisodeFileDelete",
        "onEpisodeFileDeleteForUpgrade",
    }
    inactive_events = {
        "onGrab",
        "onMovieAdded",
        "onSeriesAdd",
        "onHealthIssue",
        "onHealthRestored",
        "onApplicationUpdate",
        "onManualInteractionRequired",
    }

    if existing_script:
        for flag in active_events:
            if flag in existing_script:
                existing_script[flag] = True
        for flag in inactive_events:
            if flag in existing_script:
                existing_script[flag] = False
        for f in existing_script.get("fields", []):
            if f["name"] == "path":
                f["value"] = script_path
        req(base_url, ver, key, f"/notification/{existing_script['id']}?forceSave=true", "PUT", existing_script)
        print(f"[OK] Custom Script '{script_name}' atualizado em {service_name}.")
    else:
        script_tmpl = next(s for s in schemas if s["implementation"] == "CustomScript")
        script_tmpl["name"] = script_name
        for flag in active_events:
            if flag in script_tmpl:
                script_tmpl[flag] = True
        for flag in inactive_events:
            if flag in script_tmpl:
                script_tmpl[flag] = False
        for f in script_tmpl.get("fields", []):
            if f["name"] == "path":
                f["value"] = script_path
        req(base_url, ver, key, "/notification?forceSave=true", "POST", script_tmpl)
        print(f"[OK] Custom Script '{script_name}' registrado em {service_name}.")


def setup_seerr():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def seerr_req(path, method="GET", payload=None):
        url = f"{SEERR_URL}/api/v1{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"}
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with opener.open(request, timeout=15) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else None
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            print(f"[ERRO HTTP {e.code}] Seerr {method} {url} -> {err_body}")
            raise

    pub = seerr_req("/settings/public", "GET") or {}
    if pub.get("initialized", False):
        print("[SKIP] Seerr já inicializado.")
        return

    try:
        seerr_req("/auth/jellyfin", "POST", {
            "username": JF_USER,
            "password": JF_PASS,
            "hostname": "jellyfin",
            "port": 8096,
            "useSsl": False,
            "urlBase": "",
            "serverType": 2,
        })
        print("[OK] Seerr autenticado e vinculado ao Jellyfin.")
    except urllib.error.HTTPError as e:
        if e.code == 500:
            seerr_req("/auth/jellyfin", "POST", {
                "username": JF_USER,
                "password": JF_PASS,
            })
            print("[OK] Seerr autenticado (servidor Jellyfin já vinculado).")
        else:
            raise

    libs = seerr_req("/settings/jellyfin/library", "GET") or []
    lib_ids = ",".join(lib["id"] for lib in libs if lib.get("id"))
    if lib_ids:
        seerr_req(f"/settings/jellyfin/library?enable={urllib.parse.quote(lib_ids)}", "GET")
        print(f"[OK] Bibliotecas do Jellyfin sincronizadas e habilitadas no Seerr ({len(libs)}).")

    existing_radarr = seerr_req("/settings/radarr", "GET") or []
    if any(r.get("hostname") == "radarr" for r in existing_radarr):
        print("[SKIP] Radarr já configurado no Seerr.")
    else:
        seerr_req("/settings/radarr", "POST", {
            "name": "Radarr",
            "hostname": "radarr",
            "port": 7878,
            "apiKey": RADARR_API_KEY,
            "useSsl": False,
            "baseUrl": "/radarr",
            "activeProfileId": SEERR_PROFILE_ID,
            "activeProfileName": SEERR_PROFILE_NAME,
            "activeDirectory": "/data/media/movies",
            "is4k": False,
            "minimumAvailability": "announced",
            "isDefault": True,
            "externalUrl": "",
            "syncEnabled": True,
            "preventSearch": False,
        })
        print("[OK] Radarr registrado no Seerr (baseUrl=/radarr).")

    existing_sonarr = seerr_req("/settings/sonarr", "GET") or []
    if any(s.get("hostname") == "sonarr" for s in existing_sonarr):
        print("[SKIP] Sonarr já configurado no Seerr.")
    else:
        seerr_req("/settings/sonarr", "POST", {
            "name": "Sonarr",
            "hostname": "sonarr",
            "port": 8989,
            "apiKey": SONARR_API_KEY,
            "useSsl": False,
            "baseUrl": "/sonarr",
            "activeProfileId": SEERR_PROFILE_ID,
            "activeProfileName": SEERR_PROFILE_NAME,
            "activeDirectory": "/data/media/tv",
            "is4k": False,
            "enableSeasonFolders": True,
            "isDefault": True,
            "externalUrl": "",
            "syncEnabled": True,
            "preventSearch": False,
        })
        print("[OK] Sonarr registrado no Seerr (baseUrl=/sonarr).")

    seerr_req("/settings/initialize", "POST")
    print("[OK] Assistente inicial do Seerr finalizado.")


if __name__ == "__main__":
    wait_ready()
    setup_qbittorrent()

    p_url, p_ver, p_key = SERVICES["prowlarr"]
    r_url, r_ver, r_key = SERVICES["radarr"]
    ensure_root_folder(r_url, r_ver, r_key, "/data/media/movies")
    enable_renaming(r_url, r_ver, r_key, "renameMovies")
    ensure_download_clients(r_url, r_ver, r_key, "movies")
    ensure_max_size_limit(r_url, r_ver, r_key, RADARR_MAX_SIZE_MB_MIN, "Radarr")
    ensure_original_audio_only(r_url, r_ver, r_key, "Radarr")

    s_url, s_ver, s_key = SERVICES["sonarr"]
    ensure_root_folder(s_url, s_ver, s_key, "/data/media/tv")
    enable_renaming(s_url, s_ver, s_key, "renameEpisodes")
    ensure_download_clients(s_url, s_ver, s_key, "tv")
    ensure_max_size_limit(s_url, s_ver, s_key, SONARR_MAX_SIZE_MB_MIN, "Sonarr")
    ensure_original_audio_only(s_url, s_ver, s_key, "Sonarr")

    ensure_arr_auth(p_url, p_ver, p_key, "Prowlarr")
    ensure_arr_auth(r_url, r_ver, r_key, "Radarr")
    ensure_arr_auth(s_url, s_ver, s_key, "Sonarr")

    ensure_prowlarr_apps()
    ensure_prowlarr_indexers()
    setup_bazarr()
    jf_apikey = setup_jellyfin()
    ensure_jellyfin_connect(r_url, r_ver, r_key, jf_apikey, "Radarr")
    ensure_jellyfin_connect(s_url, s_ver, s_key, jf_apikey, "Sonarr")
    setup_seerr()
    print("Provisionamento concluído com sucesso.")
