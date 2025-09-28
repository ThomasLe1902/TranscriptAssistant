import os
from dotenv import load_dotenv
from typing import List, Dict, Any
import uuid

# Import Pinecone at module level
try:
    from pinecone import Pinecone
    import pinecone as pc_old
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    print("⚠️ Pinecone not available")

load_dotenv()
pinecone_api_key = os.getenv("PINECONE_API_KEY")
pinecone_environment = os.getenv("PINECONE_ENVIRONMENT")
pinecone_index_name = os.getenv("PINECONE_INDEX_NAME", "transcript-assistant")

# Global model variable
_model = None
_use_mock = False

def get_pinecone_index():
    """
    Lấy Pinecone index với cách tương thích
    """
    if not PINECONE_AVAILABLE:
        raise Exception("Pinecone not available")
        
    try:
        if pinecone_environment:
            # Cách cũ
            pc_old.init(api_key=pinecone_api_key, environment=pinecone_environment)
            return pc_old.Index(pinecone_index_name)
        else:
            # Cách mới
            pc = Pinecone(api_key=pinecone_api_key)
            return pc.Index(pinecone_index_name)
            
    except Exception as e:
        print(f"❌ Error getting Pinecone index: {e}")
        raise e

def get_model():
    """Lazy loading của sentence transformer model"""
    global _model, _use_mock
    if _model is None and not _use_mock:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ Using sentence-transformers model")
        except ImportError:
            print("⚠️ sentence-transformers not found, using mock embeddings")
            _use_mock = True
    return _model

def create_mock_embedding(text: str) -> List[float]:
    """Tạo mock embedding 384 dimensions (tương thích với all-MiniLM-L6-v2)"""
    import random
    text_hash = hash(text) % (2**32)
    random.seed(text_hash)
    embedding = [random.random() for _ in range(384)]
    random.seed()
    return embedding

def create_embedding(text: str) -> List[float]:
    """
    Tạo embedding sử dụng all-MiniLM-L6-v2 model hoặc mock
    """
    if _use_mock:
        return create_mock_embedding(text)
    
    model = get_model()
    if model is None:
        return create_mock_embedding(text)
    
    embedding = model.encode(text)
    return embedding.tolist()

def insert_data(texts: List[str], metadatas: List[Dict[str, Any]]):
    """
    Vector hóa và lưu texts vào Pinecone
    """
    try:
        # Initialize Pinecone với cách tương thích
        index = get_pinecone_index()
        
        vectors_to_upsert = []
        for i, (text, metadata) in enumerate(zip(texts, metadatas)):
            embedding = create_embedding(text)
            vector_id = str(uuid.uuid4())
            vector = {
                "id": vector_id,
                "values": embedding,
                "metadata": {
                    **metadata,
                    "text": text  # Thêm text vào metadata để query
                }
            }
            vectors_to_upsert.append(vector)
        
        batch_size = 100
        for i in range(0, len(vectors_to_upsert), batch_size):
            batch = vectors_to_upsert[i:i + batch_size]
            index.upsert(vectors=batch)
        
        return index
        
    except Exception as e:
        if "No active indexes found" in str(e) or "not found" in str(e).lower():
            raise Exception("Pinecone index 'subtitles' not found. Please create it first.")
        else:
            raise e

def query_data(query: str, k: int = 5, video_id: str = None) -> List[Dict[str, Any]]:
    """
    Tìm kiếm semantic trong Pinecone
    
    Args:
        query: Câu hỏi tìm kiếm
        k: Số lượng kết quả trả về
        video_id: ID video để filter (optional)
    """
    try:
        # Initialize Pinecone với cách tương thích
        index = get_pinecone_index()
        
        # Tạo embedding cho query
        query_embedding = create_embedding(query)
        
        # Chuẩn bị filter với syntax đúng cho Pinecone
        filter_dict = None
        if video_id:
            filter_dict = {"video_id": {"$eq": video_id}}
            print(f"🔍 Querying with video_id filter: {video_id}")
        else:
            print("🔍 Querying without video_id filter")
        
        # Tìm kiếm
        results = index.query(
            vector=query_embedding,
            top_k=k,
            include_metadata=True,
            filter=filter_dict
        )
        
        # Format kết quả và debug
        formatted_results = []
        for match in results.matches:
            match_video_id = match.metadata.get("video_id", "unknown")
            print(f"📝 Found match with video_id: {match_video_id}, score: {match.score:.3f}")
            formatted_results.append({
                "text": match.metadata.get("text", ""),
                "metadata": match.metadata,
                "similarity_score": float(match.score)
            })
        
        print(f"✅ Total results found: {len(formatted_results)}")
        return formatted_results
        
    except Exception as e:
        print(f"❌ Error in query_data: {e}")
        return []