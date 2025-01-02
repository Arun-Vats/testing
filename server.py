from aiohttp import web

async def health_check(request):
    return web.Response(text="OK", status=200)

async def start_server():
    app = web.Application()
    app.router.add_get('/health', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
