import time
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

# --- CONFIGURATION ---
# Replace with your actual Pinecone API Key
PINECONE_API_KEY = "pcsk_3Pw3jS_Jpncjsr2P74WsvjvjiwGXY4mxQ2FNGuJF1zSp2EKG6ZWvn6HSHaau2tF9ww4UFX" 
INDEX_NAME = "league-caster-index"

def main():
    # 1. Initialize the Embedding Model (Runs locally)
    # 'all-MiniLM-L6-v2' is a small, fast model perfect for laptops.
    # It turns text into a vector of 384 numbers.
    print("[1/4] Loading Embedding Model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # 2. Define "Mock" Historical Data
    # In the real project, you would load this from the 5,000 match dataset.
    # We store the "State" (what is happening) and the "Insight" (what the caster should say).
    historical_matches = [
        {
            "id": "match_001",
            "state_description": "Blue team leads by 2000 gold at 15 minutes with 2 dragons stacked. They have a siege composition with Caitlyn and Lux.",
            "insight": "With a significant gold lead and double dragons, Blue Team is likely to rotate mid to crack the Tier 1 tower and open up the map."
        },
        {
            "id": "match_002",
            "state_description": "Red team is behind by 5000 gold at 25 minutes. They have lost all outer turrets and are turtle-ing in base.",
            "insight": "Red Team is in survival mode. They must clear waves and look for a desperate pick on a mispositioned carry to turn this around."
        },
        {
            "id": "match_003",
            "state_description": "Even gold at 30 minutes. Both teams are dancing around the Baron pit. Vision control is split.",
            "insight": "It's a complete stalemate. The next team to clear a ward and force a face-check will likely win the game. This is a classic Baron flip scenario."
        }
    ]

    # 3. Initialize Pinecone
    print("[2/4] Connecting to Pinecone...")
    pc = Pinecone(api_key=PINECONE_API_KEY)

    # Check if index exists, if not, create it
    existing_indexes = [index.name for index in pc.list_indexes()]
    
    if INDEX_NAME not in existing_indexes:
        print(f"Creating index '{INDEX_NAME}'...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=384, # Must match the model (all-MiniLM-L6-v2 outputs 384 dims)
            metric="cosine", # Cosine similarity is best for text comparison
            spec=ServerlessSpec(cloud="aws", region="us-east-1") # Free tier settings
        )
        time.sleep(10) # Wait for index to initialize
    
    index = pc.Index(INDEX_NAME)

    # 4. Vectorize and Upsert
    print("[3/4] Vectorizing and Uploading data...")
    vectors_to_upload = []

    for match in historical_matches:
        # Convert the "state description" into numbers (Vector)
        vector = model.encode(match["state_description"]).tolist()
        
        # Prepare the payload
        vectors_to_upload.append({
            "id": match["id"],
            "values": vector,
            "metadata": {
                "text": match["state_description"],
                "insight": match["insight"]
            }
        })

    # Upload in batch
    index.upsert(vectors=vectors_to_upload)
    
    print(f"[4/4] Success! Uploaded {len(vectors_to_upload)} matches to Knowledge Base.")
    print("Your 'Long-Term Memory' is ready.")

if __name__ == "__main__":
    main()