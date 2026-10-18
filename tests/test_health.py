import urllib.error
import urllib.request

from pokemon_bot.trigger.health import start_health_server


def _get(port: int, path: str) -> int:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
            return int(r.status)
    except urllib.error.HTTPError as e:
        return e.code


def test_health_ready_e_404() -> None:
    ready = {"v": False}
    server = start_health_server(0, lambda: ready["v"], host="127.0.0.1")
    port = server.server_address[1]
    try:
        assert _get(port, "/health") == 200
        assert _get(port, "/ready") == 503
        ready["v"] = True
        assert _get(port, "/ready") == 200
        assert _get(port, "/outra") == 404
    finally:
        server.shutdown()
        server.server_close()
