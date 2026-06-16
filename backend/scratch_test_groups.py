import asyncio
from app.services.tally_connector import TallyConnector

async def main():
    connector = TallyConnector(host="host.docker.internal", port=9000)
    try:
        print("Fetching groups XML...")
        xml_data = await connector.fetch_groups()
        
        with open("raw_groups.xml", "w", encoding="utf-8") as f:
            f.write(xml_data)
        print("Raw XML saved to raw_groups.xml")
        
        # Print around line 81
        lines = xml_data.splitlines()
        print("\n--- XML around line 81 ---")
        start = max(0, 81 - 5)
        end = min(len(lines), 81 + 5)
        for idx in range(start, end):
            print(f"Line {idx+1}: {lines[idx]}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
