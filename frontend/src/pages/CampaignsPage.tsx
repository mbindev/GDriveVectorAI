import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  Container,
  Grid,
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Box,
  Chip,
  IconButton,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import { Add, Edit, Delete, Visibility, FilterList } from '@mui/icons-material';

interface Brand {
  id: number;
  name: string;
}

interface Campaign {
  id: number;
  name: string;
  brand_id: number;
  brand_name: string;
  description?: string;
  campaign_type?: string;
  start_date?: string;
  end_date?: string;
  is_active: boolean;
  created_at: string;
}

const CampaignsPage: React.FC = () => {
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [filterBrandId, setFilterBrandId] = useState<number | ''>('');
  const [openDialog, setOpenDialog] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState<Campaign | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    brand_id: '' as number | '',
    description: '',
    campaign_type: '',
    start_date: '',
    end_date: '',
  });

  useEffect(() => {
    fetchBrands();
    fetchCampaigns();
  }, []);

  useEffect(() => {
    fetchCampaigns();
  }, [filterBrandId]);

  const fetchBrands = async () => {
    try {
      const response = await axios.get('/api/brands/');
      setBrands(response.data.brands || []);
    } catch (err: any) {
      console.error('Failed to load brands');
    }
  };

  const fetchCampaigns = async () => {
    try {
      const params: any = {};
      if (filterBrandId) params.brand_id = filterBrandId;
      
      const response = await axios.get('/api/campaigns/', { params });
      setCampaigns(response.data.campaigns || []);
      setLoading(false);
    } catch (err: any) {
      setError('Failed to load campaigns');
      setLoading(false);
    }
  };

  const handleOpenDialog = (campaign?: Campaign) => {
    if (campaign) {
      setEditingCampaign(campaign);
      setFormData({
        name: campaign.name,
        brand_id: campaign.brand_id,
        description: campaign.description || '',
        campaign_type: campaign.campaign_type || '',
        start_date: campaign.start_date || '',
        end_date: campaign.end_date || '',
      });
    } else {
      setEditingCampaign(null);
      setFormData({
        name: '',
        brand_id: '',
        description: '',
        campaign_type: '',
        start_date: '',
        end_date: '',
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingCampaign(null);
  };

  const handleSaveCampaign = async () => {
    setError('');
    setSuccess('');

    if (!formData.name || !formData.brand_id) {
      setError('Campaign name and brand are required');
      return;
    }

    try {
      if (editingCampaign) {
        await axios.put(`/api/campaigns/${editingCampaign.id}`, formData);
        setSuccess('Campaign updated successfully');
      } else {
        await axios.post('/api/campaigns/', formData);
        setSuccess('Campaign created successfully');
      }
      
      handleCloseDialog();
      fetchCampaigns();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save campaign');
    }
  };

  const handleDeleteCampaign = async (campaignId: number) => {
    if (!window.confirm('Are you sure you want to delete this campaign? This will also delete all associated tags.')) {
      return;
    }

    try {
      await axios.delete(`/api/campaigns/${campaignId}`);
      setSuccess('Campaign deleted successfully');
      fetchCampaigns();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete campaign');
    }
  };

  const handleViewCampaign = (campaignId: number) => {
    navigate(`/campaigns/${campaignId}`);
  };

  const getCampaignStatus = (campaign: Campaign) => {
    if (!campaign.start_date || !campaign.end_date) return 'ongoing';
    
    const now = new Date();
    const start = new Date(campaign.start_date);
    const end = new Date(campaign.end_date);
    
    if (now < start) return 'scheduled';
    if (now > end) return 'ended';
    return 'active';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'success';
      case 'scheduled': return 'info';
      case 'ended': return 'default';
      default: return 'warning';
    }
  };

  if (loading) return <Typography>Loading...</Typography>;

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Campaign Management</Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Filter by Brand</InputLabel>
            <Select
              value={filterBrandId}
              label="Filter by Brand"
              onChange={(e) => setFilterBrandId(e.target.value as number | '')}
            >
              <MenuItem value="">All Brands</MenuItem>
              {brands.map((brand) => (
                <MenuItem key={brand.id} value={brand.id}>{brand.name}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => handleOpenDialog()}
          >
            Add Campaign
          </Button>
        </Box>
      </Box>

      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>{success}</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      <Grid container spacing={3}>
        {campaigns.map((campaign) => {
          const status = getCampaignStatus(campaign);
          return (
            <Grid item xs={12} sm={6} md={4} key={campaign.id}>
              <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <CardContent sx={{ flexGrow: 1 }}>
                  <Typography variant="h6" gutterBottom>
                    {campaign.name}
                  </Typography>
                  <Chip label={campaign.brand_name} size="small" color="primary" sx={{ mb: 1 }} />
                  <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                    <Chip
                      label={status}
                      size="small"
                      color={getStatusColor(status)}
                    />
                    {campaign.campaign_type && (
                      <Chip label={campaign.campaign_type} size="small" variant="outlined" />
                    )}
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {campaign.description || 'No description'}
                  </Typography>
                  {campaign.start_date && (
                    <Typography variant="caption" display="block" color="text.secondary">
                      Start: {new Date(campaign.start_date).toLocaleDateString()}
                    </Typography>
                  )}
                  {campaign.end_date && (
                    <Typography variant="caption" display="block" color="text.secondary">
                      End: {new Date(campaign.end_date).toLocaleDateString()}
                    </Typography>
                  )}
                </CardContent>
                <CardActions>
                  <IconButton size="small" onClick={() => handleViewCampaign(campaign.id)} color="primary">
                    <Visibility />
                  </IconButton>
                  <IconButton size="small" onClick={() => handleOpenDialog(campaign)} color="primary">
                    <Edit />
                  </IconButton>
                  <IconButton size="small" onClick={() => handleDeleteCampaign(campaign.id)} color="error">
                    <Delete />
                  </IconButton>
                </CardActions>
              </Card>
            </Grid>
          );
        })}
      </Grid>

      {campaigns.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Typography variant="h6" color="text.secondary">
            No campaigns found
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Create your first campaign to get started
          </Typography>
          <Button variant="contained" startIcon={<Add />} onClick={() => handleOpenDialog()}>
            Create Campaign
          </Button>
        </Box>
      )}

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{editingCampaign ? 'Edit Campaign' : 'Create New Campaign'}</DialogTitle>
        <DialogContent>
          <TextField
            margin="dense"
            label="Campaign Name"
            fullWidth
            required
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            autoFocus
          />
          <FormControl fullWidth margin="dense" required>
            <InputLabel>Brand</InputLabel>
            <Select
              value={formData.brand_id}
              label="Brand"
              onChange={(e) => setFormData({ ...formData, brand_id: e.target.value as number })}
            >
              {brands.map((brand) => (
                <MenuItem key={brand.id} value={brand.id}>{brand.name}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            margin="dense"
            label="Campaign Type"
            fullWidth
            value={formData.campaign_type}
            onChange={(e) => setFormData({ ...formData, campaign_type: e.target.value })}
            placeholder="e.g., Holiday, Product Launch, Seasonal"
          />
          <TextField
            margin="dense"
            label="Description"
            fullWidth
            multiline
            rows={3}
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Start Date"
            type="date"
            fullWidth
            value={formData.start_date}
            onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
            InputLabelProps={{ shrink: true }}
          />
          <TextField
            margin="dense"
            label="End Date"
            type="date"
            fullWidth
            value={formData.end_date}
            onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
            InputLabelProps={{ shrink: true }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSaveCampaign} variant="contained">
            {editingCampaign ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default CampaignsPage;
