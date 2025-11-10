import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  Container,
  Paper,
  Typography,
  Box,
  Grid,
  Card,
  CardContent,
  Button,
  Chip,
  List,
  ListItem,
  ListItemText,
  Divider,
  Alert,
  Tab,
  Tabs,
} from '@mui/material';
import { ArrowBack, Campaign, Description } from '@mui/icons-material';

interface Brand {
  id: number;
  name: string;
  description?: string;
  logo_url?: string;
  brand_color?: string;
  is_active: boolean;
  created_at: string;
}

interface BrandStatistics {
  total_documents: number;
  resource_breakdown: Record<string, number>;
  campaign_count: number;
  active_campaigns: number;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const BrandDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const [brand, setBrand] = useState<Brand | null>(null);
  const [statistics, setStatistics] = useState<BrandStatistics | null>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tabValue, setTabValue] = useState(0);

  useEffect(() => {
    if (id) {
      fetchBrandDetails();
      fetchStatistics();
      fetchDocuments();
    }
  }, [id]);

  const fetchBrandDetails = async () => {
    try {
      const response = await axios.get(`/api/brands/${id}`);
      setBrand(response.data);
    } catch (err: any) {
      setError('Failed to load brand details');
    }
  };

  const fetchStatistics = async () => {
    try {
      const response = await axios.get(`/api/brands/${id}/statistics`);
      setStatistics(response.data);
      setLoading(false);
    } catch (err: any) {
      setError('Failed to load statistics');
      setLoading(false);
    }
  };

  const fetchDocuments = async () => {
    try {
      const response = await axios.get(`/api/brands/${id}/documents`);
      setDocuments(response.data.documents || []);
    } catch (err: any) {
      console.error('Failed to load documents');
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  if (loading) return <Typography>Loading...</Typography>;
  if (!brand) return <Typography>Brand not found</Typography>;

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Button
        startIcon={<ArrowBack />}
        onClick={() => navigate('/brands')}
        sx={{ mb: 2 }}
      >
        Back to Brands
      </Button>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Paper sx={{ p: 4, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h4" gutterBottom>
              {brand.name}
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
              {brand.description || 'No description'}
            </Typography>
            <Chip
              label={brand.is_active ? 'Active' : 'Inactive'}
              color={brand.is_active ? 'success' : 'default'}
            />
          </Box>
          {brand.logo_url && (
            <img src={brand.logo_url} alt={brand.name} style={{ height: 80, marginLeft: 16 }} />
          )}
        </Box>
      </Paper>

      {statistics && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Total Documents
                </Typography>
                <Typography variant="h4">{statistics.total_documents}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Campaigns
                </Typography>
                <Typography variant="h4">{statistics.campaign_count}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {statistics.active_campaigns} active
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  PDFs
                </Typography>
                <Typography variant="h4">
                  {statistics.resource_breakdown.pdf || 0}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Images
                </Typography>
                <Typography variant="h4">
                  {statistics.resource_breakdown.image || 0}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      <Paper>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab icon={<Description />} label="Documents" iconPosition="start" />
          <Tab icon={<Campaign />} label="Resource Breakdown" iconPosition="start" />
        </Tabs>
        
        <TabPanel value={tabValue} index={0}>
          <List>
            {documents.length === 0 ? (
              <Typography color="text.secondary" sx={{ p: 2 }}>
                No documents tagged with this brand
              </Typography>
            ) : (
              documents.map((doc, index) => (
                <React.Fragment key={doc.drive_file_id}>
                  <ListItem>
                    <ListItemText
                      primary={doc.file_name}
                      secondary={`Type: ${doc.resource_type || 'Unknown'} | Added: ${new Date(doc.tagged_at).toLocaleDateString()}`}
                    />
                    <Chip label={doc.resource_type || 'Unknown'} size="small" />
                  </ListItem>
                  {index < documents.length - 1 && <Divider />}
                </React.Fragment>
              ))
            )}
          </List>
        </TabPanel>
        
        <TabPanel value={tabValue} index={1}>
          <Grid container spacing={2}>
            {statistics && Object.entries(statistics.resource_breakdown).map(([type, count]) => (
              <Grid item xs={12} sm={6} md={4} key={type}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h6">{type}</Typography>
                    <Typography variant="h4" color="primary">{count}</Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </TabPanel>
      </Paper>
    </Container>
  );
};

export default BrandDetailsPage;
