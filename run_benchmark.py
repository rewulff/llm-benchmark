#!/usr/bin/env python3
"""LLM Benchmark Suite fuer lokale Knecht-Modelle.

Testet Modelle in 3 Kategorien:
  A. Code-Tasks (smolagents Agent-Modus)
  B. Text-Analyse (direkter API-Call)
  C. Reasoning (direkter API-Call)

Usage:
  python3 run_benchmark.py --config configs/qwen3-coder-30b.json
  python3 run_benchmark.py --config configs/qwen3-coder-30b.json --categories code
  python3 run_benchmark.py --haiku-baseline
  python3 run_benchmark.py --compare
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"
CONFIGS_DIR = SCRIPT_DIR / "configs"
FIXTURES_DIR = SCRIPT_DIR / "fixtures"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 1235


# ---------------------------------------------------------------------------
# Fixtures — Test-Dateien die automatisch generiert/zurueckgesetzt werden
# ---------------------------------------------------------------------------

CALCULATOR_PY = textwrap.dedent("""\
    def add(a, b):
        return a + b

    def multiply(a, b):
        return a + b  # Bug 1: should be a * b

    def divide(a, b):
        return a / b  # Bug 2: no zero division check

    def average(numbers):
        total = sum(numbers)
        # Bug 3: missing return statement
        total / len(numbers)
""")

FLASK_APP_PY = textwrap.dedent("""\
    from flask import Flask, request, jsonify

    app = Flask(__name__)

    users = {}

    @app.route('/users', methods=['GET'])
    def get_users():
        return jsonify(list(users.values()))

    @app.route('/users', methods=['POST'])
    def create_user():
        data = request.get_json()
        user_id = len(users) + 1
        users[user_id] = {"id": user_id, "name": data["name"], "email": data["email"]}
        return jsonify(users[user_id]), 201

    @app.route('/users/<int:user_id>', methods=['GET'])
    def get_user(user_id):
        return jsonify(users[user_id])

    @app.route('/users/<int:user_id>', methods=['PUT'])
    def update_user(user_id):
        data = request.get_json()
        users[user_id]["name"] = data["name"]
        users[user_id]["email"] = data["email"]
        return jsonify(users[user_id])

    @app.route('/users/<int:user_id>', methods=['DELETE'])
    def delete_user(user_id):
        del users[user_id]
        return '', 204

    if __name__ == '__main__':
        app.run(debug=True)
""")

SUMMARY_TEXT = textwrap.dedent("""\
    Proxmox Virtual Environment (PVE) is an open-source virtualization platform
    based on Debian Linux that supports both KVM-based virtual machines and
    LXC containers. In production environments, regular maintenance of these
    systems is critical for operational stability.

    A central element of PVE maintenance is update management. Both the Proxmox
    host itself and all running containers and VMs need to be updated. For LXC
    containers, this is typically done via package manager commands (apt, apk, dnf),
    while VMs are updated through their own operating system mechanisms.

    Special care is required for host kernel updates, as they require a reboot
    and briefly affect all running guests. Proxmox's snapshot functionality allows
    creating a restore point before critical updates, enabling rollback in case
    of failure. This is particularly relevant for community-script containers,
    which often have special configurations where standard update procedures may fail.

    Automating these maintenance processes through scripts or dedicated tools
    significantly reduces manual effort and minimizes the risk of human error.
    Robust error handling that automatically triggers rollback mechanisms and
    notifies the administrator is essential. Monitoring systems like Gotify or
    Ntfy can be used for push notifications to track maintenance run status in real time.
""")

PVE_LOG = textwrap.dedent("""\
    2026-02-17 02:00:01 [INFO] === PVE Maintenance Run Started ===
    2026-02-17 02:00:01 [INFO] Host: lab-pve-02, Node: lab-pve-02
    2026-02-17 02:00:03 [INFO] Phase 1: Host health check
    2026-02-17 02:00:03 [OK] CPU: 12%, RAM: 45%, Disk: 62%
    2026-02-17 02:00:05 [INFO] Phase 2: Container updates
    2026-02-17 02:00:05 [INFO] CT 100 (debian-12): Starting update...
    2026-02-17 02:00:45 [OK] CT 100: 3 packages updated
    2026-02-17 02:00:46 [INFO] CT 101 (ubuntu-22): Starting update...
    2026-02-17 02:01:30 [OK] CT 101: 7 packages updated
    2026-02-17 02:01:31 [INFO] CT 102 (alpine-3.19): Starting update...
    2026-02-17 02:01:35 [ERROR] CT 102: apk update failed - network timeout
    2026-02-17 02:01:36 [WARN] CT 102: Retry 1/3...
    2026-02-17 02:01:50 [ERROR] CT 102: apk update failed - network timeout
    2026-02-17 02:01:51 [WARN] CT 102: Retry 2/3...
    2026-02-17 02:02:05 [OK] CT 102: 1 package updated (retry succeeded)
    2026-02-17 02:02:06 [INFO] CT 103 (forgejo): Starting update...
    2026-02-17 02:02:10 [WARN] CT 103: community-script container detected
    2026-02-17 02:02:12 [INFO] CT 103: Using custom handler
    2026-02-17 02:02:45 [OK] CT 103: app updated to v9.1.2
    2026-02-17 02:02:46 [INFO] CT 104 (searxng): Starting update...
    2026-02-17 02:02:48 [ERROR] CT 104: Permission denied - /opt/searxng/venv
    2026-02-17 02:02:48 [ERROR] CT 104: Update FAILED - file ownership mismatch (root vs searxng)
    2026-02-17 02:02:49 [WARN] CT 104: security_flag=true, app_update=failed
    2026-02-17 02:02:50 [INFO] Phase 3: VM snapshots
    2026-02-17 02:02:50 [INFO] VM 200 (win11): Creating snapshot...
    2026-02-17 02:03:30 [OK] VM 200: Snapshot 'pre-update-20260217' created
    2026-02-17 02:03:31 [INFO] Phase 4: Summary
    2026-02-17 02:03:31 [OK] Updated: 4/5 containers, 1/1 VMs
    2026-02-17 02:03:31 [ERROR] Failed: CT 104 (searxng) - permission denied
    2026-02-17 02:03:31 [WARN] Issues: CT 102 network timeout (resolved), CT 104 ownership
    2026-02-17 02:03:32 [INFO] === Run completed in 212s ===
""")

STATS_DATA = textwrap.dedent("""\
    Monthly sales figures (units) for 3 product lines, Jan-Dec 2025:

    Month    | Product A | Product B | Product C
    ---------|-----------|-----------|----------
    January  |    1200   |     800   |     450
    February |    1150   |     820   |     470
    March    |    1300   |     790   |     460
    April    |    1250   |     810   |     480
    May      |    1280   |     830   |     490
    June     |    1350   |    3200   |     500
    July     |    1320   |     850   |     510
    August   |    1290   |     840   |       5
    September|    1400   |     860   |     530
    October  |    1380   |     870   |     540
    November |    1420   |     880   |     550
    December |    1500   |     900   |     560

    Analyze this data. Identify anomalies, trends, and provide an assessment
    of which product lines need attention.
""")

CODE_REVIEW_FUNC = textwrap.dedent("""\
    def process_user_data(raw_data, db_conn):
        results = []
        for item in raw_data:
            user = db_conn.execute("SELECT * FROM users WHERE name = '%s'" % item['name'])
            if user:
                item['age'] = int(item.get('age', 0))
                item['score'] = eval(item.get('formula', '0'))
                results.append(item)
            else:
                try:
                    db_conn.execute("INSERT INTO users VALUES ('%s', %d)" % (item['name'], item['age']))
                except:
                    pass
        return results
""")

YAML_CONFIG_A = textwrap.dedent("""\
    server:
      host: 0.0.0.0
      port: 8080
      workers: 4
      timeout: 30
      ssl:
        enabled: false
        cert_path: /etc/ssl/cert.pem

    database:
      engine: postgresql
      host: localhost
      port: 5432
      name: myapp_prod
      pool_size: 10
      max_overflow: 20

    cache:
      backend: redis
      host: localhost
      port: 6379
      ttl: 3600

    logging:
      level: INFO
      format: json
      file: /var/log/myapp/app.log
""")

YAML_CONFIG_B = textwrap.dedent("""\
    server:
      host: 127.0.0.1
      port: 9090
      workers: 8
      timeout: 60
      ssl:
        enabled: true
        cert_path: /etc/letsencrypt/live/myapp.com/fullchain.pem

    database:
      engine: postgresql
      host: db.internal.myapp.com
      port: 5432
      name: myapp_prod
      pool_size: 25
      max_overflow: 50

    cache:
      backend: redis
      host: cache.internal.myapp.com
      port: 6379
      ttl: 7200
      password: ${REDIS_PASSWORD}

    logging:
      level: WARNING
      format: json
      file: /var/log/myapp/app.log
      rotation: daily
""")

DECISION_PROMPT = textwrap.dedent("""\
    We need to choose a reverse proxy for our self-hosted infrastructure.
    Requirements: Auto-SSL (Let's Encrypt), Web UI for management, Docker support,
    low resource usage, active community.

    Options:
    1. Traefik — Cloud-native, label-based, Prometheus metrics
    2. Caddy — Automatic HTTPS, Caddyfile syntax, plugin system
    3. Zoraxy — Lightweight, Web UI, Go-based, less well-known

    Create a structured decision matrix with ratings (1-5) per criterion
    and a clear recommendation with justification.
""")

ROOT_CAUSE_PROMPT = textwrap.dedent("""\
    Symptom: An LXC container (CT 104, SearXNG) reports "Permission denied"
    on every update attempt since the last maintenance run. The container
    was originally created using a community script.

    Known facts:
    - The container runs as unprivileged LXC
    - SearXNG is installed under /opt/searxng/
    - There is a user "searxng" and a user "root"
    - The venv is at /opt/searxng/venv/
    - `ls -la /opt/searxng/venv/` shows: owner=root, group=root
    - The community script runs updates as user "searxng"
    - 2 weeks ago, someone manually ran `pip install` as root

    Derive the root cause and describe the solution in at most 5 sentences.
""")


def create_large_module():
    """Generiert ein 481-Zeilen Python-Modul mit 10 Klassen + 8 kaputten Funktionen."""
    classes = [
        ("User", ["id: int", "name: str", "email: str", "age: int", "active: bool"]),
        ("Product", ["id: int", "title: str", "price: float", "stock: int", "category: str"]),
        ("Order", ["id: int", "user_id: int", "product_ids: list", "total: float", "status: str"]),
        ("Payment", ["id: int", "order_id: int", "amount: float", "method: str", "processed: bool"]),
        ("Review", ["id: int", "user_id: int", "product_id: int", "rating: int", "comment: str"]),
        ("Category", ["id: int", "name: str", "parent_id: Optional[int]", "active: bool", "sort_order: int"]),
        ("Inventory", ["id: int", "product_id: int", "warehouse: str", "quantity: int", "reserved: int"]),
        ("Shipment", ["id: int", "order_id: int", "carrier: str", "tracking: str", "status: str"]),
        ("Discount", ["id: int", "code: str", "percent: float", "valid_until: str", "used_count: int"]),
        ("AuditLog", ["id: int", "user_id: int", "action: str", "details: str", "timestamp: str"]),
    ]
    lines = [
        '"""Large module with user management, order processing, and reporting."""',
        "", "import json", "import logging",
        "from datetime import datetime, timedelta",
        "from typing import Optional, List, Dict, Any",
        "", "logger = logging.getLogger(__name__)", "",
    ]
    validation_rules = {
        "User": [("name", "str"), ("email", "str"), ("age", "non_neg")],
        "Product": [("title", "str"), ("price", "non_neg"), ("stock", "non_neg"), ("category", "str")],
        "Order": [("user_id", "non_neg"), ("total", "non_neg"), ("status", "str")],
        "Payment": [("order_id", "non_neg"), ("amount", "non_neg"), ("method", "str")],
        "Review": [("user_id", "non_neg"), ("product_id", "non_neg"), ("rating", "non_neg"), ("comment", "str")],
        "Category": [("name", "str"), ("sort_order", "non_neg")],
        "Inventory": [("product_id", "non_neg"), ("warehouse", "str"), ("quantity", "non_neg"), ("reserved", "non_neg")],
        "Shipment": [("order_id", "non_neg"), ("carrier", "str"), ("tracking", "str"), ("status", "str")],
        "Discount": [("code", "str"), ("percent", "non_neg"), ("valid_until", "str"), ("used_count", "non_neg")],
        "AuditLog": [("user_id", "non_neg"), ("action", "str"), ("details", "str"), ("timestamp", "str")],
    }
    for cls_name, fields in classes:
        field_names = [f.split(":")[0].strip() for f in fields]
        field_types = [f.split(":")[1].strip() for f in fields]
        lines.append(f"class {cls_name}:")
        desc = cls_name.lower()
        if desc == "auditlog":
            desc = "auditlog"
        lines.append(f'    """Represents a {desc} in the system."""')
        lines.append("")
        init_params = ", ".join(f"{n}: {t}" for n, t in zip(field_names, field_types))
        lines.append(f"    def __init__(self, {init_params}):")
        for n in field_names:
            lines.append(f"        self.{n} = {n}")
        lines.append("")
        lines.append("    def to_dict(self) -> dict:")
        lines.append("        return {")
        for n in field_names:
            lines.append(f'            "{n}": self.{n},')
        lines.append("        }")
        lines.append("")
        lines.append("    @classmethod")
        lines.append(f'    def from_dict(cls, data: dict) -> "{cls_name}":')
        args = ", ".join(f'data["{n}"]' for n in field_names)
        lines.append(f"        return cls({args})")
        lines.append("")
        lines.append("    def __repr__(self):")
        repr_fields = ", ".join(f"{n}={{self.{n}!r}}" for n in field_names[:3])
        lines.append(f'        return f"{cls_name}({repr_fields})"')
        lines.append("")
        lines.append("    def validate(self) -> List[str]:")
        lines.append("        errors = []")
        for field, rule in validation_rules.get(cls_name, []):
            if rule == "str":
                lines.append(f"        if not self.{field}:")
                lines.append(f'            errors.append("{field} is required")')
            elif rule == "non_neg":
                lines.append(f"        if self.{field} < 0:")
                lines.append(f'            errors.append("{field} must be non-negative")')
        lines.append("        return errors")
        lines.append("")
        lines.append("")

    broken_functions = [
        ("calculate_order_total", "Calculate the total price for an order including discounts.",
         "subtotal = sum(product.price for product in products)\n"
         "    if discount_code:\n        discount = subtotal * 0.1\n        subtotal -= discount\n"
         "    tax = subtotal * 0.19\n    shipping = 5.99 if subtotal < 50 else 0\n"
         "    return round(subtotal + tax + shipping, 2)"),
        ("process_payment", "Process a payment for an order.",
         "if not order:\n        raise ValueError('Order not found')\n"
         "    if order.status != 'pending':\n        raise ValueError('Order already processed')\n"
         "    payment = Payment(0, order.id, order.total, method, False)\n"
         "    payment.processed = True\n    order.status = 'paid'\n    return payment"),
        ("generate_sales_report", "Generate a sales report for a date range.",
         "report = {'start': start_date, 'end': end_date, 'orders': []}\n"
         "    total_revenue = 0\n    for order in orders:\n"
         "        if start_date <= order.timestamp <= end_date:\n"
         "            report['orders'].append(order.to_dict())\n"
         "            total_revenue += order.total\n"
         "    report['total_revenue'] = total_revenue\n"
         "    report['order_count'] = len(report['orders'])\n"
         "    report['average_order'] = total_revenue / max(len(report['orders']), 1)\n"
         "    return report"),
        ("check_inventory", "Check if all products in an order are in stock.",
         "out_of_stock = []\n    for product_id, quantity in items.items():\n"
         "        inv = inventory.get(product_id)\n        if not inv:\n"
         "            out_of_stock.append(product_id)\n"
         "        elif inv.quantity - inv.reserved < quantity:\n"
         "            out_of_stock.append(product_id)\n"
         "    return len(out_of_stock) == 0, out_of_stock"),
        ("send_notification", "Send a notification to a user (stub).",
         "log_entry = AuditLog(0, user.id, f'notification:{notification_type}',\n"
         "                    message, datetime.now().isoformat())\n"
         "    print(f'[NOTIFY] {user.email}: {message}')\n    return log_entry"),
        ("apply_discount", "Apply a discount code to an order.",
         "if not discount.code:\n        return 0\n"
         "    if discount.used_count >= 100:\n"
         "        raise ValueError('Discount code expired')\n"
         "    amount = order.total * (discount.percent / 100)\n"
         "    order.total -= amount\n    discount.used_count += 1\n    return amount"),
        ("export_data", "Export all data to JSON format.",
         "output = {\n        'users': [u.to_dict() for u in users],\n"
         "        'products': [p.to_dict() for p in products],\n"
         "        'orders': [o.to_dict() for o in orders],\n"
         "        'exported_at': datetime.now().isoformat(),\n    }\n"
         "    with open(filepath, 'w') as f:\n        json.dump(output, f, indent=2)\n"
         "    return len(output['users']) + len(output['products']) + len(output['orders'])"),
        ("import_data", "Import data from a JSON file.",
         "with open(filepath) as f:\n        data = json.load(f)\n"
         "    users = [User.from_dict(u) for u in data.get('users', [])]\n"
         "    products = [Product.from_dict(p) for p in data.get('products', [])]\n"
         "    orders = [Order.from_dict(o) for o in data.get('orders', [])]\n"
         "    return {'users': len(users), 'products': len(products), 'orders': len(orders)}"),
    ]
    for fname, doc, body in broken_functions:
        lines.append(f"    try:")
        lines.append(f"def {fname}(**kwargs):")
        lines.append(f'    """{doc}"""')
        for bline in body.split("\n"):
            lines.append(f"    {bline}")
        lines.append(f"    except Exception as e:")
        lines.append(f'        logger.error(f"Error in function {fname}: {{e}}", exc_info=True)')
        lines.append(f"        raise  # Re-raise the exception")
        lines.append("")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Server Management
# ---------------------------------------------------------------------------

def check_ram_available(config: dict):
    """Check if sufficient RAM is available for the model."""
    try:
        # Get total physical RAM and subtract only wired (non-reclaimable)
        # macOS reclaims inactive, purgeable, speculative pages on demand
        result = subprocess.run(["vm_stat"], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        page_size = 16384  # macOS Apple Silicon page size

        pages = {}
        for line in lines:
            for key in ("Pages free", "Pages inactive", "Pages purgeable",
                        "Pages speculative", "Pages wired down", "Pages active"):
                if key + ":" in line:
                    pages[key] = int(line.split(':')[1].strip().rstrip('.'))

        total_pages = 3145728  # 48GB / 16384
        wired = pages.get("Pages wired down", 0)
        active = pages.get("Pages active", 0)
        # Available = total - wired - active (everything else is reclaimable)
        available_gb = (total_pages - wired - active) * page_size / (1024**3)

        # Estimate model size
        gguf_path = os.path.expanduser(config["gguf_path"])
        model_size_gb = os.path.getsize(gguf_path) / (1024**3)

        # Estimate KV cache (conservative)
        ctx_size = config.get("ctx_size", 131072)
        kv_cache_gb = ctx_size * 0.5 / 1024  # 0.5 KB per token

        # Add draft model size if present
        draft_size_gb = 0
        draft = config.get("draft_model_path")
        if draft:
            draft_path = os.path.expanduser(draft)
            if os.path.exists(draft_path):
                draft_size_gb = os.path.getsize(draft_path) / (1024**3)

        # System reserve (macOS + VS Code + Claude Code)
        system_reserve_gb = 4

        total_estimated = model_size_gb + kv_cache_gb + draft_size_gb + system_reserve_gb

        if total_estimated > available_gb:
            print(f"\n⚠️  RAM INSUFFICIENT — aborting!")
            print(f"  Available: {available_gb:.1f}GB")
            print(f"  Estimated need: {total_estimated:.1f}GB")
            print(f"    - Model: {model_size_gb:.1f}GB")
            print(f"    - KV cache: {kv_cache_gb:.1f}GB")
            if draft_size_gb > 0:
                print(f"    - Draft model: {draft_size_gb:.1f}GB")
            print(f"    - System reserve: {system_reserve_gb:.1f}GB")
            print(f"  Tip: Reduce ctx_size or use --force to override.")
            if not os.environ.get("BENCHMARK_FORCE"):
                sys.exit(1)
        else:
            print(f"✓ RAM check OK: {total_estimated:.1f}GB estimated / {available_gb:.1f}GB available")
    except Exception as e:
        print(f"  Warning: RAM check failed ({e}), continuing anyway...")


def start_server(config: dict) -> subprocess.Popen:
    """Start llama-server with model config."""
    # Kill any stale llama-server processes
    try:
        result = subprocess.run(["pgrep", "-f", "llama-server.*--port.*1235"], capture_output=True, text=True)
        if result.stdout.strip():
            for pid in result.stdout.strip().split('\n'):
                print(f"  Killing stale llama-server PID {pid}")
                os.kill(int(pid), signal.SIGTERM)
            time.sleep(2)
    except Exception:
        pass

    gguf = os.path.expanduser(config["gguf_path"])
    if not os.path.exists(gguf):
        print(f"ERROR: GGUF not found: {gguf}")
        sys.exit(1)

    cmd = [
        "llama-server",
        "--model", gguf,
        "--host", SERVER_HOST,
        "--port", str(SERVER_PORT),
        "--ctx-size", str(config.get("ctx_size", 131072)),
        "--n-gpu-layers", str(config.get("gpu_layers", 99)),
        "--threads", str(config.get("threads", 10)),
    ]
    fa = config.get("flash_attn", "on")
    if fa:
        cmd += ["--flash-attn", str(fa)]

    if config.get("jinja"):
        cmd += ["--jinja"]

    if config.get("chat_template_kwargs"):
        cmd += ["--chat-template-kwargs", config["chat_template_kwargs"]]

    # Speculative decoding (draft model)
    draft = config.get("draft_model_path")
    if draft:
        draft_path = os.path.expanduser(draft)
        if os.path.exists(draft_path):
            cmd += ["--model-draft", draft_path]
            draft_max = config.get("draft_max", 8)
            cmd += ["--draft-max", str(draft_max)]
            if config.get("draft_gpu_layers"):
                cmd += ["-ngld", str(config["draft_gpu_layers"])]
            print(f"  Draft model: {draft_path} (draft-max={draft_max})")
        else:
            print(f"  WARNING: Draft model not found: {draft_path}, running without")

    log = open("/tmp/llm-benchmark-server.log", "w")
    proc = subprocess.Popen(cmd, stdout=log, stderr=log)
    print(f"  llama-server PID {proc.pid}, waiting for startup...")

    for i in range(60):
        time.sleep(2)
        try:
            r = urllib.request.urlopen(f"http://{SERVER_HOST}:{SERVER_PORT}/health", timeout=2)
            if r.status == 200:
                print(f"  Server ready after {(i+1)*2}s")
                return proc
        except Exception:
            pass
    print("ERROR: Server failed to start within 120s")
    proc.terminate()
    sys.exit(1)


def stop_server(proc: subprocess.Popen):
    """Stop llama-server."""
    proc.terminate()
    proc.wait(timeout=10)
    print("  llama-server stopped.")


# ---------------------------------------------------------------------------
# API Calls
# ---------------------------------------------------------------------------

def chat_completion(prompt: str, config: dict, system: str = "", timeout: int = 120) -> tuple[str, float]:
    """Direct /v1/chat/completions call. Returns (response_text, duration)."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    inf = config.get("inference", {})

    # Use explicit model_id from config, fallback to name, then "local"
    model_name = config.get("model_id", config.get("name", "local"))

    # Inject /no_think system prompt for thinking models (Qwen3.5-4B/9B etc.)
    if config.get("no_think") and not system:
        messages.insert(0, {"role": "system", "content": "/no_think"})

    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": inf.get("temperature", 0.7),
        "top_p": inf.get("top_p", 0.8),
        "max_tokens": inf.get("max_tokens", 4096),
    }

    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"http://{SERVER_HOST}:{SERVER_PORT}/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    r = urllib.request.urlopen(req, timeout=timeout)
    elapsed = time.time() - t0
    data = json.loads(r.read().decode())
    text = data["choices"][0]["message"]["content"]
    return text, elapsed


def run_smolagent(prompt: str, config: dict, max_steps: int = 8, timeout: int = 300) -> tuple[str, float]:
    """Run a smolagents CodeAgent task. Returns (result, duration)."""
    from smolagents import CodeAgent, LiteLLMModel

    inf = config.get("inference", {})
    model = LiteLLMModel(
        model_id=f"openai/{config.get('name', 'local')}",
        api_base=f"http://{SERVER_HOST}:{SERVER_PORT}/v1",
        api_key="not-needed",
        temperature=inf.get("temperature", 0.7),
        top_p=inf.get("top_p", 0.8),
    )
    agent = CodeAgent(
        tools=[],
        model=model,
        additional_authorized_imports=["*"],
        executor_kwargs={"additional_functions": {"open": open}},
        max_steps=max_steps,
        verbosity_level=0,
    )
    t0 = time.time()
    result = agent.run(prompt)
    elapsed = time.time() - t0
    return str(result), elapsed


# ---------------------------------------------------------------------------
# Test Definitions
# ---------------------------------------------------------------------------

def setup_fixtures():
    """Create/reset all test fixture files."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    (FIXTURES_DIR / "t1").mkdir(exist_ok=True)
    (FIXTURES_DIR / "t3").mkdir(exist_ok=True)
    (FIXTURES_DIR / "t4").mkdir(exist_ok=True)
    (FIXTURES_DIR / "t6").mkdir(exist_ok=True)

    # Reset files
    (FIXTURES_DIR / "t1" / "app.py").unlink(missing_ok=True)
    (FIXTURES_DIR / "t3" / "calculator.py").write_text(CALCULATOR_PY)
    (FIXTURES_DIR / "t4" / "app.py").write_text(FLASK_APP_PY)
    (FIXTURES_DIR / "t6" / "large_module.py").write_text(create_large_module())


# --- Category A: Code Tasks (smolagents) ---

def test_a1(config):
    """A1: File Write — fibonacci, is_prime, fizzbuzz"""
    target = FIXTURES_DIR / "t1" / "app.py"
    target.unlink(missing_ok=True)
    result, elapsed = run_smolagent(
        f"Create a Python file at {target} with three functions: "
        "fibonacci(n) returning nth fibonacci (0-indexed, fib(0)=0, fib(1)=1, fib(10)=55), "
        "is_prime(n) returning True/False, "
        "fizzbuzz(n) returning list of strings 1..n with Fizz/Buzz/FizzBuzz rules. "
        "Use open() to write the file. No tests, no main block.",
        config,
    )
    passed = target.exists()
    if passed:
        code = target.read_text()
        passed = "fibonacci" in code and "is_prime" in code and "fizzbuzz" in code
    return {"status": "PASS" if passed else "FAIL", "time": round(elapsed, 1)}


def test_a2(config):
    """A2: Bug Fix — 3 bugs in calculator.py"""
    f = FIXTURES_DIR / "t3" / "calculator.py"
    f.write_text(CALCULATOR_PY)
    result, elapsed = run_smolagent(
        f"Read {f} using open(). It has 3 bugs: "
        "1) multiply uses + instead of *, "
        "2) divide has no zero division check, "
        "3) average is missing return statement. "
        "Fix all 3 bugs and write the fixed file back using open().",
        config,
    )
    code = f.read_text()
    passed = "a * b" in code and "return" in code.split("average")[1] if "average" in code else False
    return {"status": "PASS" if passed else "FAIL", "time": round(elapsed, 1)}


def test_a3(config):
    """A3: Error Handling — Flask CRUD API"""
    f = FIXTURES_DIR / "t4" / "app.py"
    f.write_text(FLASK_APP_PY)
    result, elapsed = run_smolagent(
        f"Read {f} using open(). It's a Flask CRUD API with no error handling. "
        "Add error handling: GET/PUT/DELETE by id should return 404 JSON if user not found, "
        "POST/PUT should return 400 JSON if name or email missing. "
        "Write the fixed file back using open(). Do NOT import flask, just edit the file as text.",
        config,
    )
    code = f.read_text()
    passed = "404" in code and "400" in code
    return {"status": "PASS" if passed else "FAIL", "time": round(elapsed, 1)}


def test_a4(config):
    """A4: Large File Read — list all class names"""
    f = FIXTURES_DIR / "t6" / "large_module.py"
    result, elapsed = run_smolagent(
        f"Read {f} using open() and return a Python list of ALL class names defined in it.",
        config,
    )
    expected = ["User", "Product", "Order", "Payment", "Review", "Category",
                "Inventory", "Shipment", "Discount", "AuditLog"]
    found = sum(1 for c in expected if c in str(result))
    return {"status": "PASS" if found >= 9 else "FAIL", "time": round(elapsed, 1)}


def test_a5(config):
    """A5: Large File Edit — fix 8 broken functions"""
    f = FIXTURES_DIR / "t6" / "large_module.py"
    f.write_text(create_large_module())
    result, elapsed = run_smolagent(
        f"Read {f} using open(). "
        "The standalone functions after the class definitions have broken syntax: "
        "try/except wraps the def statement instead of being inside the function body, "
        "and functions use **kwargs but reference undefined variable names. "
        "Fix ALL standalone functions so they have: "
        "1) proper named parameters instead of **kwargs, "
        "2) try/except INSIDE the function body. "
        "Do NOT modify any class definitions. Write the result back using open().",
        config, max_steps=10, timeout=600,
    )
    code = f.read_text()
    try:
        compile(code, str(f), "exec")
        passed = True
    except SyntaxError:
        passed = False
    return {"status": "PASS" if passed else "FAIL", "time": round(elapsed, 1)}


# --- Category B: Text Analysis (direct API) ---

def test_b1(config):
    """B1: Text Summary"""
    resp, elapsed = chat_completion(
        f"Summarize the following text in exactly 3 sentences:\n\n{SUMMARY_TEXT}",
        config,
    )
    sentences = [s.strip() for s in resp.replace("...", ".").split(".") if s.strip()]
    has_key = any(w in resp.lower() for w in ["proxmox", "container", "maintenance", "update"])
    passed = 2 <= len(sentences) <= 5 and has_key
    return {"status": "PASS" if passed else "FAIL", "time": round(elapsed, 1), "response": resp[:500]}


def test_b2(config):
    """B2: Log Analysis"""
    resp, elapsed = chat_completion(
        f"Analyze this Proxmox maintenance log and create a structured report "
        f"with: 1) Summary, 2) Errors with severity, 3) Recommended actions.\n\n{PVE_LOG}",
        config,
    )
    has_ct104 = "104" in resp
    has_searxng = "searxng" in resp.lower() or "permission" in resp.lower()
    has_structure = any(w in resp.lower() for w in ["summary", "error", "action", "recommendation", "finding"])
    passed = has_ct104 and has_searxng and has_structure
    return {"status": "PASS" if passed else "FAIL", "time": round(elapsed, 1), "response": resp[:500]}


def test_b3(config):
    """B3: Statistics with Anomaly Detection"""
    resp, elapsed = chat_completion(STATS_DATA, config)
    has_b_anomaly = any(w in resp for w in ["3200", "June", "anomal", "spike", "outlier", "unusual"])
    has_c_anomaly = any(w in resp for w in ["August", "5 ", "drop", "anomal", "crash", "plummet", "outlier"])
    passed = has_b_anomaly and has_c_anomaly
    return {"status": "PASS" if passed else "FAIL", "time": round(elapsed, 1), "response": resp[:500]}


def test_b4(config):
    """B4: Code Review"""
    resp, elapsed = chat_completion(
        f"Review this Python function. Identify ALL security issues and bugs:\n\n{CODE_REVIEW_FUNC}",
        config,
    )
    issues = {
        "sql_injection": any(w in resp.lower() for w in ["sql injection", "sql-injection", "% item", "string format"]),
        "eval": any(w in resp.lower() for w in ["eval", "code execution", "arbitrary", "dangerous"]),
        "bare_except": any(w in resp.lower() for w in ["bare except", "except:", "pass", "swallow", "silently"]),
    }
    found = sum(1 for v in issues.values() if v)
    passed = found >= 2
    return {"status": "PASS" if passed else "FAIL", "time": round(elapsed, 1),
            "issues_found": {k: v for k, v in issues.items()}, "response": resp[:500]}


# --- Category C: Reasoning (direct API) ---

def test_c1(config):
    """C1: Config Diff"""
    resp, elapsed = chat_completion(
        f"Compare these two YAML configurations and explain ALL differences:\n\n"
        f"=== Config A ===\n{YAML_CONFIG_A}\n=== Config B ===\n{YAML_CONFIG_B}",
        config,
    )
    diffs = {
        "host": "127.0.0.1" in resp or "host" in resp.lower(),
        "port": "9090" in resp,
        "workers": "8" in resp,
        "ssl": "ssl" in resp.lower() or "letsencrypt" in resp.lower(),
        "db_host": "db.internal" in resp or "database" in resp.lower(),
        "pool": "25" in resp or "pool" in resp.lower(),
        "cache_pw": "password" in resp.lower() or "REDIS" in resp,
        "log_level": "WARNING" in resp or "logging" in resp.lower(),
    }
    found = sum(1 for v in diffs.values() if v)
    passed = found >= 5
    return {"status": "PASS" if passed else "FAIL", "time": round(elapsed, 1),
            "diffs_found": found, "response": resp[:500]}


def test_c2(config):
    """C2: Decision Matrix"""
    resp, elapsed = chat_completion(DECISION_PROMPT, config)
    has_matrix = any(w in resp.lower() for w in ["matrix", "rating", "criterion", "score", "|", "criteria"])
    has_all_options = all(w in resp for w in ["Traefik", "Caddy", "Zoraxy"])
    has_recommendation = any(w in resp.lower() for w in ["recommend", "conclusion", "verdict", "best", "winner", "choice"])
    passed = has_matrix and has_all_options and has_recommendation
    return {"status": "PASS" if passed else "FAIL", "time": round(elapsed, 1), "response": resp[:500]}


def test_c3(config):
    """C3: Root Cause Analysis"""
    resp, elapsed = chat_completion(ROOT_CAUSE_PROMPT, config)
    has_ownership = any(w in resp.lower() for w in ["ownership", "chown", "permission", "owner"])
    has_root_cause = any(w in resp.lower() for w in ["root", "pip install", "manual"])
    has_fix = any(w in resp.lower() for w in ["chown", "fix", "solution", "restore", "change owner"])
    passed = has_ownership and has_root_cause and has_fix
    return {"status": "PASS" if passed else "FAIL", "time": round(elapsed, 1), "response": resp[:500]}


# ---------------------------------------------------------------------------
# Test Registry
# ---------------------------------------------------------------------------

# --- Category D: Hard (direct API) — tests that separate 30B from 70B+ ---

SUBTLE_BUG_CODE = textwrap.dedent("""\
    import threading

    class Counter:
        def __init__(self):
            self.value = 0

        def increment(self):
            current = self.value
            self.value = current + 1

        def get(self):
            return self.value

    def run_concurrent_increments(n_threads=100, increments_per_thread=1000):
        counter = Counter()
        threads = []
        for _ in range(n_threads):
            t = threading.Thread(target=lambda: [counter.increment() for _ in range(increments_per_thread)])
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        return counter.get()  # Expected: 100000
""")

INSTRUCTION_FOLLOWING_PROMPT = textwrap.dedent("""\
    List exactly 5 advantages of containerization over virtual machines.
    Rules:
    - Each advantage must be ONE sentence, maximum 15 words
    - Number them 1-5
    - Do NOT use the word "lightweight"
    - End your response with the exact phrase "End of list."
""")

MULTI_STEP_REASONING = textwrap.dedent("""\
    A Proxmox cluster has 3 nodes (A, B, C) with the following state:
    - Node A: 64GB RAM, running VM-1 (16GB), VM-2 (32GB), CT-1 (4GB)
    - Node B: 128GB RAM, running VM-3 (64GB), CT-2 (8GB)
    - Node C: 64GB RAM, running CT-3 (2GB), CT-4 (2GB)

    Rules:
    - Live migration requires the target node to have enough FREE RAM
    - VMs can only migrate to nodes with >= 50% free RAM AFTER migration
    - CTs can migrate to any node with enough free RAM

    Question: Can VM-2 (32GB) be live-migrated from Node A to Node C?
    Show your step-by-step calculation and give a clear YES or NO answer.
""")

LONG_CONTEXT_PROMPT_PREFIX = textwrap.dedent("""\
    Below is a server configuration document. Read it carefully and answer
    the question at the end.

""")

def _build_long_context_input():
    """Build a ~3000 token input with a hidden detail in the middle."""
    sections = []
    services = [
        ("nginx", "80/443", "reverse proxy", "apt install nginx"),
        ("postgresql", "5432", "database", "apt install postgresql-15"),
        ("redis", "6379", "cache", "apt install redis-server"),
        ("grafana", "3000", "monitoring", "apt install grafana"),
        ("prometheus", "9090", "metrics", "apt install prometheus"),
        ("elasticsearch", "9200", "search", "apt install elasticsearch"),
        ("rabbitmq", "5672", "message queue", "apt install rabbitmq-server"),
        ("minio", "9000", "object storage", "docker run minio/minio"),
    ]
    for name, port, purpose, install in services:
        sections.append(
            f"## {name.title()}\n"
            f"Port: {port}\nPurpose: {purpose}\nInstall: {install}\n"
            f"Status: active\nBackup: daily at 02:00 UTC\n"
            f"Log rotation: 7 days\nMax connections: 1000\n"
            f"TLS: enabled via Caddy reverse proxy\n"
        )
    # Hidden detail in section 5 (prometheus)
    sections[4] = sections[4].replace(
        "Max connections: 1000",
        "Max connections: 1000\nKNOWN ISSUE: retention policy set to 90 days instead of required 365 days"
    )
    body = "\n".join(sections)
    question = "\nQuestion: Which service has a known issue and what is it about?"
    return LONG_CONTEXT_PROMPT_PREFIX + body + question


QUALITY_REVIEW_CODE = textwrap.dedent("""\
    def process_orders(orders, inventory, discounts):
        results = []
        for order in orders:
            total = 0
            for item in order['items']:
                product = inventory.get(item['product_id'])
                if product:
                    price = product['price'] * item['quantity']
                    for d in discounts:
                        if d['product_id'] == item['product_id']:
                            if d['type'] == 'percent':
                                price = price * (1 - d['value'] / 100)
                            elif d['type'] == 'fixed':
                                price = price - d['value']
                    total += price
                    product['stock'] -= item['quantity']
            order['total'] = total
            order['status'] = 'processed'
            results.append(order)
        return results
""")


def test_d1(config):
    """D1: Subtle Bug Detection (Race Condition)"""
    resp, elapsed = chat_completion(
        f"Review this code. Identify the bug that will cause incorrect results "
        f"and explain WHY it happens. Be specific about the mechanism.\n\n{SUBTLE_BUG_CODE}",
        config,
    )
    has_race = any(w in resp.lower() for w in ["race condition", "race", "thread safe", "thread-safe", "concurrent"])
    has_mechanism = any(w in resp.lower() for w in ["read", "write", "interleav", "atomic", "lock", "mutex"])
    has_toctou = any(w in resp.lower() for w in ["time of check", "toctou", "between", "current = self.value"])
    passed = has_race and (has_mechanism or has_toctou)
    return {"status": "PASS" if passed else "FAIL", "time": round(elapsed, 1), "response": resp[:500]}


def test_d2(config):
    """D2: Strict Instruction Following"""
    resp, elapsed = chat_completion(INSTRUCTION_FOLLOWING_PROMPT, config)
    lines = [l.strip() for l in resp.strip().split("\n") if l.strip()]

    # Check numbered items (1-5)
    numbered = [l for l in lines if l and l[0].isdigit()]
    has_five = len(numbered) == 5

    # Check no "lightweight"
    no_lightweight = "lightweight" not in resp.lower()

    # Check ends with exact phrase
    ends_correctly = resp.strip().endswith("End of list.")

    # Check word count per item (max 15 words per numbered line)
    words_ok = all(len(l.split()) <= 20 for l in numbered)  # generous: 20 with number prefix

    score = sum([has_five, no_lightweight, ends_correctly, words_ok])
    passed = score >= 3  # At least 3 of 4 constraints
    return {"status": "PASS" if passed else "FAIL", "time": round(elapsed, 1),
            "checks": {"five_items": has_five, "no_lightweight": no_lightweight,
                        "ends_correctly": ends_correctly, "words_ok": words_ok},
            "response": resp[:500]}


def test_d3(config):
    """D3: Multi-Step Calculation"""
    resp, elapsed = chat_completion(MULTI_STEP_REASONING, config)

    # Node C: 64GB total, 4GB used (CT-3 + CT-4) = 60GB free
    # After VM-2 (32GB) migration: 64 - 4 - 32 = 28GB free = 43.75% < 50%
    # Answer should be NO
    has_calculation = any(w in resp for w in ["28", "60", "43", "44", "56"])
    has_no = resp.strip().upper().count("NO") >= 1
    has_reasoning = any(w in resp.lower() for w in ["50%", "free ram", "after migration", "not enough"])
    passed = has_no and (has_calculation or has_reasoning)
    return {"status": "PASS" if passed else "FAIL", "time": round(elapsed, 1), "response": resp[:500]}


def test_d4(config):
    """D4: Long Context Retrieval"""
    prompt = _build_long_context_input()
    resp, elapsed = chat_completion(prompt, config)
    has_prometheus = "prometheus" in resp.lower()
    has_retention = any(w in resp.lower() for w in ["retention", "90 day", "365 day", "90 days", "365 days"])
    passed = has_prometheus and has_retention
    return {"status": "PASS" if passed else "FAIL", "time": round(elapsed, 1), "response": resp[:500]}


def test_d5(config):
    """D5: Nuanced Code Quality (beyond obvious bugs)"""
    resp, elapsed = chat_completion(
        f"Review this function for ALL issues — bugs, design problems, and edge cases. "
        f"Rank them by severity.\n\n{QUALITY_REVIEW_CODE}",
        config,
    )
    issues = {
        "negative_price": any(w in resp.lower() for w in ["negative", "below zero", "negative price", "< 0"]),
        "stock_mutation": any(w in resp.lower() for w in ["mutate", "side effect", "modif", "stock", "in-place"]),
        "missing_stock_check": any(w in resp.lower() for w in ["stock check", "out of stock", "insufficient", "enough stock", "available"]),
        "discount_stacking": any(w in resp.lower() for w in ["stack", "multiple discount", "compound", "both"]),
        "no_error_handling": any(w in resp.lower() for w in ["error", "exception", "keyerror", "missing key", "none"]),
    }
    found = sum(1 for v in issues.values() if v)
    passed = found >= 3  # Must find at least 3 of 5 issues
    return {"status": "PASS" if passed else "FAIL", "time": round(elapsed, 1),
            "issues_found": {k: v for k, v in issues.items()}, "found": found,
            "response": resp[:500]}


# --- Category E: Deep Research (long input, causal chains, domain knowledge) ---

CORRELATED_LOG = textwrap.dedent("""\
    2026-03-14 02:00:01 [INFO]  === PVE Maintenance Run Started ===
    2026-03-14 02:00:03 [INFO]  Phase 1: Host health check
    2026-03-14 02:00:03 [OK]    CPU: 8%, RAM: 52%, Disk: 71%
    2026-03-14 02:00:05 [INFO]  Phase 2: Container updates
    2026-03-14 02:00:05 [INFO]  CT 100 (uptime-kuma): Starting update...
    2026-03-14 02:00:08 [OK]    CT 100: apt update completed, 0 packages upgraded
    2026-03-14 02:00:09 [INFO]  CT 103 (forgejo): Starting update...
    2026-03-14 02:00:12 [OK]    CT 103: custom handler executed, app v9.2.1 -> v9.3.0
    2026-03-14 02:00:13 [INFO]  CT 103 (forgejo): Post-update health check...
    2026-03-14 02:00:15 [WARN]  CT 103: HTTP health check returned 502 (attempt 1/5)
    2026-03-14 02:00:25 [WARN]  CT 103: HTTP health check returned 502 (attempt 2/5)
    2026-03-14 02:00:35 [OK]    CT 103: HTTP health check returned 200
    2026-03-14 02:00:36 [INFO]  CT 116 (pve-maintenance): Starting update...
    2026-03-14 02:00:38 [OK]    CT 116: apk update completed, 2 packages upgraded
    2026-03-14 02:00:39 [INFO]  CT 117 (listmonk): Starting update...
    2026-03-14 02:00:42 [OK]    CT 117: apt update completed, 1 package upgraded (listmonk 4.1.0 -> 4.2.0)
    2026-03-14 02:00:43 [INFO]  CT 117 (listmonk): Post-update health check...
    2026-03-14 02:00:45 [OK]    CT 117: HTTP health check returned 200
    2026-03-14 02:00:46 [INFO]  CT 126 (grafana): Starting update...
    2026-03-14 02:00:55 [OK]    CT 126: apt update completed, 1 package upgraded (grafana 12.4.1 -> 12.5.0)
    2026-03-14 02:00:56 [INFO]  CT 126 (grafana): Post-update health check...
    2026-03-14 02:00:58 [ERROR] CT 126: HTTP health check FAILED - connection refused on port 3000
    2026-03-14 02:01:08 [ERROR] CT 126: HTTP health check FAILED - connection refused on port 3000 (attempt 2/5)
    2026-03-14 02:01:18 [ERROR] CT 126: HTTP health check FAILED - connection refused on port 3000 (attempt 3/5)
    2026-03-14 02:01:28 [ERROR] CT 126: HTTP health check FAILED - connection refused on port 3000 (attempt 4/5)
    2026-03-14 02:01:38 [ERROR] CT 126: HTTP health check FAILED - connection refused on port 3000 (attempt 5/5)
    2026-03-14 02:01:39 [CRIT]  CT 126: Service did not recover after update. Rollback initiated.
    2026-03-14 02:01:42 [INFO]  CT 126: Rolling back grafana 12.5.0 -> 12.4.1...
    2026-03-14 02:01:55 [OK]    CT 126: Rollback completed, service healthy on port 3000
    2026-03-14 02:01:56 [INFO]  Phase 3: Network connectivity check
    2026-03-14 02:01:57 [INFO]  Checking inter-container connectivity...
    2026-03-14 02:01:58 [OK]    CT 100 -> CT 103 (forgejo API): 200 OK (45ms)
    2026-03-14 02:01:59 [WARN]  CT 100 -> CT 126 (grafana API): 200 OK (2350ms) — response time degraded
    2026-03-14 02:02:00 [OK]    CT 100 -> CT 117 (listmonk API): 200 OK (12ms)
    2026-03-14 02:02:01 [INFO]  Phase 4: Disk usage check
    2026-03-14 02:02:02 [WARN]  CT 103: Disk usage 87% (/var/lib/forgejo) — threshold 85%
    2026-03-14 02:02:03 [OK]    CT 126: Disk usage 45%
    2026-03-14 02:02:04 [OK]    CT 117: Disk usage 23%
    2026-03-14 02:02:05 [INFO]  Phase 5: Summary
    2026-03-14 02:02:05 [OK]    Updated: 5/5 containers
    2026-03-14 02:02:05 [WARN]  Issues: CT 126 grafana update failed (rolled back), CT 103 disk near full
    2026-03-14 02:02:06 [ERROR] Action required: CT 126 grafana 12.5.0 incompatible, CT 103 disk cleanup needed
    2026-03-14 02:02:06 [INFO]  === Run completed in 125s ===
""")

DMARC_LOG = textwrap.dedent("""\
    The following is a DMARC aggregate report (simplified) for the domain wulffit.de
    covering 2026-03-13 to 2026-03-14. Analyze it for security concerns.

    Source IP       | Count | SPF    | DKIM   | DMARC  | From Header      | Envelope From
    ----------------|-------|--------|--------|--------|------------------|------------------
    85.215.148.20   |    45 | pass   | pass   | pass   | wulffit.de       | wulffit.de
    85.215.148.20   |     3 | pass   | fail   | fail   | wulffit.de       | wulffit.de
    192.168.1.50    |    12 | fail   | none   | fail   | wulffit.de       | wulffit.de
    209.85.220.41   |     8 | pass   | pass   | pass   | wulffit.de       | wulffit.de
    185.70.40.111   |     2 | fail   | fail   | fail   | wulffit.de       | wulffit.de
    85.215.148.20   |    15 | pass   | pass   | pass   | news.wulffit.de  | bounce.wulffit.de
    45.133.1.72     |    31 | fail   | fail   | fail   | wulffit.de       | different-domain.ru
    103.224.182.250 |     1 | fail   | fail   | fail   | wulffit.de       | wulffit.de
    209.85.220.41   |     5 | pass   | pass   | pass   | wulffit.de       | calendar-server.google.com

    Additional context:
    - 85.215.148.20 is the legitimate mail server (mail.wulffit.de)
    - 209.85.220.41 is Google's mail server (used for calendar invites)
    - SPF record: "v=spf1 ip4:85.215.148.20 include:_spf.google.com ~all"
    - DKIM selector: default._domainkey.wulffit.de
    - DMARC policy: v=DMARC1; p=none; rua=mailto:dmarc@wulffit.de

    Questions:
    1. Which entries indicate a genuine security threat vs. misconfiguration?
    2. What is the 192.168.1.50 entry and why is it problematic?
    3. What specific action items would you recommend?
    4. Should the DMARC policy be changed, and if so, to what?
""")


def test_e1(config):
    """E1: Correlated Log Analysis — find causal chains across phases."""
    resp, elapsed = chat_completion(
        "Analyze this maintenance log. Don't just list errors — explain the CAUSAL RELATIONSHIPS "
        "between events and identify what needs immediate attention vs. what can wait.\n\n"
        + CORRELATED_LOG,
        config,
    )
    checks = {
        # Must identify grafana as critical (service down, rollback)
        "grafana_critical": any(w in resp.lower() for w in ["critical", "immediate", "grafana"]),
        # Must connect grafana update failure with degraded response time (2350ms)
        "causal_chain": any(w in resp.lower() for w in ["2350", "response time", "degraded", "slow"]),
        # Must note forgejo disk is APPROACHING full (87% vs 85% threshold)
        "forgejo_disk": any(w in resp.lower() for w in ["87%", "85%", "disk", "forgejo"]),
        # Must note forgejo 502 during startup is NORMAL (transient, recovered)
        "forgejo_502_benign": any(w in resp.lower() for w in ["transient", "startup", "recover", "normal", "expected"]),
        # Must distinguish urgent (grafana) from non-urgent (forgejo disk)
        "prioritization": any(w in resp.lower() for w in ["priorit", "immediate", "can wait", "urgent", "first"]),
        # Must recommend investigating grafana 12.5.0 compatibility
        "grafana_investigate": any(w in resp.lower() for w in ["12.5", "compatibility", "changelog", "breaking", "investigate"]),
    }
    score = sum(1 for v in checks.values() if v)
    passed = score >= 4  # Must get at least 4 of 6
    return {"status": "PASS" if passed else "FAIL", "time": round(elapsed, 1),
            "score": f"{score}/6", "checks": checks, "response": resp[:800]}


def test_e2(config):
    """E2: DMARC Log Analysis — real-world email security assessment."""
    resp, elapsed = chat_completion(DMARC_LOG, config)
    checks = {
        # Must identify 45.133.1.72 / different-domain.ru as spoofing/phishing
        "spoofing_detected": any(w in resp.lower() for w in ["spoof", "phish", "forge", "impersonat", "malicious"]),
        # Must identify 192.168.1.50 as internal/RFC1918 — should not send externally
        "rfc1918": any(w in resp.lower() for w in ["private", "internal", "192.168", "rfc1918", "local", "misconfigur"]),
        # Must note the 3 DKIM failures from legitimate server (key rotation issue?)
        "dkim_failure_legit": any(w in resp.lower() for w in ["dkim fail", "3 ", "key rotation", "signing", "legitimate"]),
        # Must recommend upgrading DMARC policy from p=none to p=quarantine or p=reject
        "policy_upgrade": any(w in resp.lower() for w in ["quarantine", "reject", "p=quarantine", "p=reject", "stricter"]),
        # Must note Google calendar entries are legitimate (SPF+DKIM pass)
        "google_legit": any(w in resp.lower() for w in ["google", "calendar", "legitimate", "expected"]),
        # Must identify 103.224.182.250 as suspicious (single attempt, all fail)
        "single_probe": any(w in resp.lower() for w in ["103.224", "single", "probe", "suspicious", "attempt"]),
        # Must recommend fixing the internal relay (192.168.1.50)
        "fix_internal": any(w in resp.lower() for w in ["relay", "smarthost", "route", "configure", "spf"]),
    }
    score = sum(1 for v in checks.values() if v)
    passed = score >= 4  # Must get at least 4 of 7
    return {"status": "PASS" if passed else "FAIL", "time": round(elapsed, 1),
            "score": f"{score}/7", "checks": checks, "response": resp[:800]}


ALL_TESTS = {
    "code": {
        "A1_file_write": test_a1,
        "A2_bug_fix": test_a2,
        "A3_error_handling": test_a3,
        "A4_large_read": test_a4,
        "A5_large_edit": test_a5,
    },
    "text": {
        "B1_summary": test_b1,
        "B2_log_analysis": test_b2,
        "B3_statistics": test_b3,
        "B4_code_review": test_b4,
    },
    "reasoning": {
        "C1_config_diff": test_c1,
        "C2_decision_matrix": test_c2,
        "C3_root_cause": test_c3,
    },
    "hard": {
        "D1_subtle_bug": test_d1,
        "D2_instruction_following": test_d2,
        "D3_multi_step_calc": test_d3,
        "D4_long_context": test_d4,
        "D5_nuanced_review": test_d5,
    },
    "deep": {
        "E1_correlated_log": test_e1,
        "E2_dmarc_analysis": test_e2,
    },
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_tests(config: dict, categories: list[str], timeout: int, test_filter: list[str] = None) -> dict:
    """Run selected test categories and return results."""
    setup_fixtures()
    results = {"model": config.get("display_name", config.get("name", "unknown")), "timestamp": datetime.now().isoformat(), "tests": {}}

    for cat in categories:
        tests = ALL_TESTS.get(cat, {})
        for name, fn in tests.items():
            # Apply test filter if specified
            if test_filter:
                # Match test names like "A1" matches "A1_file_write"
                if not any(name.startswith(f) for f in test_filter):
                    continue

            print(f"\n{'='*60}")
            print(f"  {name}")
            print(f"{'='*60}")
            try:
                result = fn(config)
                results["tests"][name] = result
                print(f"  → {result['status']} in {result['time']}s")
            except Exception as e:
                results["tests"][name] = {"status": f"ERROR: {e}", "time": 0}
                print(f"  → ERROR: {e}")

    # Summary with quality scoring
    tests = results["tests"]
    total = len(tests)
    passed = sum(1 for t in tests.values() if t.get("status") == "PASS")
    total_time = sum(t.get("time", 0) for t in tests.values())

    # Quality score: count sub-checks from D and E tests (score field like "4/6")
    quality_points = 0
    quality_max = 0
    for name, t in tests.items():
        if "score" in t and "/" in str(t["score"]):
            pts, mx = t["score"].split("/")
            quality_points += int(pts)
            quality_max += int(mx)
        elif "issues_found" in t:
            found = sum(1 for v in t["issues_found"].values() if v)
            quality_points += found
            quality_max += len(t["issues_found"])
        elif "checks" in t and isinstance(t["checks"], dict):
            found = sum(1 for v in t["checks"].values() if v)
            quality_points += found
            quality_max += len(t["checks"])

    results["summary"] = {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": f"{passed}/{total} ({100*passed//total if total else 0}%)",
        "total_time": round(total_time, 1),
    }
    if quality_max > 0:
        results["summary"]["quality_score"] = f"{quality_points}/{quality_max}"
    return results


def save_results(results: dict, name: str):
    """Save results to JSON."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y%m%d")
    path = RESULTS_DIR / f"{name}_{date}.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {path}")
    return path


def compare_results():
    """Compare all result files in results/ directory."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(RESULTS_DIR.glob("*.json"))
    if not files:
        print("No results found in results/")
        return

    all_results = []
    for f in files:
        with open(f) as fh:
            all_results.append(json.load(fh))

    # Collect all test names
    all_tests = set()
    for r in all_results:
        all_tests.update(r.get("tests", {}).keys())
    all_tests = sorted(all_tests)

    # Header
    models = [r.get("model", "?") for r in all_results]
    header = f"| Test | {' | '.join(models)} |"
    sep = f"|------|{'|'.join(['------'] * len(models))}|"

    lines = [
        f"# LLM Benchmark Vergleich",
        f"",
        f"**Generiert:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        header,
        sep,
    ]

    for test in all_tests:
        cells = []
        for r in all_results:
            t = r.get("tests", {}).get(test, {})
            status = t.get("status", "—")
            time_s = t.get("time", 0)
            cell = f"**{status}** {time_s}s" if status in ("PASS", "FAIL") else status
            cells.append(cell)
        lines.append(f"| {test} | {' | '.join(cells)} |")

    # Summary row
    cells = []
    for r in all_results:
        s = r.get("summary", {})
        cells.append(f"**{s.get('pass_rate', '?')}** ({s.get('total_time', '?')}s)")
    lines.append(f"| **GESAMT** | {' | '.join(cells)} |")

    report = "\n".join(lines)
    print(report)

    date = datetime.now().strftime("%Y%m%d")
    path = RESULTS_DIR / f"comparison_{date}.md"
    with open(path, "w") as f:
        f.write(report)
    print(f"\nSaved to {path}")


def main():
    parser = argparse.ArgumentParser(description="LLM Benchmark Suite fuer lokale Knecht-Modelle")
    parser.add_argument("--config", help="Path to model config JSON")
    parser.add_argument("--categories", default="all",
                        help="Test categories: all, code, text, reasoning (comma-separated)")
    parser.add_argument("--tests", help="Comma-separated test names to run (e.g., A1,A2,B1)")
    parser.add_argument("--timeout", type=int, default=300, help="Max seconds per test")
    parser.add_argument("--compare", action="store_true", help="Compare all results")
    parser.add_argument("--haiku-baseline", action="store_true", help="Run Haiku baseline (needs ANTHROPIC_API_KEY)")
    parser.add_argument("--external-server", action="store_true",
                        help="Skip server start/stop (use already running server on port 1235)")
    args = parser.parse_args()

    if args.compare:
        compare_results()
        return

    if args.haiku_baseline:
        print("Haiku baseline: Use Claude Code Task-Tool with --model haiku.")
        print("This is documented in the playbook but not automated in this script.")
        print("Haiku results should be manually added to results/haiku_baseline.json")
        return

    if not args.config:
        parser.print_help()
        return

    # Load config
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = CONFIGS_DIR / config_path
    with open(config_path) as f:
        config = json.load(f)

    print(f"LLM Benchmark: {config.get('name', 'unknown')}")
    print(f"GGUF: {config.get('gguf_path')}")
    print(f"Context: {config.get('ctx_size', 'default')}")

    # Parse categories
    if args.categories == "all":
        categories = ["code", "text", "reasoning", "hard", "deep"]
    else:
        categories = [c.strip() for c in args.categories.split(",")]

    # Parse test filter
    test_filter = None
    if args.tests:
        test_filter = [t.strip() for t in args.tests.split(",")]
        print(f"Test filter: {test_filter}")

    # Check RAM availability (skip for external server)
    if not args.external_server:
        check_ram_available(config)

    # Start server (or use external)
    proc = None
    if not args.external_server:
        proc = start_server(config)
    else:
        print(f"Using external server on {SERVER_HOST}:{SERVER_PORT}")
    try:
        results = run_tests(config, categories, args.timeout, test_filter)
        save_results(results, config.get("display_name", config.get("name", "unknown")))

        print(f"\n{'='*60}")
        summary = results['summary']
        print(f"SUMMARY: {summary['pass_rate']} in {summary['total_time']}s")
        if "quality_score" in summary:
            print(f"QUALITY: {summary['quality_score']}")
        print(f"{'='*60}")
    finally:
        if proc:
            stop_server(proc)


if __name__ == "__main__":
    main()
