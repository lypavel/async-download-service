import asyncio
import logging
from pathlib import Path

import aiofiles
from aiohttp import web
from environs import Env

logging.basicConfig(
    level=logging.INFO,
    format='[%(name)s][%(levelname)s]: %(message)s'
)

logger = logging.getLogger(Path(__file__).name)


async def archive(request):
    archive_hash = request.match_info['archive_hash']
    photos_path = Path(env.str('PHOTOS_DIRECTORY'), archive_hash)
    if not photos_path.exists():
        raise web.HTTPNotFound(text='Архив не существует или был удалён.')

    response = web.StreamResponse()
    response.headers['Content-Disposition'] = 'attachment; \
        filename="archive.zip"'
    await response.prepare(request)

    process = await asyncio.create_subprocess_exec(
        'zip',
        '-r',
        '-',
        '.',
        cwd=photos_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    response_delay = env.int('RESPONSE_DELAY', 0)
    chunk_size = env.int('CHUNK_SIZE', 500 * 1024)
    try:
        while not process.stdout.at_eof():
            await asyncio.sleep(response_delay)

            stdout = await process.stdout.read(n=chunk_size)
            logger.info('Sending archive chunk...')

            await response.write(stdout)

        return response
    except asyncio.CancelledError:
        logger.error('Download was interrupted')
        raise
    except SystemExit as system_exit:
        logger.exception(system_exit)
    except Exception as exception:
        logger.exception(exception)
    finally:
        if process.returncode is None:
            process.kill()
            await process.communicate()


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    env = Env()
    env.read_env()

    if not env.bool('LOGGING', True):
        logger.disabled = True

    host = env.str('SERVICE_HOST', '127.0.0.1')
    port = env.int('SERVICE_PORT', 8080)

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app, host=host, port=port)
