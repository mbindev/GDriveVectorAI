import React, { useEffect, useState } from 'react';
import {
  Container, Typography, Box, Paper, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, IconButton, Button, TextField,
  Dialog, DialogTitle, DialogContent, DialogActions, Alert, Chip
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import AddIcon from '@mui/icons-material/Add';
import RefreshIcon from '@mui/icons-material/Refresh';
import axios from 'axios';

interface Folder {
  folder_id: string;
  folder_name: string;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

const FoldersPage: React.FC = () => {
  const [folders, setFolders] = useState<Folder[]>([]);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedFolder, setSelectedFolder] = useState<Folder | null>(null);
  const [formData, setFormData] = useState({
    folder_id: '',
    folder_name: '',
    description: ''
  });
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchFolders = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/folders/');
      setFolders(response.data.folders);
    } catch (error: any) {
      setMessage({ type: 'error', text: 'Failed to fetch folders' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFolders();
  }, []);

  const handleOpenDialog = (folder?: Folder) => {
    if (folder) {
      setSelectedFolder(folder);
      setFormData({
        folder_id: folder.folder_id,
        folder_name: folder.folder_name,
        description: folder.description || ''
      });
    } else {
      setSelectedFolder(null);
      setFormData({
        folder_id: '',
        folder_name: '',
        description: ''
      });
    }
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      if (selectedFolder) {
        // Update existing folder
        await axios.put(`/api/folders/${selectedFolder.folder_id}`, {
          folder_name: formData.folder_name,
          description: formData.description
        });
        setMessage({ type: 'success', text: 'Folder updated successfully' });
      } else {
        // Create new folder
        await axios.post('/api/folders/', formData);
        setMessage({ type: 'success', text: 'Folder created successfully' });
      }
      setDialogOpen(false);
      fetchFolders();
    } catch (error: any) {
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to save folder' });
    }
  };

  const handleDelete = async () => {
    if (!selectedFolder) return;

    try {
      await axios.delete(`/api/folders/${selectedFolder.folder_id}`);
      setMessage({ type: 'success', text: 'Folder deleted successfully' });
      setDeleteDialogOpen(false);
      setSelectedFolder(null);
      fetchFolders();
    } catch (error: any) {
      setMessage({ type: 'error', text: 'Failed to delete folder' });
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Folder Management
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
          >
            Add Folder
          </Button>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchFolders}
            disabled={loading}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {message && (
        <Alert severity={message.type} onClose={() => setMessage(null)} sx={{ mb: 2 }}>
          {message.text}
        </Alert>
      )}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Folder Name</TableCell>
              <TableCell>Folder ID</TableCell>
              <TableCell>Description</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Created</TableCell>
              <TableCell align="center">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {folders.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  No folders configured. Add a folder to get started.
                </TableCell>
              </TableRow>
            ) : (
              folders.map((folder) => (
                <TableRow key={folder.folder_id} hover>
                  <TableCell>
                    <Typography variant="body1" fontWeight="medium">
                      {folder.folder_name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
                      {folder.folder_id}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {folder.description || 'No description'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={folder.is_active ? 'Active' : 'Inactive'}
                      color={folder.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">
                      {formatDate(folder.created_at)}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <IconButton
                      size="small"
                      onClick={() => handleOpenDialog(folder)}
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => {
                        setSelectedFolder(folder);
                        setDeleteDialogOpen(true);
                      }}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Add/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {selectedFolder ? 'Edit Folder' : 'Add New Folder'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Folder ID"
              value={formData.folder_id}
              onChange={(e) => setFormData({ ...formData, folder_id: e.target.value })}
              fullWidth
              required
              disabled={!!selectedFolder}
              helperText="The Google Drive folder ID from the URL"
            />
            <TextField
              label="Folder Name"
              value={formData.folder_name}
              onChange={(e) => setFormData({ ...formData, folder_name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              fullWidth
              multiline
              rows={3}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleSave}
            variant="contained"
            disabled={!formData.folder_id || !formData.folder_name}
          >
            {selectedFolder ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete "{selectedFolder?.folder_name}"?
            This will not delete associated documents but will remove the folder reference.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default FoldersPage;
