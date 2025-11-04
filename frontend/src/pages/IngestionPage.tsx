import React, { useEffect } from 'react';
import {
  Container, Typography, Button, Box, Alert, CircularProgress, List,
  ListItem, ListItemText, TextField, Paper, MenuItem, Select,
  FormControl, InputLabel, Card, CardContent, Divider
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

interface FileInfo {
  id: string;
  name: string;
}

interface Folder {
  folder_id: string;
  folder_name: string;
  description: string;
}

const IngestionPage: React.FC = () => {
  const [loading, setLoading] = React.useState(false);
  const [message, setMessage] = React.useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [files, setFiles] = React.useState<FileInfo[]>([]);
  const [folders, setFolders] = React.useState<Folder[]>([]);
  const [selectedFolderId, setSelectedFolderId] = React.useState('');
  const [folderName, setFolderName] = React.useState('');
  const [description, setDescription] = React.useState('');
  const [jobId, setJobId] = React.useState<string | null>(null);
  const navigate = useNavigate();

  const fetchFolders = async () => {
    try {
      const response = await axios.get('/api/folders/');
      setFolders(response.data.folders);
    } catch (error) {
      console.error('Failed to fetch folders');
    }
  };

  useEffect(() => {
    fetchFolders();
  }, []);

  const handleStartIngestion = async () => {
    if (!selectedFolderId) {
      setMessage({ type: 'error', text: 'Please enter a folder ID' });
      return;
    }

    setLoading(true);
    setMessage(null);
    setJobId(null);

    try {
      const response = await axios.post('/api/ingest/start', {
        folder_id: selectedFolderId,
        folder_name: folderName || `Folder ${selectedFolderId}`,
        description: description
      });

      setFiles(response.data.files);
      setJobId(response.data.job_id);
      setMessage({
        type: 'success',
        text: `Started ingestion: ${response.data.message}`
      });
    } catch (error: any) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to start ingestion. Please check your settings.'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleViewJob = () => {
    if (jobId) {
      navigate(`/?tab=jobs`);
    }
  };

  return (
    <Container maxWidth="md">
      <Typography variant="h4" component="h1" gutterBottom>
        Document Ingestion
      </Typography>

      <Typography variant="body1" color="text.secondary" paragraph>
        Start a new ingestion job to process documents from a Google Drive folder.
        All documents will be downloaded, text will be extracted, and vector embeddings
        will be generated for semantic search.
      </Typography>

      {message && (
        <Alert
          severity={message.type}
          onClose={() => setMessage(null)}
          sx={{ mb: 2 }}
          action={
            jobId && message.type === 'success' ? (
              <Button color="inherit" size="small" onClick={handleViewJob}>
                View Job
              </Button>
            ) : undefined
          }
        >
          {message.text}
        </Alert>
      )}

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Configuration
          </Typography>
          <Divider sx={{ mb: 3 }} />

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {folders.length > 0 && (
              <FormControl fullWidth>
                <InputLabel>Select Existing Folder</InputLabel>
                <Select
                  value={selectedFolderId}
                  label="Select Existing Folder"
                  onChange={(e) => {
                    const folder = folders.find(f => f.folder_id === e.target.value);
                    setSelectedFolderId(e.target.value);
                    if (folder) {
                      setFolderName(folder.folder_name);
                      setDescription(folder.description);
                    }
                  }}
                >
                  <MenuItem value="">
                    <em>Or enter a new folder ID below</em>
                  </MenuItem>
                  {folders.map((folder) => (
                    <MenuItem key={folder.folder_id} value={folder.folder_id}>
                      {folder.folder_name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}

            <TextField
              label="Google Drive Folder ID"
              value={selectedFolderId}
              onChange={(e) => setSelectedFolderId(e.target.value)}
              fullWidth
              required
              helperText="Enter the folder ID from the Google Drive URL"
              placeholder="e.g., 1a2b3c4d5e6f7g8h9i0j"
            />

            <TextField
              label="Folder Name"
              value={folderName}
              onChange={(e) => setFolderName(e.target.value)}
              fullWidth
              helperText="A friendly name for this folder"
            />

            <TextField
              label="Description (Optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              fullWidth
              multiline
              rows={2}
              helperText="Describe the contents of this folder"
            />

            <Button
              variant="contained"
              onClick={handleStartIngestion}
              disabled={loading || !selectedFolderId}
              size="large"
              startIcon={loading ? <CircularProgress size={20} /> : <PlayArrowIcon />}
              fullWidth
            >
              {loading ? 'Starting Ingestion...' : 'Start Ingestion'}
            </Button>
          </Box>
        </CardContent>
      </Card>

      {files.length > 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Files Queued for Processing ({files.length}):
          </Typography>
          <List sx={{ maxHeight: 400, overflow: 'auto' }}>
            {files.map((file) => (
              <ListItem key={file.id} divider>
                <ListItemText
                  primary={file.name}
                  secondary={`File ID: ${file.id}`}
                  secondaryTypographyProps={{ sx: { fontFamily: 'monospace', fontSize: '0.75rem' } }}
                />
              </ListItem>
            ))}
          </List>
        </Paper>
      )}
    </Container>
  );
};

export default IngestionPage;
