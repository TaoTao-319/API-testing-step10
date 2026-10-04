"""Local booking API. Python standard library only.

Run: python server.py
Base URL: http://127.0.0.1:8000
Data and tokens are kept in memory and reset when the server restarts.
"""

import json
import secrets
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit


BOOKINGS = {}
TOKENS = set()
NEXT_ID = 1


def booking_error(data):
    if not isinstance(data, dict):
        return "Body must be a JSON object"
    fields = {
        "firstname": str, "lastname": str,
        "totalprice": int, "depositpaid": bool,
        "bookingdates": dict,
    }
    for name, expected_type in fields.items():
        if name not in data:
            return "Missing field: " + name
        if type(data[name]) is not expected_type:
            return "Incorrect type: " + name
    for name in ("checkin", "checkout"):
        if not isinstance(data["bookingdates"].get(name), str):
            return "Missing or invalid bookingdates." + name
    if "additionalneeds" in data and not isinstance(data["additionalneeds"], str):
        return "Incorrect type: additionalneeds"
    return None


class BookingAPI(BaseHTTPRequestHandler):
    def reply(self, status, data=None):
        body = b"" if data is None else json.dumps(data).encode("utf-8")
        self.send_response(status)
        if data is not None:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 1_000_000:
                raise ValueError("Invalid body length")
            data = json.loads(self.rfile.read(length))
            return data, True
        except (ValueError, UnicodeDecodeError):
            self.reply(400, {"error": "Invalid JSON body"})
            return None, False

    def authorized(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
            token = cookie.get("token")
            valid = token is not None and token.value in TOKENS
        except Exception:
            valid = False
        if not valid:
            self.reply(403, {"error": "A valid token cookie is required"})
        return valid

    def booking_id(self, path):
        parts = path.strip("/").split("/")
        if len(parts) == 2 and parts[0] == "booking" and parts[1].isdigit():
            return int(parts[1])
        return None

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/ping":
            self.reply(200, {"status": "ok"})
        elif url.path == "/booking":
            filters = parse_qs(url.query)
            matches = [
                {"bookingid": booking_id}
                for booking_id, booking in BOOKINGS.items()
                if all(booking.get(key) == filters[key][0]
                       for key in ("firstname", "lastname") if key in filters)
            ]
            self.reply(200, matches)
        else:
            booking_id = self.booking_id(url.path)
            if booking_id in BOOKINGS:
                self.reply(200, BOOKINGS[booking_id])
            else:
                self.reply(404, {"error": "Booking or endpoint not found"})

    def do_POST(self):
        global NEXT_ID
        path = urlsplit(self.path).path
        if path not in ("/auth", "/booking"):
            self.reply(404, {"error": "Endpoint not found"})
            return
        data, valid = self.read_json()
        if not valid:
            return
        if path == "/auth":
            if isinstance(data, dict) and data.get("username") == "admin" and data.get("password") == "password123":
                token = secrets.token_hex(16)
                TOKENS.add(token)
                self.reply(200, {"token": token})
            else:
                self.reply(401, {"error": "Bad credentials"})
            return
        error = booking_error(data)
        if error:
            self.reply(400, {"error": error})
            return
        booking_id = NEXT_ID
        NEXT_ID += 1
        BOOKINGS[booking_id] = data
        self.reply(200, {"bookingid": booking_id, "booking": data})

    def do_PUT(self):
        booking_id = self.booking_id(urlsplit(self.path).path)
        if booking_id is None:
            self.reply(404, {"error": "Endpoint not found"})
            return
        if not self.authorized():
            return
        if booking_id not in BOOKINGS:
            self.reply(404, {"error": "Booking not found"})
            return
        data, valid = self.read_json()
        if not valid:
            return
        error = booking_error(data)
        if error:
            self.reply(400, {"error": error})
            return
        BOOKINGS[booking_id] = data
        self.reply(200, data)

    def do_DELETE(self):
        booking_id = self.booking_id(urlsplit(self.path).path)
        if booking_id is None:
            self.reply(404, {"error": "Endpoint not found"})
            return
        if not self.authorized():
            return
        if booking_id not in BOOKINGS:
            self.reply(404, {"error": "Booking not found"})
            return
        del BOOKINGS[booking_id]
        self.reply(201, {"message": "Booking deleted"})


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8000), BookingAPI)
    print("Local booking API: http://127.0.0.1:8000", flush=True)
    print("Demo credentials: admin / password123", flush=True)
    print("Keep this terminal open. Press Ctrl+C to stop. Data resets on restart.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
