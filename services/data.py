import os
from dotenv import load_dotenv
from typing import List, Dict, Any
import uuid

load_dotenv()
pinecone_api_key = os.getenv("PINECONE_API_KEY")

# Global model variable
_model = None
_use_mock = False

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
        # Import Pinecone client
        from pinecone import Pinecone
        
        # Initialize Pinecone
        pc = Pinecone(api_key=pinecone_api_key)
        index = pc.Index("subtitles")
        
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
        # Import Pinecone client
        from pinecone import Pinecone
        
        # Initialize Pinecone
        pc = Pinecone(api_key=pinecone_api_key)
        index = pc.Index("subtitles")
        
        # Tạo embedding cho query
        query_embedding = create_embedding(query)
        
        # Chuẩn bị filter
        filter_dict = {}
        if video_id:
            filter_dict["video_id"] = video_id
        
        # Tìm kiếm
        results = index.query(
            vector=query_embedding,
            top_k=k,
            include_metadata=True,
            filter=filter_dict if filter_dict else None
        )
        
        # Format kết quả
        formatted_results = []
        for match in results.matches:
            formatted_results.append({
                "text": match.metadata.get("text", ""),
                "metadata": match.metadata,
                "similarity_score": float(match.score)
            })
        
        return formatted_results
        
    except Exception as e:
        return []

def get_stats() -> Dict[str, Any]:
    """
    Lấy thống kê về vector store
    """
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=pinecone_api_key)
        index = pc.Index("subtitles")
        stats = index.describe_index_stats()
        return {
            "total_vectors": stats.total_vector_count,
            "dimension": stats.dimension,
            "index_fullness": stats.index_fullness
        }
    except Exception as e:
        return {}

def wipe_database() -> Dict[str, Any]:
    """
    Xóa tất cả records trong index
    """
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=pinecone_api_key)
        index = pc.Index("subtitles")
        
        # Lấy thống kê trước khi xóa
        stats_before = index.describe_index_stats()
        total_before = stats_before.total_vector_count
        
        # Xóa tất cả vectors
        index.delete(delete_all=True)
        
        # Lấy thống kê sau khi xóa
        stats_after = index.describe_index_stats()
        total_after = stats_after.total_vector_count
        
        return {
            "success": True,
            "deleted_vectors": total_before,
            "remaining_vectors": total_after,
            "message": f"Successfully deleted {total_before} vectors from database"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to wipe database"
        }

