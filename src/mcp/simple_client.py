"""Simple MCP client for testing."""

import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# E2 again! Windows cp1252 console can't print emoji . In M3 this fix
# lived in base_agent.py, but this file doesn't import it — so we have to
# force UTF-8 here as well.
sys.stdout.reconfigure(encoding="utf-8")


async def test_hello_server():
    """Test hello world MCP server."""
    print("🔌 Connecting to hello-world server...")

    # Server parameters
    server_params = StdioServerParameters(
        command=sys.executable,  # venv python (the one with mcp installed)
        args=["-u", "src/mcp/hello_server.py"],  # -u = show output immediately
    )

    # Connect to server
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print("\n📋 Available tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")

            # Call greet tool
            print("\n🔧 Calling 'greet' tool...")
            result = await session.call_tool("greet", {"name": "Alice"})
            print(f"   Result: {result.content[0].text}")

            # Call add tool
            print("\n🔧 Calling 'add' tool...")
            result = await session.call_tool("add", {"a": 5, "b": 3})
            print(f"   Result: {result.content[0].text}")

            print("\n✅ MCP communication working!")


if __name__ == "__main__":
    asyncio.run(test_hello_server())
