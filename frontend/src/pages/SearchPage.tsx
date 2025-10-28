import React from 'react';
import { Container, Typography, TextField, Button, Box, List, ListItem, ListItemText, Chip } from '@mui/material';
import axios from 'axios';

interface SearchResult {
  drive_file_id: string;
  file_name: string;
  mime_type: string;
  drive_url: string;
  extracted_text_snippet: string;
  similarity_score: number;
}

const SearchPage: React.FC = () => {
  const [query, setQuery] = React.useState('');
  const [results, setResults] = React.useState<SearchResult[]>([]);
  const [loading, setLoading] = React.useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    try {
      const response = await axios.post('/api/search', {
        query_text: query,
        limit: 10
      });
      setResults(response.data);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="lg">
      <Typography variant="h4" component="h1" gutterBottom>
        Document Search
      </Typography>

      <Box sx={{ mt: 3, mb: 4 }}>
        <TextField
          fullWidth
          label="Search query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
        />
        <Button
          variant="contained"
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          sx={{ mt: 2 }}
          size="large"
        >
          {loading ? 'Searching...' : 'Search'}
        </Button>
      </Box>

      {results.length > 0 && (
        <Box>
          <Typography variant="h6" gutterBottom>
            Search Results:
          </Typography>
          <List>
            {results.map((result) => (
              <ListItem key={result.drive_file_id} alignItems="flex-start">
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle1">{result.file_name}</Typography>
                      <Chip
                        label={`Similarity: ${(result.similarity_score * 100).toFixed(1)}%`}
                        size="small"
                        color="primary"
                      />
                    </Box>
                  }
                  secondary={
                    <>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        {result.extracted_text_snippet}
                      </Typography>
                      <Button
                        size="small"
                        href={result.drive_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        View in Drive
                      </Button>
                    </>
                  }
                />
              </ListItem>
            ))}
          </List>
        </Box>
      )}
    </Container>
  );
};

export default SearchPage;
