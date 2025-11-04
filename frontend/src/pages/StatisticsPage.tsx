import React, { useEffect, useState } from 'react';
import {
  Container, Typography, Box, Paper, Grid, Card, CardContent,
  CircularProgress, Alert, Divider
} from '@mui/material';
import FolderIcon from '@mui/icons-material/Folder';
import DescriptionIcon from '@mui/icons-material/Description';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import PendingIcon from '@mui/icons-material/Pending';
import WorkIcon from '@mui/icons-material/Work';
import StorageIcon from '@mui/icons-material/Storage';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import axios from 'axios';

interface Statistics {
  total_documents: number;
  completed_documents: number;
  failed_documents: number;
  pending_documents: number;
  processing_documents: number;
  total_text_length: number;
  avg_text_length: number;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  running_jobs: number;
  total_folders: number;
}

const StatisticsPage: React.FC = () => {
  const [stats, setStats] = useState<Statistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchStatistics = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/statistics/');
      setStats(response.data);
    } catch (error: any) {
      setMessage({ type: 'error', text: 'Failed to fetch statistics' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatistics();
    // Refresh every 30 seconds
    const interval = setInterval(fetchStatistics, 30000);
    return () => clearInterval(interval);
  }, []);

  const formatBytes = (bytes: number) => {
    if (!bytes || bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const StatCard: React.FC<{
    title: string;
    value: string | number;
    subtitle?: string;
    icon: React.ReactNode;
    color: string;
  }> = ({ title, value, subtitle, icon, color }) => (
    <Card elevation={2}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6" color="text.secondary">
            {title}
          </Typography>
          <Box sx={{ color, display: 'flex', alignItems: 'center' }}>
            {icon}
          </Box>
        </Box>
        <Typography variant="h3" fontWeight="bold">
          {value}
        </Typography>
        {subtitle && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {subtitle}
          </Typography>
        )}
      </CardContent>
    </Card>
  );

  if (loading && !stats) {
    return (
      <Container maxWidth="xl">
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  if (!stats) {
    return (
      <Container maxWidth="xl">
        <Alert severity="error">Failed to load statistics</Alert>
      </Container>
    );
  }

  const successRate = stats.total_documents > 0
    ? Math.round((stats.completed_documents / stats.total_documents) * 100)
    : 0;

  const jobSuccessRate = stats.total_jobs > 0
    ? Math.round((stats.completed_jobs / stats.total_jobs) * 100)
    : 0;

  return (
    <Container maxWidth="xl">
      <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 4 }}>
        System Statistics
      </Typography>

      {message && (
        <Alert severity={message.type} onClose={() => setMessage(null)} sx={{ mb: 3 }}>
          {message.text}
        </Alert>
      )}

      {/* Overview Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Documents"
            value={stats.total_documents?.toLocaleString() || 0}
            icon={<DescriptionIcon fontSize="large" />}
            color="#1976d2"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Jobs"
            value={stats.total_jobs?.toLocaleString() || 0}
            icon={<WorkIcon fontSize="large" />}
            color="#9c27b0"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Folders"
            value={stats.total_folders?.toLocaleString() || 0}
            icon={<FolderIcon fontSize="large" />}
            color="#ed6c02"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Success Rate"
            value={`${successRate}%`}
            subtitle={`${stats.completed_documents} / ${stats.total_documents} documents`}
            icon={<TrendingUpIcon fontSize="large" />}
            color="#2e7d32"
          />
        </Grid>
      </Grid>

      {/* Document Status Breakdown */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h5" gutterBottom sx={{ mb: 3 }}>
          Document Status Breakdown
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6} md={3}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <CheckCircleIcon sx={{ color: 'success.main', fontSize: 40 }} />
              <Box>
                <Typography variant="h4" fontWeight="bold">
                  {stats.completed_documents?.toLocaleString() || 0}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Completed
                </Typography>
              </Box>
            </Box>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <ErrorIcon sx={{ color: 'error.main', fontSize: 40 }} />
              <Box>
                <Typography variant="h4" fontWeight="bold">
                  {stats.failed_documents?.toLocaleString() || 0}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Failed
                </Typography>
              </Box>
            </Box>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <CircularProgress size={40} />
              <Box>
                <Typography variant="h4" fontWeight="bold">
                  {stats.processing_documents?.toLocaleString() || 0}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Processing
                </Typography>
              </Box>
            </Box>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <PendingIcon sx={{ color: 'warning.main', fontSize: 40 }} />
              <Box>
                <Typography variant="h4" fontWeight="bold">
                  {stats.pending_documents?.toLocaleString() || 0}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Pending
                </Typography>
              </Box>
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* Job Status Breakdown */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h5" gutterBottom sx={{ mb: 3 }}>
          Job Status Breakdown
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={4}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <CheckCircleIcon sx={{ color: 'success.main', fontSize: 40 }} />
              <Box>
                <Typography variant="h4" fontWeight="bold">
                  {stats.completed_jobs?.toLocaleString() || 0}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Completed Jobs
                </Typography>
              </Box>
            </Box>
          </Grid>
          <Grid item xs={12} sm={4}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <CircularProgress size={40} />
              <Box>
                <Typography variant="h4" fontWeight="bold">
                  {stats.running_jobs?.toLocaleString() || 0}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Running Jobs
                </Typography>
              </Box>
            </Box>
          </Grid>
          <Grid item xs={12} sm={4}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <ErrorIcon sx={{ color: 'error.main', fontSize: 40 }} />
              <Box>
                <Typography variant="h4" fontWeight="bold">
                  {stats.failed_jobs?.toLocaleString() || 0}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Failed Jobs
                </Typography>
              </Box>
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* Storage Statistics */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom sx={{ mb: 3 }}>
          Storage Statistics
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <StorageIcon sx={{ color: 'primary.main', fontSize: 40 }} />
              <Box>
                <Typography variant="h4" fontWeight="bold">
                  {formatBytes(stats.total_text_length || 0)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total Text Processed
                </Typography>
              </Box>
            </Box>
          </Grid>
          <Grid item xs={12} sm={6}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <StorageIcon sx={{ color: 'secondary.main', fontSize: 40 }} />
              <Box>
                <Typography variant="h4" fontWeight="bold">
                  {formatBytes(stats.avg_text_length || 0)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Average Document Size
                </Typography>
              </Box>
            </Box>
          </Grid>
        </Grid>
      </Paper>
    </Container>
  );
};

export default StatisticsPage;
