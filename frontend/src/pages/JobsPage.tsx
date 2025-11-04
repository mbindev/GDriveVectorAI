import React, { useEffect, useState } from 'react';
import {
  Container, Typography, Box, Paper, Card, CardContent, LinearProgress,
  Chip, IconButton, Button, Grid, Alert, CircularProgress, Dialog,
  DialogTitle, DialogContent, DialogActions, List, ListItem, ListItemText
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import InfoIcon from '@mui/icons-material/Info';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import axios from 'axios';

interface Job {
  job_id: string;
  folder_id: string;
  status: string;
  total_files: number;
  processed_files: number;
  failed_files: number;
  error_message: string;
  started_at: string;
  completed_at: string;
}

interface JobLog {
  id: number;
  drive_file_id: string;
  log_level: string;
  message: string;
  created_at: string;
  details: any;
}

const JobsPage: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [logs, setLogs] = useState<JobLog[]>([]);
  const [logsDialogOpen, setLogsDialogOpen] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/jobs/', { params: { limit: 50 } });
      setJobs(response.data.jobs);
    } catch (error: any) {
      setMessage({ type: 'error', text: 'Failed to fetch jobs' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  // Auto-refresh every 5 seconds if there are running jobs
  useEffect(() => {
    if (!autoRefresh) return;

    const hasRunningJobs = jobs.some(job => job.status === 'running');
    if (!hasRunningJobs) return;

    const interval = setInterval(() => {
      fetchJobs();
    }, 5000);

    return () => clearInterval(interval);
  }, [jobs, autoRefresh]);

  const handleViewLogs = async (job: Job) => {
    setSelectedJob(job);
    try {
      const response = await axios.get(`/api/jobs/${job.job_id}/logs`, {
        params: { limit: 200 }
      });
      setLogs(response.data.logs);
      setLogsDialogOpen(true);
    } catch (error: any) {
      setMessage({ type: 'error', text: 'Failed to fetch logs' });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success';
      case 'running': return 'info';
      case 'pending': return 'warning';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircleIcon />;
      case 'running': return <CircularProgress size={20} />;
      case 'failed': return <ErrorIcon />;
      default: return <PlayArrowIcon />;
    }
  };

  const calculateProgress = (job: Job) => {
    if (job.total_files === 0) return 0;
    return Math.round((job.processed_files / job.total_files) * 100);
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  const calculateDuration = (startedAt: string, completedAt: string) => {
    if (!startedAt) return 'N/A';
    const start = new Date(startedAt).getTime();
    const end = completedAt ? new Date(completedAt).getTime() : Date.now();
    const durationMs = end - start;
    const seconds = Math.floor(durationMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  };

  return (
    <Container maxWidth="xl">
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Ingestion Jobs
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant={autoRefresh ? 'contained' : 'outlined'}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            Auto-Refresh: {autoRefresh ? 'ON' : 'OFF'}
          </Button>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchJobs}
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

      {loading && jobs.length === 0 ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : jobs.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary">
            No jobs found. Start an ingestion to see jobs here.
          </Typography>
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {jobs.map((job) => (
            <Grid item xs={12} key={job.job_id}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Box>{getStatusIcon(job.status)}</Box>
                      <Box>
                        <Typography variant="h6">
                          Job: {job.job_id.substring(0, 8)}...
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Folder ID: {job.folder_id || 'N/A'}
                        </Typography>
                      </Box>
                      <Chip
                        label={job.status}
                        color={getStatusColor(job.status) as any}
                        size="small"
                      />
                    </Box>
                    <IconButton onClick={() => handleViewLogs(job)}>
                      <InfoIcon />
                    </IconButton>
                  </Box>

                  <Box sx={{ mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="body2">
                        Progress: {job.processed_files} / {job.total_files} files
                      </Typography>
                      <Typography variant="body2" fontWeight="bold">
                        {calculateProgress(job)}%
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={calculateProgress(job)}
                      color={job.failed_files > 0 ? 'warning' : 'primary'}
                    />
                  </Box>

                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={3}>
                      <Typography variant="caption" color="text.secondary">
                        Started
                      </Typography>
                      <Typography variant="body2">
                        {formatDate(job.started_at)}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={3}>
                      <Typography variant="caption" color="text.secondary">
                        Duration
                      </Typography>
                      <Typography variant="body2">
                        {calculateDuration(job.started_at, job.completed_at)}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={3}>
                      <Typography variant="caption" color="text.secondary">
                        Completed
                      </Typography>
                      <Typography variant="body2" color="success.main">
                        {job.processed_files - job.failed_files}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={3}>
                      <Typography variant="caption" color="text.secondary">
                        Failed
                      </Typography>
                      <Typography variant="body2" color="error.main">
                        {job.failed_files}
                      </Typography>
                    </Grid>
                  </Grid>

                  {job.error_message && (
                    <Alert severity="error" sx={{ mt: 2 }}>
                      {job.error_message}
                    </Alert>
                  )}
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Logs Dialog */}
      <Dialog open={logsDialogOpen} onClose={() => setLogsDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          Job Logs: {selectedJob?.job_id.substring(0, 8)}...
        </DialogTitle>
        <DialogContent>
          {logs.length === 0 ? (
            <Typography>No logs available</Typography>
          ) : (
            <List>
              {logs.map((log) => (
                <ListItem key={log.id} divider>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
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
                    }
                    secondary={
                      <>
                        <Typography variant="body2">{log.message}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          File ID: {log.drive_file_id.substring(0, 20)}...
                        </Typography>
                      </>
                    }
                  />
                </ListItem>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLogsDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default JobsPage;
