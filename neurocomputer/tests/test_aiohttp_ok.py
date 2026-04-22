from aiohttp import web

async def create_app():
    app = web.Application()
    @app.get("/health")
    async def health(request):
        return web.Response(text="OK")
    return app

async def test_health_returns_ok(aiohttp_client):
    app = await create_app()
    client = await aiohttp_client(app)
    resp = await client.get("/health")
    assert resp.status == 200
    text = await resp.text()
    assert text == "OK"
