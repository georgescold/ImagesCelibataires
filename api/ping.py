# -*- coding: utf-8 -*-
"""Sonde de diagnostic : aucun import du projet."""
import json, os, sys
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        info = {
            "ok": True,
            "python": sys.version.split()[0],
            "cwd": os.getcwd(),
            "dossier_fonction": os.path.dirname(os.path.abspath(__file__)),
            "voisins": sorted(os.listdir(os.path.dirname(os.path.abspath(__file__))))[:20],
            "sys_path_contient_le_dossier":
                os.path.dirname(os.path.abspath(__file__)) in sys.path,
            "pillow": False,
            "env_presentes": sorted(k for k in os.environ
                                    if k.startswith(("SUPABASE", "FAL", "ATELIER", "SESSION"))),
        }
        try:
            import PIL  # noqa
            info["pillow"] = True
        except Exception as e:
            info["pillow"] = f"absent : {e}"
        corps = json.dumps(info, ensure_ascii=False, indent=1).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)
