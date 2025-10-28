import React from 'react';
import { Container, Typography, Button, Box, Alert, CircularProgress, List, ListItem, ListItemText } from '@mui/material';
import axios from 'axios';

interface FileInfo {
  id: string;
  name: string;
}

const IngestionPage: React.FC = () => {
  const [loading, setLoading] = React.useState(false);
  const [message, setMessage] = React.useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [files, setFiles] = React.useState<FileInfo[]>([]);

  const handleStartIngestion = async () => {
    setLoading(true);
    setMessage(null);

    try {
      const response = await axios.post('/api/ingest/start', {
        folder_id: process.env.REACT_APP_DRIVE_FOLDER_ID || ''
      });

      setFiles(response.data.files);
      setMessage({ type: 'success', text: response.data.message });
    } catch (error: any) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to start ingestion. Please check your settings.'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="md">
      <Typography variant="h4" component="h1" gutterBottom>
        Document Ingestion
      </Typography>

      {message && (
        <Alert severity={message.type} sx={{ mb: 2 }}>
          {message.text}
        </Alert>
      )}

      <Box sx={{ mt: 3 }}>
        <Button
          variant="contained"
          onClick={handleStartIngestion}
          disabled={loading}
          size="large"
          startIcon={loading && <CircularProgress size={20} />}
        >
          {loading ? 'Starting Ingestion...' : 'Start Drive Scan & Ingest'}
        </Button>
      </Box>

      {files.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            Files Queued for Processing:
          </Typography>
          <List>
            {files.map((file) => (
              <ListItem key={file.id}>
                <ListItemText primary={file.name} secondary={`ID: ${file.id}`} />
              </ListItem>
            ))}
          </List>
        </Box>
      )}
    </Container>
  );
};

export default IngestionPage;
