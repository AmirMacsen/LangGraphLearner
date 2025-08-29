from mcp.server import FastMCP

mcp = FastMCP("math_map_server")

@mcp.tool()
async def add(a: int, b: int)-> int:
    """
    计算两个整数的和
    :param a:
    :param b:
    :return:
    """
    return a + b

if __name__ == '__main__':
    mcp.run(transport="stdio")