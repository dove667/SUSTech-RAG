"""TCP 代理 :8080 → :3000"""
import asyncio
import sys


async def handle_client(r, w):
    try:
        rr, ww = await asyncio.open_connection("127.0.0.1", 3000)

        async def pipe(src, dst):
            try:
                while True:
                    data = await src.read(65536)
                    if not data:
                        break
                    dst.write(data)
                    await dst.drain()
            except Exception:
                pass
            finally:
                try:
                    dst.close()
                except Exception:
                    pass

        await asyncio.gather(pipe(r, ww), pipe(rr, w))
    except Exception:
        pass


async def main():
    server = await asyncio.start_server(handle_client, "0.0.0.0", 8080)
    print("[proxy] :8080 → :3000 ready", flush=True)
    await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
