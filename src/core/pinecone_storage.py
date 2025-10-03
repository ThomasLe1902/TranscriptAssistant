"""
Pinecone storage service để lưu trữ subtitles và summaries
"""

import os
import sys
import json
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

load_dotenv()

class PineconeStorage:
    """Pinecone storage service cho subtitles và summaries"""
    
    def __init__(self):
        """Initialize Pinecone client"""
        self.api_key = os.getenv("PINECONE_API_KEY")
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY environment variable not set")
        
        self.pc = Pinecone(api_key=self.api_key)
        
        # Index name and namespaces
        self.index_name = "transcripts"
        self.subtitles_namespace = "subtitles"
        self.summaries_namespace = "summaries"
        
        # Initialize indexes
        self._setup_indexes()
    
    def _setup_indexes(self):
        """Setup Pinecone index with namespaces"""
        try:
            # Check if transcripts index exists
            if self.index_name not in self.pc.list_indexes().names():
                print(f"Creating transcripts index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=768,  # Gemini embedding-001 dimension
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
            else:
                print(f"Transcripts index {self.index_name} already exists")
                
        except Exception as e:
            print(f"❌ Error setting up index: {e}")
            raise
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using Gemini embedding-001"""
        import google.generativeai as genai
        
        # Configure Gemini
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        
        # Get embedding
        result = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_document"
        )
        
        return result['embedding']
    
    def store_subtitle(self, subtitle_data: Dict[str, Any]) -> bool:
        """Store subtitle data to Pinecone"""
        try:
            index = self.pc.Index(self.index_name, namespace=self.subtitles_namespace)
            
            # Generate embedding
            text = subtitle_data.get('text', '')
            embedding = self._get_embedding(text)
            # embedding = [0.1] * 768  # Simple dummy vector
            
            # Prepare metadata
            metadata = {
                'type': 'subtitle',
                'video_id': subtitle_data.get('video_id', ''),
                'lesson_title': subtitle_data.get('lesson_title', ''),
                'timestamp_id': subtitle_data.get('timestamp_id', ''),
                'start_time': subtitle_data.get('start_time', ''),
                'end_time': subtitle_data.get('end_time', ''),
                'text': text
            }
            
            # Store to Pinecone
            index.upsert(
                vectors=[{
                    'id': f"subtitle_{subtitle_data.get('video_id', '')}_{subtitle_data.get('timestamp_id', '')}",
                    'values': embedding,
                    'metadata': metadata
                }]
            )
            
            return True
            
        except Exception as e:
            print(f"❌ Error storing subtitle: {e}")
            return False
    
    def store_subtitles(self, subtitles_data: List[Dict[str, Any]]) -> int:
        """Store multiple subtitle data to Pinecone"""
        success_count = 0
        for subtitle in subtitles_data:
            if self.store_subtitle(subtitle):
                success_count += 1
        return success_count
    
    def store_summary(self, summary_data: Dict[str, Any]) -> bool:
        """Store summary data to Pinecone"""
        try:
            index = self.pc.Index(self.index_name, namespace=self.summaries_namespace)
            
            # Generate embedding
            text = summary_data.get('text', '')
            embedding = self._get_embedding(text)
            # embedding = [0.1] * 768  # Simple dummy vector
            
            # Prepare metadata
            metadata = {
                'type': 'summary',
                'video_id': summary_data.get('video_id', ''),
                'lesson_title': summary_data.get('lesson_title', ''),
                'text': text
            }
            
            # Store to Pinecone
            index.upsert(
                vectors=[{
                    'id': f"summary_{summary_data.get('video_id', '')}",
                    'values': embedding,
                    'metadata': metadata
                }]
            )
            
            return True
            
        except Exception as e:
            print(f"❌ Error storing summary: {e}")
            return False
    
    def store_summaries(self, summaries_data: List[Dict[str, Any]]) -> int:
        """Store multiple summary data to Pinecone"""
        success_count = 0
        for summary in summaries_data:
            if self.store_summary(summary):
                success_count += 1
        return success_count
    
    def search_subtitles(self, query: str, video_id: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search subtitles by query"""
        try:
            # Generate query embedding
            query_embedding = self._get_embedding(query)
            
            # Search in subtitles namespace
            index = self.pc.Index(self.index_name, namespace=self.subtitles_namespace)
            
            # Build filter
            search_filter = {"type": "subtitle"}
            if video_id:
                search_filter["video_id"] = video_id
            
            # Search
            results = index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=search_filter
            )
            
            # Format results
            formatted_results = []
            for match in results.matches:
                formatted_results.append({
                    'id': match.id,
                    'score': match.score,
                    'metadata': match.metadata
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"❌ Error searching subtitles: {e}")
            return []
    
    def search_summaries(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search summaries by query"""
        try:
            # Generate query embedding
            query_embedding = self._get_embedding(query)
            
            # Search in summaries index
            index = self.pc.Index(self.index_name, namespace=self.summaries_namespace)
            
            # Search
            results = index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter={"type": "summary"}
            )
            
            # Format results
            formatted_results = []
            for match in results.matches:
                formatted_results.append({
                    'id': match.id,
                    'score': match.score,
                    'metadata': match.metadata
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"❌ Error searching summaries: {e}")
            return []
    
    def get_summary_by_video_id(self, video_id: str) -> Dict[str, Any]:
        """Get summary by video_id"""
        try:
            index = self.pc.Index(self.index_name, namespace=self.summaries_namespace)
            
            # Search by video_id
            results = index.query(
                vector=[0.0] * 768,  # Dummy vector for metadata search
                top_k=1,
                include_metadata=True,
                filter={"type": "summary", "video_id": video_id}
            )
            
            if results.matches:
                match = results.matches[0]
                return {
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting summary by video_id: {e}")
            return None
    
    def get_subtitles_by_timestamp_range(self, video_id: str, start_time: str = None, end_time: str = None, top_k: int = 10) -> List[Dict[str, Any]]:
        """Get subtitles by timestamp range"""
        try:
            index = self.pc.Index(self.index_name, namespace=self.subtitles_namespace)
            
            # Search by video_id
            search_filter = {"type": "subtitle", "video_id": video_id}
            
            results = index.query(
                vector=[0.0] * 768,  # Dummy vector for metadata search
                top_k=top_k,
                include_metadata=True,
                filter=search_filter
            )
            
            # Filter by timestamp if provided
            filtered_results = []
            for match in results.matches:
                metadata = match.metadata
                
                # If timestamp filters are provided, check them
                if start_time and metadata.get('start_time'):
                    if metadata['start_time'] < start_time:
                        continue
                
                if end_time and metadata.get('end_time'):
                    if metadata['end_time'] > end_time:
                        continue
                
                filtered_results.append({
                    "id": match.id,
                    "score": match.score,
                    "metadata": metadata
                })
            
            return filtered_results
            
        except Exception as e:
            print(f"❌ Error getting subtitles by timestamp range: {e}")
            return []
    
    def get_all_videos(self) -> List[Dict[str, Any]]:
        """Get all available videos"""
        try:
            # Get from summaries index
            summary_index = self.pc.Index(self.index_name, namespace=self.summaries_namespace)
            summary_results = summary_index.query(
                vector=[0.0] * 768,
                top_k=100,  # Get up to 100 videos
                include_metadata=True,
                filter={"type": "summary"}
            )
            
            videos = []
            for match in summary_results.matches:
                metadata = match.metadata
                videos.append({
                    "video_id": metadata.get('video_id'),
                    "lesson_title": metadata.get('lesson_title'),
                    "summary_preview": metadata.get('text', '')[:200] + "..." if len(metadata.get('text', '')) > 200 else metadata.get('text', '')
                })
            
            return videos
            
        except Exception as e:
            print(f"❌ Error getting all videos: {e}")
            return []
    
    def get_subtitle_by_timestamp_id(self, timestamp_id: str, video_id: str = None) -> Dict[str, Any]:
        """Get subtitle by timestamp_id"""
        try:
            index = self.pc.Index(self.index_name, namespace=self.subtitles_namespace)
            
            # Search by timestamp_id
            search_filter = {"type": "subtitle"}
            if video_id:
                search_filter["video_id"] = video_id
            
            # Get all subtitles and filter by timestamp_id
            results = index.query(
                vector=[0.0] * 768,  # Dummy vector for metadata search
                top_k=100,  # Get more results to filter
                include_metadata=True,
                filter=search_filter
            )
            
            # Filter by exact timestamp_id match
            for match in results.matches:
                metadata = match.metadata
                stored_timestamp_id = metadata.get('timestamp_id')
                # Convert both to float for comparison
                try:
                    if float(stored_timestamp_id) == float(timestamp_id):
                        return {
                            "id": match.id,
                            "score": match.score,
                            "metadata": metadata
                        }
                except (ValueError, TypeError):
                    # If conversion fails, try string comparison
                    if str(stored_timestamp_id) == str(timestamp_id):
                        return {
                            "id": match.id,
                            "score": match.score,
                            "metadata": metadata
                        }
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting subtitle by timestamp_id: {e}")
            return None
    
    def search_subtitles_by_timestamp_id(self, timestamp_id: str, video_id: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search subtitles by timestamp_id (partial match)"""
        try:
            index = self.pc.Index(self.index_name, namespace=self.subtitles_namespace)
            
            # Search by timestamp_id
            search_filter = {"type": "subtitle"}
            if video_id:
                search_filter["video_id"] = video_id
            
            results = index.query(
                vector=[0.0] * 768,  # Dummy vector for metadata search
                top_k=top_k,
                include_metadata=True,
                filter=search_filter
            )
            
            # Filter by timestamp_id (partial match)
            filtered_results = []
            for match in results.matches:
                metadata = match.metadata
                stored_timestamp_id = metadata.get('timestamp_id')
                # Convert both to string for comparison
                try:
                    stored_str = str(int(float(stored_timestamp_id))) if stored_timestamp_id is not None else ""
                    search_str = str(int(float(timestamp_id))) if timestamp_id else ""
                    if search_str in stored_str:
                        filtered_results.append({
                            "id": match.id,
                            "score": match.score,
                            "metadata": metadata
                        })
                except (ValueError, TypeError):
                    # If conversion fails, try string comparison
                    stored_str = str(stored_timestamp_id) if stored_timestamp_id is not None else ""
                    if timestamp_id.lower() in stored_str.lower():
                        filtered_results.append({
                            "id": match.id,
                            "score": match.score,
                            "metadata": metadata
                        })
            
            return filtered_results
            
        except Exception as e:
            print(f"❌ Error searching subtitles by timestamp_id: {e}")
            return []
    
    def rerank_results(self, query: str, results: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """Rerank results based on keyword relevance"""
        try:
            if not results:
                return results
            
            # Simple keyword-based reranking
            query_lower = query.lower()
            query_words = set(query_lower.split())
            
            def calculate_relevance_score(result):
                metadata = result.get('metadata', {})
                text = metadata.get('text', '').lower()
                
                # Calculate keyword matches
                text_words = set(text.split())
                keyword_matches = len(query_words.intersection(text_words))
                
                # Calculate word frequency
                word_frequency = sum(text.count(word) for word in query_words)
                
                # Combine with original score
                original_score = result.get('score', 0)
                relevance_score = keyword_matches * 0.3 + word_frequency * 0.1 + original_score * 0.6
                
                return relevance_score
            
            # Sort by relevance score
            reranked_results = sorted(results, key=calculate_relevance_score, reverse=True)
            
            return reranked_results[:top_k]
            
        except Exception as e:
            print(f"❌ Error reranking results: {e}")
            return results[:top_k]
    
    def get_adjacent_timestamps(self, timestamp_id: str, video_id: str = None, count: int = 2) -> List[Dict[str, Any]]:
        """Get adjacent timestamps (-1, +1)"""
        try:
            target_video_id = video_id
            current_timestamp = float(timestamp_id)
            
            # Get all subtitles for the video
            search_filter = {"type": "subtitle"}
            if target_video_id:
                search_filter["video_id"] = target_video_id
            
            index = self.pc.Index(self.index_name, namespace=self.subtitles_namespace)
            results = index.query(
                vector=[0.0] * 768,
                top_k=100,  # Get more results to find adjacent ones
                include_metadata=True,
                filter=search_filter
            )
            
            # Filter and sort by timestamp_id
            subtitles = []
            for match in results.matches:
                metadata = match.metadata
                stored_timestamp = metadata.get('timestamp_id')
                if stored_timestamp is not None:
                    try:
                        stored_timestamp_float = float(stored_timestamp)
                        subtitles.append({
                            'id': match.id,
                            'score': match.score,
                            'metadata': metadata,
                            'timestamp_float': stored_timestamp_float
                        })
                    except (ValueError, TypeError):
                        continue
            
            # Sort by timestamp
            subtitles.sort(key=lambda x: x['timestamp_float'])
            
            # Find current timestamp position
            current_index = None
            for i, subtitle in enumerate(subtitles):
                if abs(subtitle['timestamp_float'] - current_timestamp) < 0.1:  # Allow small difference
                    current_index = i
                    break
            
            if current_index is None:
                return []
            
            # Get adjacent timestamps (-1, +1)
            adjacent_results = []
            start_index = max(0, current_index - 1)  # -1
            end_index = min(len(subtitles), current_index + 2)  # +1
            
            for i in range(start_index, end_index):
                if i != current_index:  # Exclude current timestamp
                    adjacent_results.append({
                        'id': subtitles[i]['id'],
                        'score': subtitles[i]['score'],
                        'metadata': subtitles[i]['metadata']
                    })
            
            return adjacent_results[:count]
            
        except Exception as e:
            print(f"❌ Error getting adjacent timestamps: {e}")
            return []
    
    def search_with_rerank(self, query: str, video_id: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search subtitles with reranking"""
        try:
            # First, get more results than needed for reranking
            initial_results = self.search_subtitles(query, video_id=video_id, top_k=top_k * 2)
            
            # Rerank the results
            reranked_results = self.rerank_results(query, initial_results, top_k)
            
            return reranked_results
            
        except Exception as e:
            print(f"❌ Error in search with rerank: {e}")
            return []
    
    def search_timestamp_with_context(self, timestamp_id: str, video_id: str = None) -> List[Dict[str, Any]]:
        """Search timestamp with adjacent context"""
        try:
            # Get current timestamp
            current_result = self.get_subtitle_by_timestamp_id(timestamp_id, video_id)
            results = []
            
            if current_result:
                results.append(current_result)
            
            # Get adjacent timestamps (-1, +1)
            adjacent_results = self.get_adjacent_timestamps(timestamp_id, video_id, count=2)
            results.extend(adjacent_results)
            
            return results
            
        except Exception as e:
            print(f"❌ Error in search timestamp with context: {e}")
            return []
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        try:
            stats = {}
            
            # Get main index stats
            try:
                main_index = self.pc.Index(self.index_name)
                main_stats = main_index.describe_index_stats()
                
                # Get namespace-specific stats
                namespaces = main_stats.namespaces
                
                # Get subtitles namespace stats
                if self.subtitles_namespace in namespaces:
                    subtitles_ns = namespaces[self.subtitles_namespace]
                    stats['subtitles'] = {
                        'total_vectors': subtitles_ns.vector_count,
                        'dimension': main_stats.dimension
                    }
                else:
                    stats['subtitles'] = {'total_vectors': 0, 'dimension': main_stats.dimension}
                
                # Get summaries namespace stats
                if self.summaries_namespace in namespaces:
                    summaries_ns = namespaces[self.summaries_namespace]
                    stats['summaries'] = {
                        'total_vectors': summaries_ns.vector_count,
                        'dimension': main_stats.dimension
                    }
                else:
                    stats['summaries'] = {'total_vectors': 0, 'dimension': main_stats.dimension}
                    
            except Exception as e:
                stats['subtitles'] = {'error': str(e)}
                stats['summaries'] = {'error': str(e)}
            
            return stats
            
        except Exception as e:
            print(f"❌ Error getting index stats: {e}")
            return {}
    
    def wipe_index(self, namespace: str = None):
        """Wipe all data from specified namespace or both namespaces"""
        try:
            if namespace:
                # Wipe specific namespace
                if namespace in [self.subtitles_namespace, self.summaries_namespace]:
                    index = self.pc.Index(self.index_name, namespace=namespace)
                    index.delete(delete_all=True)
                    print(f"✅ Wiped {namespace} namespace")
                else:
                    print(f"❌ Invalid namespace: {namespace}")
            else:
                # Wipe both namespaces
                for ns in [self.subtitles_namespace, self.summaries_namespace]:
                    try:
                        index = self.pc.Index(self.index_name, namespace=ns)
                        index.delete(delete_all=True)
                        print(f"✅ Wiped {ns} namespace")
                    except Exception as e:
                        print(f"❌ Error wiping {ns}: {e}")
                        
        except Exception as e:
            print(f"❌ Error wiping namespace: {e}")


def store_to_pinecone(chunks_file: str = "chunked_transcript.json",
                     summaries_file: str = "summarized_report.json"):
    """Store data from JSON files to Pinecone"""
    try:
        print("🌲 Storing data to Pinecone...")
        
        # Initialize storage
        storage = PineconeStorage()
        
        # Store chunks
        if os.path.exists(chunks_file):
            print(f"📄 Loading chunks from {chunks_file}...")
            with open(chunks_file, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            
            print(f"📦 Storing {len(chunks)} chunks...")
            success_count = 0
            for chunk in chunks:
                if chunk.get('type') == 'subtitle':
                    if storage.store_subtitle(chunk):
                        success_count += 1
            
            print(f"✅ Stored {success_count}/{len(chunks)} chunks")
        else:
            print(f"⚠️  Chunks file not found: {chunks_file}")
        
        # Store summaries
        if os.path.exists(summaries_file):
            print(f"📄 Loading summaries from {summaries_file}...")
            with open(summaries_file, 'r', encoding='utf-8') as f:
                summaries = json.load(f)
            
            print(f"📦 Storing {len(summaries)} summaries...")
            success_count = 0
            for summary in summaries:
                if summary.get('type') == 'summary':
                    if storage.store_summary(summary):
                        success_count += 1
            
            print(f"✅ Stored {success_count}/{len(summaries)} summaries")
        else:
            print(f"⚠️  Summaries file not found: {summaries_file}")
        
        # Show stats
        stats = storage.get_index_stats()
        print(f"📊 Index Statistics:")
        print(f"  Subtitles: {stats.get('subtitles', {}).get('total_vectors', 0)} vectors")
        print(f"  Summaries: {stats.get('summaries', {}).get('total_vectors', 0)} vectors")
        
        return True
        
    except Exception as e:
        print(f"❌ Error storing to Pinecone: {e}")
        return False

