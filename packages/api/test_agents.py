
from item_processing.agents import augment_item_description


if __name__ == "__main__":
    import asyncio

    async def main():
        # Example usage
        item_description = "The image must contain a well-maintained Toyota Landcruiser engine from 2001, with clear visibility of all components. The timing belt or timing chain should be visible."
        augmented_description = await augment_item_description(item_description,agent_ids=["49c4b21b-7244-4f73-9327-ccb535d5d12b"])
        print('\n\nAugmented description\n\n',augmented_description)
        
        item_description = "The image must contain a 2007 petrol Pajero engine, with its cylinder heads clearly visible."
        augmented_description = await augment_item_description(item_description,agent_ids=["49c4b21b-7244-4f73-9327-ccb535d5d12b"])
        print('\n\nAugmented description\n\n',augmented_description)

    asyncio.run(main())
