"""
RAG (Retrieval-Augmented Generation) Service
Combines ChromaDB retrieval with Gemini LLM for context-aware responses
"""

from services.chroma_client import chroma_client
from services.gemini_client import gemini_client
from config import settings

class RAGService:
    """
    Retrieval-Augmented Generation service that:
    1. Retrieves relevant documents from ChromaDB
    2. Augments LLM prompt with retrieved context
    3. Generates informed responses using Gemini
    """

    def __init__(self, chroma_client, gemini_client, top_k=5):
        self.chroma_client = chroma_client
        self.gemini_client = gemini_client
        self.top_k = top_k

    async def query_with_rag(
        self, 
        user_query: str, 
        game: str = None,
        use_all_games: bool = False
    ) -> dict:
        """
        Query using RAG pattern:
        1. Search ChromaDB for relevant documents
        2. Build context from retrieved documents
        3. Augment prompt with context
        4. Generate response using Gemini
        
        Args:
            user_query: User's question
            game: Specific game to search (optional)
            use_all_games: Search across all games if True
            
        Returns:
            dict with response, sources, and context info
        """
        
        # Step 1: Retrieve relevant documents from ChromaDB
        retrieved_docs = self._retrieve_context(
            user_query, 
            game=game,
            use_all_games=use_all_games
        )
        
        # Step 2: Format retrieved context
        context_text = self._format_context(retrieved_docs)
        
        # Step 3: Build augmented prompt
        augmented_prompt = self._build_augmented_prompt(user_query, context_text)
        
        # Step 4: Generate response with Gemini
        response_text = await self.gemini_client.generate_text(augmented_prompt)
        
        return {
            "response": response_text,
            "sources": retrieved_docs,
            "context_count": len(retrieved_docs),
            "game": game,
        }

    def _retrieve_context(
        self, 
        query: str, 
        game: str = None,
        use_all_games: bool = False,
        top_k: int = None
    ) -> list:
        """
        Retrieve relevant documents from ChromaDB
        """
        if top_k is None:
            top_k = self.top_k
        
        try:
            # If specific game requested, search that collection
            if game and not use_all_games:
                return self._search_game_collection(query, game, top_k)
            
            # Search across all game collections
            if use_all_games:
                return self._search_all_collections(query, top_k)
            
            # Default: search all available collections
            return self._search_all_collections(query, top_k)
            
        except Exception as e:
            print(f"Error retrieving context: {e}")
            return []

    def _search_game_collection(self, query: str, game: str, top_k: int) -> list:
        """Search a specific game's ChromaDB collection"""
        try:
            collection = self.chroma_client.get_or_create_collection(game)
            results = collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            # Format results
            documents = []
            if results and results['documents'] and len(results['documents']) > 0:
                for i, doc in enumerate(results['documents'][0]):
                    documents.append({
                        "game": game,
                        "content": doc,
                        "distance": results['distances'][0][i] if results.get('distances') else 0,
                        "metadata": results['metadatas'][0][i] if results.get('metadatas') and i < len(results['metadatas'][0]) else {}
                    })
            
            return documents
        except Exception as e:
            print(f"Error searching {game} collection: {e}")
            return []

    def _search_all_collections(self, query: str, top_k: int) -> list:
        """Search across all game collections"""
        all_documents = []
        
        try:
            collections = self.chroma_client.client.list_collections()
            
            for collection_obj in collections:
                game_name = collection_obj.name
                try:
                    collection = self.chroma_client.get_or_create_collection(game_name)
                    results = collection.query(
                        query_texts=[query],
                        n_results=top_k // len(collections) + 1  # Distribute top_k across collections
                    )
                    
                    if results and results['documents'] and len(results['documents']) > 0:
                        for i, doc in enumerate(results['documents'][0]):
                            all_documents.append({
                                "game": game_name,
                                "content": doc,
                                "distance": results['distances'][0][i] if results.get('distances') else 0,
                                "metadata": results['metadatas'][0][i] if results.get('metadatas') and i < len(results['metadatas'][0]) else {}
                            })
                except Exception as e:
                    print(f"Error searching {game_name} collection: {e}")
                    continue
            
            # Sort by distance and return top_k
            all_documents.sort(key=lambda x: x.get('distance', float('inf')))
            return all_documents[:top_k]
            
        except Exception as e:
            print(f"Error listing collections: {e}")
            return []

    def _format_context(self, documents: list) -> str:
        """Format retrieved documents into context string for prompt"""
        if not documents:
            return "No relevant context found in the database."
        
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            game = doc.get('game', 'Unknown')
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            distance = doc.get('distance', 0)
            
            # Build document context
            doc_context = f"[Source {i} - {game.upper()}]\n{content}"
            
            if metadata and metadata.get('winning_numbers'):
                doc_context += f"\nWinning Numbers: {metadata.get('winning_numbers')}"
            if metadata and metadata.get('draw_date'):
                doc_context += f"\nDraw Date: {metadata.get('draw_date')}"
            
            context_parts.append(doc_context)
        
        return "\n\n".join(context_parts)

    def _build_augmented_prompt(self, user_query: str, context: str) -> str:
        """Build the augmented prompt with context for Gemini"""
        augmented_prompt = f"""You are an expert lottery data analyst. Use the following context from our lottery database to answer the user's question accurately and helpfully.

CONTEXT FROM LOTTERY DATABASE:
{context}

---

USER QUESTION: {user_query}

Please provide a helpful, accurate response based on the context above. If the context doesn't contain relevant information, say so clearly and provide general knowledge if helpful."""
        
        return augmented_prompt

    async def generate_summary(self, game: str) -> str:
        """Generate a summary of a game's lottery data"""
        query = f"Summary of {game} lottery draws, patterns, and frequency statistics"
        result = await self.query_with_rag(
            user_query=query,
            game=game,
            use_all_games=False
        )
        return result['response']

    async def generate_game_comparison(self) -> str:
        """Generate comparison across all games"""
        query = "Compare the lottery games across draws, odds, and patterns"
        result = await self.query_with_rag(
            user_query=query,
            use_all_games=True
        )
        return result['response']


# Initialize RAG service
rag_service = RAGService(chroma_client, gemini_client, top_k=5)
