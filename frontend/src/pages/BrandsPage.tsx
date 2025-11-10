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
  Avatar,
} from '@mui/material';
import { Add, Edit, Delete, Visibility } from '@mui/icons-material';

interface Brand {
  id: number;
  name: string;
  description?: string;
  logo_url?: string;
  brand_color?: string;
  is_active: boolean;
  created_at: string;
}

const BrandsPage: React.FC = () => {
  const navigate = useNavigate();
  const [brands, setBrands] = useState<Brand[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [openDialog, setOpenDialog] = useState(false);
  const [editingBrand, setEditingBrand] = useState<Brand | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    logo_url: '',
    brand_color: '#1976d2',
  });

  useEffect(() => {
    fetchBrands();
  }, []);

  const fetchBrands = async () => {
    try {
      const response = await axios.get('/api/brands/');
      setBrands(response.data.brands || []);
      setLoading(false);
    } catch (err: any) {
      setError('Failed to load brands');
      setLoading(false);
    }
  };

  const handleOpenDialog = (brand?: Brand) => {
    if (brand) {
      setEditingBrand(brand);
      setFormData({
        name: brand.name,
        description: brand.description || '',
        logo_url: brand.logo_url || '',
        brand_color: brand.brand_color || '#1976d2',
      });
    } else {
      setEditingBrand(null);
      setFormData({
        name: '',
        description: '',
        logo_url: '',
        brand_color: '#1976d2',
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingBrand(null);
  };

  const handleSaveBrand = async () => {
    setError('');
    setSuccess('');

    if (!formData.name) {
      setError('Brand name is required');
      return;
    }

    try {
      if (editingBrand) {
        await axios.put(`/api/brands/${editingBrand.id}`, formData);
        setSuccess('Brand updated successfully');
      } else {
        await axios.post('/api/brands/', formData);
        setSuccess('Brand created successfully');
      }
      
      handleCloseDialog();
      fetchBrands();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save brand');
    }
  };

  const handleDeleteBrand = async (brandId: number) => {
    if (!window.confirm('Are you sure you want to delete this brand? This will also delete all associated campaigns and tags.')) {
      return;
    }

    try {
      await axios.delete(`/api/brands/${brandId}`);
      setSuccess('Brand deleted successfully');
      fetchBrands();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete brand');
    }
  };

  const handleViewBrand = (brandId: number) => {
    navigate(`/brands/${brandId}`);
  };

  if (loading) return <Typography>Loading...</Typography>;

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Brand Management</Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => handleOpenDialog()}
        >
          Add Brand
        </Button>
      </Box>

      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>{success}</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      <Grid container spacing={3}>
        {brands.map((brand) => (
          <Grid item xs={12} sm={6} md={4} key={brand.id}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flexGrow: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  {brand.logo_url ? (
                    <Avatar src={brand.logo_url} sx={{ width: 56, height: 56, mr: 2 }} />
                  ) : (
                    <Avatar
                      sx={{
                        width: 56,
                        height: 56,
                        mr: 2,
                        bgcolor: brand.brand_color || '#1976d2',
                      }}
                    >
                      {brand.name.charAt(0).toUpperCase()}
                    </Avatar>
                  )}
                  <Box>
                    <Typography variant="h6">{brand.name}</Typography>
                    <Chip
                      label={brand.is_active ? 'Active' : 'Inactive'}
                      size="small"
                      color={brand.is_active ? 'success' : 'default'}
                    />
                  </Box>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  {brand.description || 'No description'}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Created: {new Date(brand.created_at).toLocaleDateString()}
                </Typography>
              </CardContent>
              <CardActions>
                <IconButton size="small" onClick={() => handleViewBrand(brand.id)} color="primary">
                  <Visibility />
                </IconButton>
                <IconButton size="small" onClick={() => handleOpenDialog(brand)} color="primary">
                  <Edit />
                </IconButton>
                <IconButton size="small" onClick={() => handleDeleteBrand(brand.id)} color="error">
                  <Delete />
                </IconButton>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {brands.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Typography variant="h6" color="text.secondary">
            No brands found
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Create your first brand to get started
          </Typography>
          <Button variant="contained" startIcon={<Add />} onClick={() => handleOpenDialog()}>
            Create Brand
          </Button>
        </Box>
      )}

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{editingBrand ? 'Edit Brand' : 'Create New Brand'}</DialogTitle>
        <DialogContent>
          <TextField
            margin="dense"
            label="Brand Name"
            fullWidth
            required
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            autoFocus
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
            label="Logo URL"
            fullWidth
            value={formData.logo_url}
            onChange={(e) => setFormData({ ...formData, logo_url: e.target.value })}
          />
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" gutterBottom>Brand Color</Typography>
            <input
              type="color"
              value={formData.brand_color}
              onChange={(e) => setFormData({ ...formData, brand_color: e.target.value })}
              style={{ width: '100%', height: '40px', cursor: 'pointer' }}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSaveBrand} variant="contained">
            {editingBrand ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default BrandsPage;
