# -*- coding: utf-8 -*-
"""Fermeture de session."""
from http.server import BaseHTTPRequestHandler
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _lib as L


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        L.json_rep(self, {"ok": True}, entetes={
            "Set-Cookie": "atelier=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0"})
