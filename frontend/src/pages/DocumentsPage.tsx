import React, { useEffect, useState } from 'react';
import {
  Container, Typography, Box, Paper, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, IconButton, Chip, TextField,
  MenuItem, Select, FormControl, InputLabel, Pagination, Button,
  Dialog, DialogTitle, DialogContent, DialogActions, CircularProgress,
  Alert, Tooltip, Link
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import RefreshIcon from '@mui/icons-material/Refresh';
import InfoIcon from '@mui/icons-material/Info';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import axios from 'axios';

interface Document {
  id: number;
  drive_file_id: string;
  file_name: string;
  mime_type: string;
  drive_url: string;
  folder_id: string;
  status: string;
  error_message: string;
  full_text_length: number;
  created_at: string;
  updated_at: string;
  processed_at: string;
}

interface Log {
  id: number;
  log_level: string;
  message: string;
  created_at: string;
  details: any;
}

const DocumentsPage: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(20);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [logs, setLogs] = useState<Log[]>([]);
  const [logsDialogOpen, setLogsDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const offset = (page - 1) * limit;
      const params: any = { limit, offset };
      if (statusFilter) params.status = statusFilter;

      const response = await axios.get('/api/documents/', { params });
      setDocuments(response.data.documents);
      setTotal(response.data.total);
    } catch (error: any) {
      setMessage({ type: 'error', text: 'Failed to fetch documents' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [page, statusFilter]);

  const handleDelete = async () => {
    if (!selectedDoc) return;

    try {
      await axios.delete(`/api/documents/${selectedDoc.drive_file_id}`);
      setMessage({ type: 'success', text: 'Document deleted successfully' });
      setDeleteDialogOpen(false);
      setSelectedDoc(null);
      fetchDocuments();
    } catch (error: any) {
      setMessage({ type: 'error', text: 'Failed to delete document' });
    }
  };

  const handleViewLogs = async (doc: Document) => {
    setSelectedDoc(doc);
    try {
      const response = await axios.get(`/api/documents/${doc.drive_file_id}/logs`);
      setLogs(response.data.logs);
      setLogsDialogOpen(true);
    } catch (error: any) {
      setMessage({ type: 'error', text: 'Failed to fetch logs' });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success';
      case 'processing': return 'info';
      case 'pending': return 'warning';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  const formatFileSize = (length: number) => {
    if (!length) return 'N/A';
    if (length < 1024) return `${length} chars`;
    return `${(length / 1024).toFixed(2)} KB`;
  };

  return (
    <Container maxWidth="xl">
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Documents Library
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={fetchDocuments}
          disabled={loading}
        >
          Refresh
        </Button>
      </Box>

      {message && (
        <Alert severity={message.type} onClose={() => setMessage(null)} sx={{ mb: 2 }}>
          {message.text}
        </Alert>
      )}

      <Box sx={{ mb: 3, display: 'flex', gap: 2, alignItems: 'center' }}>
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>Status Filter</InputLabel>
          <Select
            value={statusFilter}
            label="Status Filter"
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="pending">Pending</MenuItem>
            <MenuItem value="processing">Processing</MenuItem>
            <MenuItem value="completed">Completed</MenuItem>
            <MenuItem value="failed">Failed</MenuItem>
          </Select>
        </FormControl>
        <Typography variant="body2" color="text.secondary">
          Total: {total} documents
        </Typography>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>File Name</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Size</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Processed</TableCell>
              <TableCell align="center">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <CircularProgress />
                </TableCell>
              </TableRow>
            ) : documents.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  No documents found
                </TableCell>
              </TableRow>
            ) : (
              documents.map((doc) => (
                <TableRow key={doc.id} hover>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body2">{doc.file_name}</Typography>
                      {doc.drive_url && (
                        <Tooltip title="Open in Google Drive">
                          <IconButton
                            size="small"
                            component="a"
                            href={doc.drive_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <OpenInNewIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">
                      {doc.mime_type.split('/').pop()}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={doc.status}
                      color={getStatusColor(doc.status) as any}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{formatFileSize(doc.full_text_length)}</TableCell>
                  <TableCell>
                    <Typography variant="caption">
                      {formatDate(doc.created_at)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">
                      {formatDate(doc.processed_at)}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Tooltip title="View Logs">
                      <IconButton size="small" onClick={() => handleViewLogs(doc)}>
                        <InfoIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => {
                          setSelectedDoc(doc);
                          setDeleteDialogOpen(true);
                        }}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
        <Pagination
          count={Math.ceil(total / limit)}
          page={page}
          onChange={(e, value) => setPage(value)}
          color="primary"
        />
      </Box>

      {/* Logs Dialog */}
      <Dialog open={logsDialogOpen} onClose={() => setLogsDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          Processing Logs: {selectedDoc?.file_name}
        </DialogTitle>
        <DialogContent>
          {logs.length === 0 ? (
            <Typography>No logs available</Typography>
          ) : (
            <Box sx={{ mt: 2 }}>
              {logs.map((log) => (
                <Box key={log.id} sx={{ mb: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Chip
                      label={log.log_level}
                      size="small"
                      color={
                        log.log_level === 'error' ? 'error' :
                        log.log_level === 'warning' ? 'warning' : 'info'
                      }
                    />
                    <Typography variant="caption" color="text.secondary">
                      {formatDate(log.created_at)}
                    </Typography>
                  </Box>
                  <Typography variant="body2">{log.message}</Typography>
                  {log.details && (
                    <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>
                      {JSON.stringify(log.details)}
                    </Typography>
                  )}
                </Box>
              ))}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLogsDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete "{selectedDoc?.file_name}"?
            This action cannot be undone.
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

export default DocumentsPage;
