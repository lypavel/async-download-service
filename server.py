import asyncio
from aiohttp import web
import aiofiles
from pathlib import Path


async def archive(request):
    response = web.StreamResponse()
    response.headers['Content-Disposition'] = 'attachment; \
        filename="archive.zip"'
    await response.prepare(request)

    archive_hash = request.match_info.get('archive_hash')

    process = await asyncio.create_subprocess_exec(
        'zip',
        '-r',
        '-',
        '.',
        cwd=Path(f'test_photos/{archive_hash}'),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    while True:
        stdout = await process.stdout.read(n=512000)
        if process.stdout.at_eof():
            return response
        await response.write(stdout)


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app, host='0.0.0.0', port=8000)
