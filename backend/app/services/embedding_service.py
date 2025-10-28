from vertexai.language_models import TextEmbeddingModel
from app.main import settings
import vertexai

def get_text_embedding(text_content: str) -> List[float]:
    """Generate text embedding using Vertex AI."""
    # Initialize Vertex AI
    vertexai.init(project=settings.google_project_id, location="us-central1")

    # Get the embedding model
    model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")

    # Generate embedding
    embeddings = model.get_embeddings([text_content])

    return embeddings[0].values
